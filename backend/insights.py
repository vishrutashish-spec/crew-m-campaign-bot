"""
Deterministic insight engine.

Every insight is a pure function of the cohort model. No LLM, no randomness,
no thresholds tuned to make a demo look good. Same numbers in, same insights
out, and each one carries the arithmetic that produced it so a PMM can check
the claim rather than trust it.

Insights are typed by the four-way distinction the project mandates:
  OBSERVED   , a fact read off the source of record
  DERIVED    , exact arithmetic on observed facts
  RECOMMENDED, an action the rules suggest, given the facts
  (PREDICTED is reserved for the simulator, which is the only thing that
   forecasts anything.)

--- Data access note (governance) ---
Operates only on aggregate cohort counts already loaded in memory. Reads no
user records and moves no data anywhere.
"""

from __future__ import annotations

import anchors as A
import population as P


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _n(x: int) -> str:
    return f"{x:,}"


# ---------------------------------------------------------------------------
# Base-wide insights
# ---------------------------------------------------------------------------

def base_insights(model: dict) -> list[dict]:
    t = P.totals(model)
    out: list[dict] = []

    # -- The push illusion. The single most actionable fact in the model. ----
    push = t["reach"]["push"]
    real_push = sum(c["reach_push_app"] for c in model["cells"].values())
    stale = push["count"] - real_push
    out.append({
        "id": "push_stale_tokens",
        "kind": "DERIVED",
        "severity": "high",
        "title": f"{_n(stale)} of your {_n(push['count'])} push-reachable users cannot actually receive push",
        "body": (
            f"Push reachability reads {_pct(push['of_total'])} of the base, but only "
            f"{_n(real_push)} of those people have an app install signal. The remaining "
            f"{_n(stale)} sit in the no-app segment, which still reports 11% push "
            f"reachability because App Uninstalled never fires in this account, so "
            f"tokens are never invalidated. Those sends will report as delivered and "
            f"land nowhere."
        ),
        "arithmetic": (
            f"{_n(push['count'])} push-reachable - {_n(real_push)} with app install "
            f"signal = {_n(stale)} stale tokens"
        ),
        "action": "Exclude the no-app segment from push campaigns and measure push reach against the app base only.",
    })

    # -- Channel hierarchy -------------------------------------------------
    wa, em = t["reach"]["whatsapp"], t["reach"]["email"]
    ratio = wa["count"] / max(real_push, 1)
    out.append({
        "id": "channel_hierarchy",
        "kind": "OBSERVED",
        "severity": "high",
        "title": f"WhatsApp reaches {ratio:.1f}x more people than push actually can",
        "body": (
            f"WhatsApp reaches {_n(wa['count'])} ({_pct(wa['of_total'])}) and email "
            f"{_n(em['count'])} ({_pct(em['of_total'])}), neither of which needs the app. "
            f"Real push capacity is {_n(real_push)}. Any campaign whose primary channel "
            f"is push is choosing the smallest audience available."
        ),
        "arithmetic": f"{_n(wa['count'])} WhatsApp / {_n(real_push)} real push = {ratio:.1f}x",
        "action": "Lead with WhatsApp for anything aimed at the whole base. Reserve push for the 30-day-active app cohort.",
    })

    # -- The no-app wall ---------------------------------------------------
    out.append({
        "id": "no_app_wall",
        "kind": "OBSERVED",
        "severity": "high",
        "title": f"{_pct(t['no_app_share'])} of the eligible base has no app install signal",
        "body": (
            f"{_n(t['no_app'])} of {_n(t['eligible'])} people show no install signal in "
            f"365 days. Every in-app funnel, telehealth, health checkup, HRA, is "
            f"invisible to them. This is an acquisition gate, not an engagement problem: "
            f"no amount of in-app optimisation moves it."
        ),
        "arithmetic": f"{_n(t['no_app'])} / {_n(t['eligible'])} = {_pct(t['no_app_share'])}",
        "action": "Treat app install as its own objective with WhatsApp and email as the only viable channels.",
    })

    # -- Activation gap ----------------------------------------------------
    out.append({
        "id": "activation_gap",
        "kind": "OBSERVED",
        "severity": "high",
        "title": f"{A.ACTIVATION_GAP_POINTS}-point gap between org and employee activation",
        "body": (
            f"About {_pct(A.ORG_ACTIVATION_RATE)} of organisations have at least one "
            f"booking, but only {_pct(A.EMPLOYEE_ACTIVATION_RATE)} of employees ever "
            f"book. The benefit is switched on almost everywhere and used almost nowhere. "
            f"That gap is awareness and access inside the workplace, not org-level sales."
        ),
        "arithmetic": (
            f"{_pct(A.ORG_ACTIVATION_RATE)} org - {_pct(A.EMPLOYEE_ACTIVATION_RATE)} "
            f"employee = {A.ACTIVATION_GAP_POINTS} points"
        ),
        "action": "Target employees inside already-activated orgs, the access is there, the awareness is not.",
    })

    # -- Installed but quiet ----------------------------------------------
    quiet = t["app_dormant"]
    out.append({
        "id": "installed_quiet",
        "kind": "DERIVED",
        "severity": "medium",
        "title": f"{_n(quiet)} people have the app but have not opened it in 30 days",
        "body": (
            f"Of {_n(t['app'])} with an install signal, {_n(t['mau'])} were active in the "
            f"last 30 days, leaving {_n(quiet)} installed and quiet. These are the "
            f"cheapest users to reactivate, the install barrier is already cleared and "
            f"push still works on them."
        ),
        "arithmetic": f"{_n(t['app'])} app - {_n(t['mau'])} active 30d = {_n(quiet)}",
        "action": "Run re-engagement on this group via push plus WhatsApp, not app-install messaging.",
    })

    # -- Funnel leak, computed not hardcoded -------------------------------
    for prod, funnel, label in (("th", t["th_funnel"], "Telehealth"),
                                ("hc", t["hc_funnel"], "Health Checkup")):
        worst = min(funnel[1:], key=lambda s: s["from_prev"])
        idx = funnel.index(worst)
        prev = funnel[idx - 1]
        lost = prev["count"] - worst["count"]
        out.append({
            "id": f"{prod}_worst_step",
            "kind": "OBSERVED",
            "severity": "high" if worst["from_prev"] < 0.4 else "medium",
            "title": f"{label}: biggest drop is {prev['stage']} to {worst['stage']} ({_pct(worst['from_prev'])} continue)",
            "body": (
                f"{_n(prev['count'])} reached {prev['stage']} and {_n(worst['count'])} "
                f"reached {worst['stage']}, {_n(lost)} people lost at one step, the "
                f"largest single leak in the {label} funnel. End to end, "
                f"{_pct(funnel[-1]['cumulative'])} of homepage viewers book."
            ),
            "arithmetic": (
                f"{_n(worst['count'])} / {_n(prev['count'])} = {_pct(worst['from_prev'])} "
                f"continue, {_n(lost)} lost"
            ),
            "action": f"Fix the {prev['stage']} to {worst['stage']} step before spending on more {label} traffic.",
        })

    # -- HC structural ceiling --------------------------------------------
    out.append({
        "id": "hc_ceiling",
        "kind": "OBSERVED",
        "severity": "low",
        "title": "Health Checkup repeat rate is capped by design, not by performance",
        "body": (
            f"Plans include roughly {A.HC_BOOKINGS_PER_USER:.0f} free checkup per year, "
            f"so repeat bookings are structurally limited. Telehealth runs about "
            f"{A.TH_CONSULTS_PER_YEAR:.0f} consults a year once a user starts. Reading "
            f"HC repeat rate as a failure leads to the wrong campaign."
        ),
        "arithmetic": "One free checkup per plan year, a ceiling, not a conversion problem.",
        "action": "Message HC as 'use the one in your plan', never 'book again'.",
    })

    # -- Cross-sell bridge -------------------------------------------------
    out.append({
        "id": "crosssell_bridge",
        "kind": "OBSERVED",
        "severity": "medium",
        "title": f"{_pct(A.HC_TO_TH_CROSSSELL_RATE)} of health-checkup report viewers go on to book telehealth",
        "body": (
            f"The report-viewed moment is the strongest cross-sell signal in the product: "
            f"someone has just seen their own numbers. {_pct(A.HC_TO_TH_CROSSSELL_RATE)} "
            f"convert to a telehealth booking from there without any prompting."
        ),
        "arithmetic": f"HC report viewed to TH booking = {_pct(A.HC_TO_TH_CROSSSELL_RATE)}",
        "action": "Trigger a telehealth prompt on report view rather than on a calendar schedule.",
    })

    return out


# ---------------------------------------------------------------------------
# Cohort-level insights
# ---------------------------------------------------------------------------

def cohort_insights(model: dict, cohort_key: str,
                    org_filter: str | None = None) -> list[dict]:
    c = P.cohort_summary(model, cohort_key, org_filter)
    if not c:
        return []
    base = P.totals(model)
    out: list[dict] = []

    # -- App ownership vs the base ----------------------------------------
    delta = c["app_share"] - base["app_share"]
    direction = "above" if delta > 0 else "below"
    out.append({
        "id": "app_vs_base",
        "kind": "DERIVED",
        "severity": "high" if abs(delta) > 0.05 else "medium",
        "title": f"App ownership is {abs(delta) * 100:.1f} points {direction} the base average",
        "body": (
            f"{_pct(c['app_share'])} of the {c['label']} cohort has an install signal, "
            f"against {_pct(base['app_share'])} across the whole base. "
            + (f"Push is a viable primary channel here."
               if delta > 0.03 else
               f"Push will underperform badly in this cohort, lead with WhatsApp.")
        ),
        "arithmetic": (
            f"{_n(c['app'])} / {_n(c['total'])} = {_pct(c['app_share'])} vs base "
            f"{_pct(base['app_share'])}"
        ),
        "action": ("Push plus WhatsApp." if delta > 0.03
                   else "WhatsApp first; treat push as incremental only."),
    })

    # -- Real vs apparent push capacity in this cohort ---------------------
    cells = [x for x in model["cells"].values()
             if x["cohort"] == cohort_key
             and (org_filter is None or x["org"] == org_filter)]
    real_push = sum(x["reach_push_app"] for x in cells)
    apparent = c["reach"]["push"]["count"]
    if apparent > real_push:
        out.append({
            "id": "cohort_push_real",
            "kind": "DERIVED",
            "severity": "high",
            "title": f"Real push capacity here is {_n(real_push)}, not {_n(apparent)}",
            "body": (
                f"The reachability panel reports {_n(apparent)} push-reachable in this "
                f"cohort, but only {_n(real_push)} have an app install signal. Plan "
                f"against {_n(real_push)} or the campaign will look like it "
                f"underperformed when it simply never arrived."
            ),
            "arithmetic": f"{_n(apparent)} reported - {_n(real_push)} with app = {_n(apparent - real_push)} stale",
            "action": "Size push campaigns for this cohort off the app base.",
        })

    # -- Device skew -------------------------------------------------------
    if c["app"] > 0:
        out.append({
            "id": "device_skew",
            "kind": "DERIVED",
            "severity": "low",
            "title": f"{_pct(c['android_share_of_app'])} Android / {_pct(c['ios_share_of_app'])} iOS among app users",
            "body": (
                f"{_n(c['android'])} Android and {_n(c['ios'])} iOS devices in this "
                f"cohort's app base. iOS requires explicit notification opt-in, so an "
                f"iOS-heavy cohort loses more push reach than the install numbers "
                f"suggest."
            ),
            "arithmetic": f"{_n(c['android'])} Android + {_n(c['ios'])} iOS = {_n(c['app'])} app users",
            "action": "Rich-media creative renders differently across the two, check both before send.",
            "modeled": True,
        })

    # -- Dominant org type -------------------------------------------------
    if c["org_breakdown"]:
        top_org = max(c["org_breakdown"].items(), key=lambda kv: kv[1]["total"])
        ok, ov = top_org
        out.append({
            "id": "org_concentration",
            "kind": "DERIVED",
            "severity": "medium",
            "title": f"{_pct(ov['share_of_cohort'])} of this cohort sits in {ov['label']}",
            "body": (
                f"{_n(ov['total'])} of {_n(c['total'])} people. {ov['note'] or ''} "
                f"App ownership inside this org type is {_pct(ov['app_share'])} and "
                f"{_n(ov['dnd'])} are DND-suppressed."
            ).strip(),
            "arithmetic": f"{_n(ov['total'])} / {_n(c['total'])} = {_pct(ov['share_of_cohort'])}",
            "action": f"Segment by {ov['label']} first, it dominates this cohort's behaviour.",
            "modeled": True,
        })

    # -- Booking performance vs base --------------------------------------
    for prod, booked, name in (("th", c["th_booked"], "Telehealth"),
                               ("hc", c["hc_booked"], "Health Checkup")):
        rate = c[f"{prod}_booked_of_app"]
        base_rate = P._rate(base[f"{prod}_booked"], base["app"])
        d = rate - base_rate
        out.append({
            "id": f"{prod}_vs_base",
            "kind": "DERIVED",
            "severity": "medium" if abs(d) > 0.01 else "low",
            "title": f"{name} booking is {_pct(rate)} of app users here vs {_pct(base_rate)} base-wide",
            "body": (
                f"{_n(booked)} bookings from {_n(c['app'])} app users in this cohort. "
                + ("Above average, this cohort responds; give it more volume."
                   if d > 0.005 else
                   "Below average, headroom exists but the message has not landed yet."
                   if d < -0.005 else
                   "In line with the base.")
            ),
            "arithmetic": f"{_n(booked)} / {_n(c['app'])} = {_pct(rate)}",
            "action": (f"Scale {name} spend into this cohort." if d > 0.005
                       else f"Test new {name} messaging here before scaling spend."),
        })

    # -- Send time --------------------------------------------------------
    out.append({
        "id": "send_time",
        "kind": "RECOMMENDED",
        "severity": "low",
        "title": f"Send at {c['peak_hour']}:00 for this cohort",
        "body": (
            f"Real booking intent is twin-peaked at 11:00 and 18:00 to 19:00 IST, "
            f"measured on 133,218 consults. The often-quoted 20:00 to 23:00 window "
            f"carries under a fifth of bookings."
        ),
        "arithmetic": "Observed booking clock, 133,218 consults in IST, cohort-adjusted.",
        "action": f"Schedule for {c['peak_hour']}:00 local.",
        "modeled": True,
    })

    # -- DND --------------------------------------------------------------
    if c["dnd"] > 0:
        out.append({
            "id": "dnd",
            "kind": "OBSERVED",
            "severity": "medium" if c["dnd_share"] > 0.02 else "low",
            "title": f"{_n(c['dnd'])} people in this cohort are DND-suppressed",
            "body": (
                f"{_pct(c['dnd_share'])} of the cohort. DND is applied at whole-org "
                f"level and unconditionally, every campaign has to check the flag "
                f"itself, it is not enforced centrally. These users are P1, never P0."
            ),
            "arithmetic": f"{_n(c['dnd'])} / {_n(c['total'])} = {_pct(c['dnd_share'])}",
            "action": "Add an explicit is_in_DND_CT != true condition to every segment.",
        })

    return out


def cohort_comparison(model: dict, org_filter: str | None = None) -> dict:
    """Cross-cohort comparison, which cohort leads on each metric."""
    cohorts = [c for c in P.all_cohorts(model, org_filter) if c]
    if not cohorts:
        return {}

    def leader(key, fn):
        best = max(cohorts, key=fn)
        return {"cohort": best["label"], "value": fn(best), "key": best["key"]}

    return {
        "largest": leader("total", lambda c: c["total"]),
        "highest_app_share": leader("app_share", lambda c: c["app_share"]),
        "most_app_users": leader("app", lambda c: c["app"]),
        "highest_th_rate": leader("th", lambda c: c["th_booked_of_app"]),
        "highest_hc_rate": leader("hc", lambda c: c["hc_booked_of_app"]),
        "most_dormant": leader("dormant", lambda c: c["app_dormant"]),
        "biggest_no_app": leader("no_app", lambda c: c["no_app"]),
        "highest_ios": leader("ios", lambda c: c["ios_share_of_app"]),
    }
