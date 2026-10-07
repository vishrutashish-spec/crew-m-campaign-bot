"""
Crew M API server.

Cohort-first: age cohorts are the primary organising dimension, with org type
as a drill-down. Every figure served here is an exact sum over the deterministic
cohort model, and the model is verified against its anchors before the server
accepts a single request.

--- Data access note (governance) ---
What: aggregate cohort counts and documented segment totals. Why: the product
answers who to target, on which channel, at what time. Protection: no
user-level records are read or served, every response is counts-only, all
CleverTap queries are read-only and bounded to <= 1 year, and every data-access
route logs what was requested.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import anchors as A
import population as P
import insights as I
import copy_engine as CE
import decisions as D
import signal_engine as SIG
import cohort_intel as CI
import timing as T

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crewm")

app = FastAPI(title="Crew M API", version="2.0.0")

# ---------------------------------------------------------------------------
# CleverTap resync cache
# ---------------------------------------------------------------------------
# A successful resync is held in memory for the life of the process and layered
# over the anchored CT_LIVE block when the overview is served. The anchors
# themselves are never mutated: they are the committed record of what was
# verified and when, and a live pull is a different claim with its own
# timestamp. Nothing here feeds the cohort model, so no invariant can move
# under a resync.
_CT_RESYNC: Optional[dict] = None


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict = {}


def get_model() -> dict:
    """Build and verify the cohort model once. Refuses to serve if it fails."""
    if "model" not in _state:
        logger.info("Building deterministic cohort model...")
        model = P.build()
        checks = P.verify(model)   # raises if any anchor disagrees
        # Stamped on the model so anything that quotes the count reads the real
        # one. It has drifted twice already from being typed into prose.
        model["invariant_count"] = len(checks)
        _state["model"] = model
        _state["checks"] = checks
        _state["built_at"] = datetime.now(timezone.utc).isoformat()
        _state["sim_checks"] = _simulation_sweep(model)
        logger.info(
            f"Cohort model verified, {len(checks)} invariants and "
            f"{len(_state['sim_checks'])} simulation checks hold"
        )
    return _state["model"]


def _simulation_sweep(model: dict) -> list[str]:
    """
    Run every objective x channel combination through the simulator core at
    startup and assert its sanity. If any assertion fails, the server refuses
    to boot, exactly like the cohort invariants: a wrong simulation is a wrong
    number wearing a chart.
    """
    checks: list[str] = []
    combos = 0
    for objective in A.OBJECTIVE_CONVERSION:
        for forced in [None] + A.CHANNELS:
            r = _simulate_core(model, objective, ["26_35", "36_40"], None,
                               forced, None, True, True)
            f = r["funnel"]
            combos += 1
            assert f["sent"] >= f["delivered"] >= f["opened"] >= f["clicked"] >= f["converted"],                 f"{objective}/{forced}: funnel not monotonic"
            assert r["audience"]["addressable"] <= r["audience"]["objective_pool"],                 f"{objective}/{forced}: addressable exceeds pool"
            assert r["audience"]["control_group"] == round(
                r["audience"]["addressable"] * A.CONTROL_GROUP_SHARE),                 f"{objective}/{forced}: control group is not 5% flat"
            if objective == "app_install" and forced == "push":
                assert r["audience"]["addressable"] == 0,                     "app_install over push must address nobody (disjoint groups)"
            if forced is None:
                sel = r["decision"]["selected"]
                best = max(r["decision"]["channels"].values(), key=lambda c: c["total"])
                assert r["decision"]["channels"][sel]["total"] == best["total"],                     f"{objective}: recommended channel is not the rubric winner"
    checks.append(f"all {combos} objective x channel simulations are monotonic")
    checks.append("addressable never exceeds the objective pool")
    checks.append("control group is 5% flat in every simulation")
    checks.append("app-install over push addresses exactly nobody")
    checks.append("the recommended channel always wins the published rubric")
    conv = A.OBJECTIVE_CONVERSION
    assert conv["th_activation"] == round(A.TH_FUNNEL[-1][2] / A.TH_FUNNEL[0][2], 4)
    assert conv["hc_activation"] == round(A.HC_FUNNEL[-1][2] / A.HC_FUNNEL[0][2], 4)
    assert conv["hc_crosssell"] == A.HC_TO_TH_CROSSSELL_RATE
    checks.append("3 of 5 conversion rates reconcile to observed funnel anchors")
    return checks


SEGMENT_LABELS = {
    "base": "Full eligible base",
    "no_app": "No app (365d)",
    "hc_never_booked": "HC eligible, never booked",
    "th_never_booked": "TH eligible, never booked",
    "p0_dark_both": "P0 dark on both",
    "p0_dark_either": "P0 dark on either",
    "p1_dark_both": "P1 dark on both (DND)",
    "p1_dark_either": "P1 dark on either (DND)",
}


def _org(org: Optional[str]) -> Optional[str]:
    if org in (None, "", "all"):
        return None
    if org not in A.ORG_TYPE_SHARES:
        raise HTTPException(400, f"Unknown org type '{org}'")
    return org


# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    get_model()
    return {
        "status": "ok",
        "version": "2.0.0",
        "invariants_verified": len(_state["checks"]),
        "built_at": _state["built_at"],
    }


@app.get("/api/verification")
def verification():
    """Every invariant the model asserts. Shown in the UI methodology panel so
    the accuracy claim is checkable rather than asserted."""
    get_model()
    return {"label": "OBSERVED", "checks": _state["checks"],
            "sim_checks": _state["sim_checks"]}


@app.get("/api/overview")
def overview(org: Optional[str] = Query(None)):
    """Dashboard: base totals, cohort table, funnels, insights."""
    model = get_model()
    org_f = _org(org)
    logger.info(f"DATA_ACCESS: overview requested (org={org_f or 'all'})")

    totals = P.totals(model, org_f)
    cells = [c for c in model["cells"].values()
             if org_f is None or c["org"] == org_f]

    return {
        "label": "OBSERVED",
        "org_filter": org_f,
        "totals": totals,
        "cohorts": P.all_cohorts(model, org_f),
        "comparison": I.cohort_comparison(model, org_f),
        "insights": I.base_insights(model) if org_f is None else [],
        "activation": {
            "employee_rate": A.EMPLOYEE_ACTIVATION_RATE,
            "org_rate": A.ORG_ACTIVATION_RATE,
            "gap_points": A.ACTIVATION_GAP_POINTS,
            "targets": A.ADOPTION_TARGETS,
            "label": "OBSERVED",
        },
        "ct_live": {
            "metrics": ({**A.CT_LIVE, **_CT_RESYNC["live"]}
                        if _CT_RESYNC and _CT_RESYNC.get("live") else A.CT_LIVE),
            "scope": A.CT_LIVE_SCOPE,
            "pulled_at": (_CT_RESYNC["pulled_at"] if _CT_RESYNC
                          else A.CT_PULL_DATE.isoformat()),
            "is_resynced": bool(_CT_RESYNC and _CT_RESYNC.get("live")),
            "window_days": A.CT_WINDOW_DAYS,
            "dau_method": A.DAU_METHOD,
            "label": "OBSERVED",
        },
        # The documented reachability panel, straight from the source table.
        "segment_reachability": [
            {"key": k, "label": SEGMENT_LABELS[k], "users": v[0],
             "push": v[1], "email": v[2], "whatsapp": v[3]}
            for k, v in A.SEGMENT_REACHABILITY.items()
        ],
        "built_at": _state["built_at"],
    }


@app.get("/api/cohorts")
def cohorts(org: Optional[str] = Query(None)):
    model = get_model()
    org_f = _org(org)
    logger.info(f"DATA_ACCESS: cohort list requested (org={org_f or 'all'})")
    return {
        "label": "OBSERVED",
        "org_filter": org_f,
        "cohorts": P.all_cohorts(model, org_f),
        "org_types": [
            {"key": k, "label": A.ORG_TYPE_LABELS[k], "share": v,
             "note": A.SEGMENT_ADOPTION_NOTES.get(k)}
            for k, v in A.ORG_TYPE_SHARES.items()
        ],
        "org_share_is_modeled": A.ORG_SHARE_IS_MODELED,
    }


@app.get("/api/cohorts/{cohort_key}")
def cohort_detail(cohort_key: str, org: Optional[str] = Query(None)):
    model = get_model()
    org_f = _org(org)
    summary = P.cohort_summary(model, cohort_key, org_f)
    if not summary:
        raise HTTPException(404, f"Unknown cohort '{cohort_key}'")
    logger.info(f"DATA_ACCESS: cohort {cohort_key} detail (org={org_f or 'all'})")

    return {
        "label": "OBSERVED",
        "cohort": summary,
        "insights": I.cohort_insights(model, cohort_key, org_f),
        "base_totals": P.totals(model),
    }


@app.get("/api/methodology")
def methodology():
    """Provenance for every number. The four-way distinction made explicit."""
    get_model()
    return {
        "provenance": A.provenance(),
        "checks": _state["checks"],
        "mau_scoped": {
            "value": P.MAU_SCOPED,
            "provenance": P.MAU_SCOPED_PROVENANCE,
        },
        "reach_decomposed": A.REACH_DECOMPOSED,
        "segment_reachability": {
            k: {"users": v[0], "push": v[1], "email": v[2], "whatsapp": v[3]}
            for k, v in A.SEGMENT_REACHABILITY.items()
        },
        "funnels": {
            "th": [{"stage": s, "event": e, "count": n} for s, e, n in A.TH_FUNNEL],
            "hc": [{"stage": s, "event": e, "count": n} for s, e, n in A.HC_FUNNEL],
            "window": "120 days, active + non-test organisations",
        },
    }


# ---------------------------------------------------------------------------
# Simulator
# ---------------------------------------------------------------------------

class SimRequest(BaseModel):
    objective: str
    cohort_keys: list[str]
    org: Optional[str] = None
    channel: Optional[str] = None
    send_hour: Optional[int] = None
    exclude_dnd: bool = True
    exclude_no_app_for_push: bool = True


@app.get("/api/simulate/options")
def simulate_options():
    get_model()
    return {
        "objectives": [
            {"key": "th_activation", "label": "Telehealth activation",
             "desc": "First consultation for people who have never booked"},
            {"key": "hc_activation", "label": "Health checkup activation",
             "desc": "First checkup booking"},
            {"key": "app_install", "label": "App install",
             "desc": "Move the no-app segment onto the app"},
            {"key": "reengagement", "label": "Re-engagement",
             "desc": "Installed but quiet for 30 days or more"},
            {"key": "hc_crosssell", "label": "HC to TH cross-sell",
             "desc": "Telehealth prompt after a checkup report view"},
        ],
        "cohorts": [{"key": c["key"], "label": c["label"]} for c in A.AGE_COHORTS],
        "org_types": [{"key": k, "label": A.ORG_TYPE_LABELS[k]}
                      for k in A.ORG_TYPE_SHARES],
        "channels": [{"key": k, "label": A.CHANNEL_LABELS[k]} for k in A.CHANNELS],
        "control_group_share": A.CONTROL_GROUP_SHARE,
    }


def _simulate_core(model: dict, objective: str, cohort_keys: list[str],
                   org_f, forced_channel, send_hour_in,
                   exclude_dnd: bool, exclude_no_app_for_push: bool) -> dict:
    """The whole simulation, callable by the endpoint AND the startup sweep."""
    cells = [c for c in model["cells"].values()
             if c["cohort"] in cohort_keys
             and (org_f is None or c["org"] == org_f)]
    if not cells:
        raise HTTPException(400, "That combination selects nobody")

    s = lambda k: sum(c[k] for c in cells)  # noqa: E731
    cohort_total, app_total = s("total"), s("app")

    # -- Objective determines the eligible pool inside the selection -------
    # pool_is_app records WHICH population the pool is drawn from, because
    # reachability has to be measured against that same population. An
    # app-install campaign targets people without the app, so intersecting it
    # with app-installed push reach would be intersecting two disjoint groups.
    if objective == "app_install":
        pool, pool_desc, pool_is_app = s("no_app"), "no app install signal", False
    elif objective == "reengagement":
        pool, pool_desc, pool_is_app = (
            s("app_dormant"), "app installed, quiet 30 days or more", True)
    elif objective == "th_activation":
        pool = app_total - s("th_booked")
        pool_desc, pool_is_app = "app installed, never booked telehealth", True
    elif objective == "hc_activation":
        pool = app_total - s("hc_booked")
        pool_desc, pool_is_app = "app installed, never booked a checkup", True
    else:  # hc_crosssell
        pool = s("hc_booked")
        pool_desc, pool_is_app = "booked a checkup, cross-sell on report view", True

    # -- Channel: pick the one that actually reaches the most of that pool --
    # Reach is taken from the app or no-app component to match the pool, then
    # DND is applied proportionally, then capped by the pool itself.
    dnd_keep = (s("not_dnd") / cohort_total) if cohort_total else 0.0
    component = "app" if pool_is_app else "no_app"

    channel_options = {}
    for ch in A.CHANNELS:
        reach = s(f"reach_{ch}_{component}")
        if ch == "push" and not pool_is_app:
            # The only push-reachable people without the app are stale tokens
            # on uninstalled apps. Excluding them is the default and correct.
            if exclude_no_app_for_push:
                reach = 0
        if exclude_dnd:
            reach = round(reach * dnd_keep)
        channel_options[ch] = min(reach, pool)

    # Weighted rubric over six published parameters (decisions.CHANNEL_RULE),
    # not argmax(reach). The full breakdown ships with the response so the UI
    # can show exactly how the recommendation was computed.
    decision = D.score_channels(pool, channel_options, dnd_keep)
    if forced_channel:
        channel = forced_channel
        channel_label = "OBSERVED"
    else:
        channel = decision["selected"]
        channel_label = "RECOMMENDED"

    addressable = channel_options[channel]
    control = round(addressable * A.CONTROL_GROUP_SHARE)
    sent = addressable - control

    # -- Funnel projection, PREDICTED, low confidence by construction -----
    b = A.CHANNEL_BENCHMARKS[channel]
    conv = A.OBJECTIVE_CONVERSION[objective]
    delivered = round(sent * b["delivery"])
    opened = round(delivered * b["open"])
    clicked = round(opened * b["click"])
    converted = round(clicked * conv)

    hours = [A.PEAK_HOUR[k] for k in cohort_keys]
    send_hour = send_hour_in if send_hour_in is not None else max(set(hours), key=hours.count)

    warnings = []
    if channel == "push":
        stale = s("reach_push_no_app")
        if not pool_is_app:
            warnings.append(
                f"This objective targets people without the app, so push has no "
                f"legitimate audience here, the only push-reachable users in "
                f"that pool are {stale:,} stale tokens on uninstalled apps. "
                + ("They are excluded." if exclude_no_app_for_push
                   else "They are currently INCLUDED and will deliver nothing.")
            )
        elif stale > 0:
            warnings.append(
                f"Push reachability across this selection reads "
                f"{s('reach_push'):,}, but {stale:,} of those sit in the no-app "
                f"segment as stale tokens. This estimate uses only the "
                f"{s('reach_push_app'):,} with an app install signal."
            )
    if addressable == 0:
        warnings.append(
            f"{A.CHANNEL_LABELS[channel]} reaches nobody in this pool. Pick a "
            f"different channel or a different objective."
        )
    if objective == "hc_crosssell":
        warnings.append(
            f"Cross-sell converts best triggered on report view, not on a "
            f"schedule, {A.HC_TO_TH_CROSSSELL_RATE:.1%} convert unprompted "
            f"from that moment."
        )
    if not exclude_dnd:
        warnings.append(
            f"DND is not being excluded. {s('dnd'):,} people in this selection "
            f"carry the suppression flag and must not receive campaign sends."
        )

    return {
        "label": "PREDICTED",
        "confidence": "low",
        "confidence_reason": A.BENCHMARK_PROVENANCE,

        "selection": {
            "cohorts": [P.COHORT_BY_KEY[k]["label"] for k in cohort_keys],
            "org": A.ORG_TYPE_LABELS[org_f] if org_f else "All org types",
            "cohort_total": cohort_total,
            "app_in_selection": app_total,
            "dnd_in_selection": s("dnd"),
            "label": "DERIVED",
        },
        "audience": {
            "objective_pool": pool,
            "pool_description": pool_desc,
            "addressable": addressable,
            "control_group": control,
            "sent": sent,
            "label": "DERIVED",
        },
        "decision": decision,
        "conversion_provenance": {
            "kind": A.CONVERSION_PROVENANCE[objective][0],
            "basis": A.CONVERSION_PROVENANCE[objective][1],
        },
        "channel": {
            "selected": channel,
            "selected_label": A.CHANNEL_LABELS[channel],
            "label": channel_label,
            "options": {
                ch: {
                    "label": A.CHANNEL_LABELS[ch],
                    "addressable": v,
                    "share_of_pool": round(v / pool, 4) if pool else 0.0,
                }
                for ch, v in channel_options.items()
            },
        },
        "funnel": {
            "sent": sent,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "converted": converted,
            "delivery_rate": round(delivered / sent, 4) if sent else 0.0,
            "open_rate": round(opened / delivered, 4) if delivered else 0.0,
            "click_rate": round(clicked / opened, 4) if opened else 0.0,
            "conversion_rate": round(converted / sent, 6) if sent else 0.0,
            "click_to_convert": conv,
            "label": "PREDICTED",
        },
        "funnel_explain": T.funnel_explain(channel, objective, sent, {
            "sent": sent, "delivered": delivered, "opened": opened,
            "clicked": clicked, "converted": converted,
            "conversion_rate": round(converted / sent, 6) if sent else 0.0,
        }),
        "timing_detail": T.recommend(channel, cohort_keys),
        "timing": {
            "send_hour": send_hour,
            "note": f"Observed booking peaks are 11:00 and 18:00-19:00 IST; this slot is {send_hour}:00",
            "label": "RECOMMENDED" if send_hour_in is None else "OBSERVED",
        },
        "warnings": warnings,
    }




@app.post("/api/simulate")
def simulate(req: SimRequest):
    """
    Size an audience from the real cohort model, then project a funnel.

    Audience sizing is DERIVED, exact counts out of the model. The funnel is
    PREDICTED at low confidence; click-to-convert is anchored to the OBSERVED
    homepage-to-booked funnel rates wherever one exists (three of the five
    objectives), and stays a labelled prior for the other two.
    """
    model = get_model()
    org_f = _org(req.org)

    if req.objective not in A.OBJECTIVE_CONVERSION:
        raise HTTPException(400, f"Unknown objective '{req.objective}'")
    if not req.cohort_keys:
        raise HTTPException(400, "Select at least one age cohort")
    unknown = set(req.cohort_keys) - set(P.COHORT_KEYS)
    if unknown:
        raise HTTPException(400, f"Unknown cohort(s): {sorted(unknown)}")
    if req.channel and req.channel not in A.CHANNELS:
        raise HTTPException(400, f"Unknown channel '{req.channel}'")

    logger.info(
        f"DATA_ACCESS: simulation objective={req.objective} "
        f"cohorts={req.cohort_keys} org={org_f or 'all'} channel={req.channel}"
    )
    return _simulate_core(model, req.objective, req.cohort_keys, org_f,
                          req.channel, req.send_hour,
                          req.exclude_dnd, req.exclude_no_app_for_push)


# ---------------------------------------------------------------------------
# Copy studio: deterministic generation from the approved library
# ---------------------------------------------------------------------------

class CopyGenRequest(BaseModel):
    objective: str
    cohort_keys: list[str]
    channel: str
    angle: Optional[str] = None
    # Server-produced audience size from a prior /api/simulate run. Passing it
    # back lets each variant carry a predicted funnel in absolute counts.
    audience_sent: Optional[int] = None


class CopyAnalyzeRequest(BaseModel):
    text: str
    title: Optional[str] = None
    channel: str
    objective: str
    cohort_key: str
    audience_sent: Optional[int] = None


class AssistantRequest(BaseModel):
    message: str
    cohort_keys: list[str] = []
    org: Optional[str] = None
    objective: Optional[str] = None
    channel: Optional[str] = None
    tuning: Optional[dict] = None


@app.post("/api/assistant")
def assistant_answer(req: AssistantRequest):
    """Grounded campaign Q&A. Deterministic retrieval over the verified model,
    every reply scored against the published 10-parameter rubric. Tuning
    parameters change depth and framing, never whether a figure is labelled."""
    model = get_model()
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(400, "Empty message")
    if len(msg) > 600:
        raise HTTPException(400, "Keep questions under 600 characters")
    org_f = _org(req.org)
    logger.info(f"DATA_ACCESS: assistant query intents on cohorts={req.cohort_keys}")
    return SIG.answer(model, msg, req.cohort_keys, org_f, req.objective,
                      req.channel, tuning=req.tuning)


@app.get("/api/rules")
def rules():
    """The decision rubrics: every recommendation's parameters and weights."""
    get_model()
    reg = D.registry()
    reg["rules"] = [r for r in reg["rules"] if r["id"] != "assistant_quality"]
    reg["rules"] += [SIG.RUBRIC, T.TIMING_RULE, T.FUNNEL_RULE]
    return reg


@app.get("/api/signal/suggestions")
def signal_suggestions(cohorts: Optional[str] = Query(None)):
    get_model()
    keys = [k for k in (cohorts or "").split(",") if k] or ["26_35"]
    return {"suggestions": SIG.suggestions(keys)}


@app.get("/api/intel/{cohort_key}")
def cohort_intelligence(cohort_key: str):
    """Clinical and behavioural evidence for one cohort: specialty mix,
    biomarker abnormality, real booking clock. All OBSERVED."""
    model = get_model()
    if cohort_key not in P.COHORT_KEYS:
        raise HTTPException(404, f"Unknown cohort '{cohort_key}'")
    logger.info(f"DATA_ACCESS: cohort intelligence for {cohort_key} (aggregates only)")
    summary = P.cohort_summary(model, cohort_key, None)
    return {
        "label": "OBSERVED",
        "cohort": cohort_key,
        "provenance": CI.provenance(),
        "specialty_mix": CI.specialty_mix(cohort_key),
        "rising_specialties": CI.rising_specialties(cohort_key),
        "biomarkers": CI.biomarkers(cohort_key),
        "steepest_gradients": CI.steepest_gradient(3),
        "engagement": CI.th_engagement(cohort_key),
        "booking_clock": CI.booking_clock(cohort_key),
        "consulter_vs_base": CI.consulter_vs_base(
            cohort_key, summary.get("share_of_base", 0) if summary else 0),
        "gender": CI.gender_split(),
    }


@app.get("/api/timing")
def timing_recommendations(cohorts: Optional[str] = Query(None)):
    """Send-time recommendations per channel, with the observed booking clock
    and the arithmetic behind each one."""
    get_model()
    keys = [k for k in (cohorts or "").split(",") if k in P.COHORT_KEYS] or ["26_35"]
    return {"label": "RECOMMENDED", "cohorts": keys,
            "channels": T.all_channels(keys), "rule": T.TIMING_RULE}


@app.get("/api/copy/options")
def copy_options():
    get_model()
    return CE.options()


@app.post("/api/copy/generate")
def copy_generate(req: CopyGenRequest):
    """Generate channel-disciplined variants from the approved copy library."""
    get_model()
    logger.info(
        f"DATA_ACCESS: copy generation objective={req.objective} "
        f"cohorts={req.cohort_keys} channel={req.channel} angle={req.angle}"
    )
    try:
        return CE.generate(req.objective, req.cohort_keys, req.channel,
                           angle=req.angle, audience_sent=req.audience_sent)
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/copy/analyze")
def copy_analyze(req: CopyAnalyzeRequest):
    """Analyze pasted copy against the same discipline rules."""
    get_model()
    if req.channel not in A.CHANNELS:
        raise HTTPException(400, f"Unknown channel '{req.channel}'")
    if req.cohort_key not in CE.BANDS:
        raise HTTPException(400, f"Unknown cohort '{req.cohort_key}'")
    if req.objective not in A.OBJECTIVE_CONVERSION:
        raise HTTPException(400, f"Unknown objective '{req.objective}'")
    logger.info(f"DATA_ACCESS: copy analysis channel={req.channel} objective={req.objective}")
    analysis = CE.analyze(req.text, req.channel, req.cohort_key, req.objective,
                          title=req.title)
    prediction = CE.predict(analysis, req.channel, req.objective,
                            audience_sent=req.audience_sent)
    return {"label": "DERIVED", "analysis": analysis, "prediction": prediction}


class ResyncRequest(BaseModel):
    requested_by: Optional[str] = None


@app.get("/api/signal/tuning")
def signal_tuning():
    """The tuning parameters SIGNAL exposes, and what is deliberately locked."""
    return SIG.TUNING


@app.post("/api/ct/resync")
def ct_resync(req: Optional[ResyncRequest] = None):
    """
    Re-pull the live usage figures from CleverTap on demand.

    Governance: read-only counts endpoints only, never a profile row. Every
    window is bounded and none exceeds a year. The pull is audit-logged with
    who asked, when, and exactly which event and window was queried, per the
    audit-logging requirement for data-access features.

    The response also states what a resync deliberately cannot refresh, so
    pressing it never implies the whole dashboard was just re-verified.
    """
    global _CT_RESYNC
    import ct_connector as CT

    who = (req.requested_by if req and req.requested_by else "dashboard")
    logger.info("DATA_ACCESS: ct resync requested by=%s at=%s",
                who, datetime.now(timezone.utc).isoformat())
    result = CT.resync(requested_by=who)
    if result.get("ok"):
        _CT_RESYNC = result
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
