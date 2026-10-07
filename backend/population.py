"""
Deterministic cohort model for Crew M.

This is NOT a random sample. It is an exact contingency table.

Why that matters: a sampled population drifts. Run it twice and the numbers
move, cohort subtotals stop adding up to the headline, and nobody can tell a
real finding from sampling noise. Every count here comes from integer
apportionment (largest-remainder), so:

  * cohort subtotals sum EXACTLY to the 956,050 eligible base
  * org splits within a cohort sum EXACTLY to that cohort
  * app / no-app, device, gender, DND all sum EXACTLY to their anchors
  * every funnel stage sums EXACTLY to its documented count
  * channel reachability sums EXACTLY to the observed base percentages
  * the same inputs always produce byte-identical output

verify() asserts every one of those at startup. If the model and an anchor ever
disagree the server refuses to boot rather than serve a wrong number.

--- Data access note (governance) ---
What: aggregate cohort counts derived from documented segment totals. No
user-level data is read, stored or moved; this module operates purely on
integer totals and never touches PII.
"""

from __future__ import annotations

import anchors as A


# ---------------------------------------------------------------------------
# Exact integer apportionment
# ---------------------------------------------------------------------------

def allocate(total: int, weights: dict[str, float]) -> dict[str, int]:
    """
    Split `total` across `weights` so the parts sum to exactly `total`.

    Largest-remainder: floor each share, then give the leftover units to the
    keys with the largest fractional remainders. Ties break on key name, so the
    result is fully deterministic.
    """
    keys = list(weights)
    if total <= 0:
        return {k: 0 for k in keys}
    wsum = sum(weights.values())
    if wsum <= 0:
        return {k: 0 for k in keys}

    exact = {k: total * weights[k] / wsum for k in keys}
    out = {k: int(exact[k]) for k in keys}
    short = total - sum(out.values())
    if short:
        for k in sorted(keys, key=lambda k: (-(exact[k] - out[k]), k))[:short]:
            out[k] += 1
    return out


def allocate_capped(total: int, weights: dict[str, float],
                    caps: dict[str, int]) -> dict[str, int]:
    """
    allocate(), but no key may exceed its cap.

    Water-filling: allocate proportionally, clamp anything over cap, redistribute
    the freed units among keys with headroom, repeat. Needed wherever a quantity
    is nested inside another, MAU inside a cell's app base, a funnel stage
    inside the app base it is drawn from.
    """
    total = min(total, sum(caps.get(k, 0) for k in weights))
    out = {k: 0 for k in weights}
    active = {k: w for k, w in weights.items() if w > 0 and caps.get(k, 0) > 0}

    while total > 0 and active:
        share = allocate(total, active)
        overflow, capped_now = 0, []
        for k, v in share.items():
            room = caps[k] - out[k]
            if v >= room:
                out[k] = caps[k]
                overflow += v - room
                capped_now.append(k)
            else:
                out[k] += v
        total = overflow
        for k in capped_now:
            active.pop(k, None)
        if not capped_now:
            break
    return out


# ---------------------------------------------------------------------------
# DERIVED, 30-day-active users inside the eligible base.
#
# CleverTap's MAU (147,003) is account-wide and cannot be used as a scoped
# anchor. What transfers is the RATIO: account-wide, 147,003 of 397,301 annual
# actives were active in the last 30 days = 37.0%. Applying that same ratio to
# the scoped app base gives the eligible-base MAU. Flagged DERIVED, not
# OBSERVED, because it is a ratio transfer rather than a measurement.
# ---------------------------------------------------------------------------

MAU_RATIO = A.CT_LIVE["mau_30d"] / A.CT_LIVE["annual_active_users"]   # 0.3700
MAU_SCOPED = round(A.APP_INSTALLED * MAU_RATIO)                        # ~80,262
MAU_SCOPED_PROVENANCE = (
    f"DERIVED. CleverTap MAU ({A.CT_LIVE['mau_30d']:,}) is account-wide and "
    f"cannot be divided by the eligible base. The 30-day-active share of "
    f"annual actives ({MAU_RATIO:.1%}) is applied to the scoped app base "
    f"({A.APP_INSTALLED:,}) to give {MAU_SCOPED:,} active users inside the "
    f"eligible base."
)

COHORT_KEYS = [c["key"] for c in A.AGE_COHORTS]
COHORT_BY_KEY = {c["key"]: c for c in A.AGE_COHORTS}
ORG_KEYS = list(A.ORG_TYPE_SHARES)


def _cid(cohort: str, org: str) -> str:
    return f"{cohort}|{org}"


# ---------------------------------------------------------------------------
# Build, 6 cohorts x 4 org types = 24 cells, all exact integers
# ---------------------------------------------------------------------------

def build() -> dict:
    cohort_total = allocate(A.TOTAL_ELIGIBLE, A.AGE_COHORT_SHARES)

    cells: dict[str, dict] = {}
    for ck in COHORT_KEYS:
        org_split = allocate(cohort_total[ck], A.ORG_TYPE_SHARES)
        for org in ORG_KEYS:
            cells[_cid(ck, org)] = {
                "cohort": ck, "org": org, "total": org_split[org],
            }

    # -- App install signal: exact to APP_INSTALLED (216,924) ---------------
    app = allocate_capped(
        A.APP_INSTALLED,
        {k: c["total"] * A.APP_PROPENSITY[c["cohort"]] for k, c in cells.items()},
        {k: c["total"] for k, c in cells.items()},
    )
    for k, c in cells.items():
        c["app"] = app[k]
        c["no_app"] = c["total"] - c["app"]

    # -- 30-day active: exact to MAU_SCOPED, capped by each cell's app base --
    mau = allocate_capped(
        MAU_SCOPED,
        {k: c["app"] * A.MAU_PROPENSITY[c["cohort"]] for k, c in cells.items()},
        {k: c["app"] for k, c in cells.items()},
    )
    for k, c in cells.items():
        c["mau"] = mau[k]
        c["app_dormant"] = c["app"] - c["mau"]   # installed, quiet 30d+

    # -- Device split within each cell's app base ---------------------------
    for c in cells.values():
        ios_rate = min(0.95, A.IOS_SHARE[c["cohort"]]
                       * A.IOS_MULTIPLIER_BY_ORG[c["org"]])
        s = allocate(c["app"], {"ios": ios_rate, "android": 1 - ios_rate})
        c["ios"], c["android"] = s["ios"], s["android"]

    # -- Gender across the whole cell ---------------------------------------
    for c in cells.values():
        f = A.FEMALE_SHARE[c["cohort"]]
        s = allocate(c["total"], {"female": f, "male": 1 - f})
        c["female"], c["male"] = s["female"], s["male"]

    # -- DND: org-skewed, never uniform ([Bible 16]) ------------------------
    for c in cells.values():
        r = A.DND_SHARE_BY_ORG[c["org"]]
        s = allocate(c["total"], {"dnd": r, "ok": 1 - r})
        c["dnd"], c["not_dnd"] = s["dnd"], s["ok"]

    # -- Channel reachability ----------------------------------------------
    # Allocated separately over the app and no-app populations, each to its own
    # decomposed target, so the base-wide total lands exactly on the observed
    # 23% / 80% / 80%. Org multipliers redistribute within a target without
    # changing it.
    for ch in A.CHANNELS:
        d = A.REACH_DECOMPOSED[ch]
        app_alloc = allocate_capped(
            d["app"],
            {k: c["app"] * A.REACH_MULTIPLIER_BY_ORG[c["org"]]
             for k, c in cells.items()},
            {k: c["app"] for k, c in cells.items()},
        )
        no_app_alloc = allocate_capped(
            d["no_app"],
            {k: c["no_app"] * A.REACH_MULTIPLIER_BY_ORG[c["org"]]
             for k, c in cells.items()},
            {k: c["no_app"] for k, c in cells.items()},
        )
        for k, c in cells.items():
            c[f"reach_{ch}_app"] = app_alloc[k]
            c[f"reach_{ch}_no_app"] = no_app_alloc[k]
            c[f"reach_{ch}"] = app_alloc[k] + no_app_alloc[k]

            # Campaign-ready = reachable AND not DND-suppressed. DND is an
            # independent flag every campaign must check for itself
            # ([Bible 5.2]), so it is applied on top of reachability, not
            # baked into it.
            keep = c["not_dnd"] / c["total"] if c["total"] else 0
            c[f"ready_{ch}"] = allocate(
                c[f"reach_{ch}"], {"y": keep, "n": 1 - keep}
            )["y"]

    # -- Product funnels: exact to each documented stage count -------------
    # All these events are in-app, so every stage is drawn from the app base.
    # Weighted toward active users, which is how funnels actually fill.
    fw = {k: c["mau"] * 2.0 + c["app_dormant"] * 0.35 for k, c in cells.items()}
    caps = {k: c["app"] for k, c in cells.items()}

    for prod, funnel in (("th", A.TH_FUNNEL), ("hc", A.HC_FUNNEL)):
        for label, _event, observed in funnel:
            alloc = allocate_capped(observed, fw, caps)
            for k, c in cells.items():
                c.setdefault(f"{prod}_funnel", {})[label] = alloc[k]

    for c in cells.values():
        c["th_booked"] = c["th_funnel"][A.TH_FUNNEL[-1][0]]
        c["hc_booked"] = c["hc_funnel"][A.HC_FUNNEL[-1][0]]

    return {"cells": cells, "cohort_total": cohort_total}


# ---------------------------------------------------------------------------
# Verification, the server will not start if any of this fails
# ---------------------------------------------------------------------------

def verify(model: dict) -> list[str]:
    cells = model["cells"]
    checks: list[str] = []

    def eq(label, got, want):
        if got != want:
            raise AssertionError(f"{label}: model={got:,} anchor={want:,}")
        checks.append(f"{label} = {want:,}")

    s = lambda k: sum(c[k] for c in cells.values())  # noqa: E731

    eq("eligible base", s("total"), A.TOTAL_ELIGIBLE)
    eq("app installed", s("app"), A.APP_INSTALLED)
    eq("no app", s("no_app"), A.NO_APP_COUNT)
    eq("30d active (derived)", s("mau"), MAU_SCOPED)
    eq("ios + android = app base", s("ios") + s("android"), A.APP_INSTALLED)
    eq("male + female = base", s("male") + s("female"), A.TOTAL_ELIGIBLE)
    eq("dnd + not_dnd = base", s("dnd") + s("not_dnd"), A.TOTAL_ELIGIBLE)

    # Reachability must reproduce the observed base percentages exactly.
    for ch in A.CHANNELS:
        eq(f"reach {ch}", s(f"reach_{ch}"), A.REACH_DECOMPOSED[ch]["total"])
        got_rate = s(f"reach_{ch}") / A.TOTAL_ELIGIBLE
        want_rate = A.BASE_REACH[ch]
        if abs(got_rate - want_rate) > 0.0005:
            raise AssertionError(
                f"reach {ch} rate: model={got_rate:.4f} anchor={want_rate:.4f}"
            )
        checks.append(f"reach {ch} rate = {want_rate:.0%} of base")

    for prod, funnel in (("th", A.TH_FUNNEL), ("hc", A.HC_FUNNEL)):
        for label, _e, want in funnel:
            eq(f"{prod.upper()} funnel '{label}'",
               sum(c[f"{prod}_funnel"][label] for c in cells.values()), want)

    for ck in COHORT_KEYS:
        got = sum(c["total"] for c in cells.values() if c["cohort"] == ck)
        if got != model["cohort_total"][ck]:
            raise AssertionError(f"cohort {ck} subtotal mismatch")
    checks.append("all 6 cohort subtotals reconcile")

    for k, c in cells.items():
        assert c["app"] <= c["total"], f"{k}: app > total"
        assert c["mau"] <= c["app"], f"{k}: mau > app"
        for ch in A.CHANNELS:
            assert c[f"reach_{ch}"] <= c["total"], f"{k}: {ch} reach > cell"
            assert c[f"ready_{ch}"] <= c[f"reach_{ch}"], f"{k}: ready > reach"
        for label, _e, _t in A.TH_FUNNEL:
            assert c["th_funnel"][label] <= c["app"], f"{k}: TH {label} > app"
        for label, _e, _t in A.HC_FUNNEL:
            assert c["hc_funnel"][label] <= c["app"], f"{k}: HC {label} > app"
    checks.append(f"all {len(cells)} cells pass containment checks")

    # Deliverable push must be present and non-zero on every cohort summary.
    # This exact field going missing made the cohort chart plot zero bars.
    for ck in COHORT_KEYS:
        cs = cohort_summary(model, ck)
        wa = cs["reach"]["push"].get("with_app")
        if wa is None:
            raise AssertionError(f"cohort {ck}: push.with_app missing from summary")
        if wa <= 0:
            raise AssertionError(f"cohort {ck}: push.with_app is {wa}, expected > 0")
    checks.append("every cohort reports deliverable push > 0")

    # A channel may only be labelled OBSERVED if there is campaign evidence
    # behind it. Without this, someone can promote a modeled prior to observed
    # by editing one string, which is the most damaging silent edit available
    # in this file: it would make a guess look measured.
    for ch, rates in A.CHANNEL_BENCHMARKS.items():
        prov = A.CHANNEL_BENCHMARK_PROVENANCE.get(ch)
        if prov is None:
            raise AssertionError(f"channel {ch}: no benchmark provenance")
        for metric, v in rates.items():
            if not (0.0 < v <= 1.0):
                raise AssertionError(
                    f"channel {ch}: {metric} rate {v} is outside (0, 1]")
        if prov["kind"] == "OBSERVED":
            if prov.get("campaigns", 0) <= 0 or prov.get("sent", 0) <= 0:
                raise AssertionError(
                    f"channel {ch} is marked OBSERVED but cites "
                    f"{prov.get('campaigns')} campaigns and {prov.get('sent')} "
                    "sends. An observed rate needs sends behind it.")
        elif prov["kind"] != "MODELED":
            raise AssertionError(
                f"channel {ch}: provenance kind {prov['kind']!r} is neither "
                "OBSERVED nor MODELED")
    checks.append("every channel rate is in range and OBSERVED ones cite real sends")

    return checks


# ---------------------------------------------------------------------------
# Rollups
# ---------------------------------------------------------------------------

def _rate(num: int, den: int, nd: int = 4) -> float:
    return round(num / den, nd) if den else 0.0


def _funnel(cells: list[dict], prod: str, funnel_def, app: int) -> list[dict]:
    """Funnel stages with counts first; every rate derived from those counts,
    so a percentage can never disagree with the bar it sits under."""
    out = []
    for i, (label, event, _t) in enumerate(funnel_def):
        count = sum(c[f"{prod}_funnel"][label] for c in cells)
        out.append({"stage": label, "event": event, "count": count})
    first = out[0]["count"] if out else 0
    for i, st in enumerate(out):
        st["from_prev"] = _rate(st["count"], out[i - 1]["count"]) if i else 1.0
        st["cumulative"] = _rate(st["count"], first)
        st["of_app"] = _rate(st["count"], app)
    return out


def cohort_summary(model: dict, cohort_key: str,
                   org_filter: str | None = None) -> dict:
    cells = [c for c in model["cells"].values()
             if c["cohort"] == cohort_key
             and (org_filter is None or c["org"] == org_filter)]
    if not cells:
        return {}

    meta = COHORT_BY_KEY[cohort_key]
    s = lambda k: sum(c[k] for c in cells)  # noqa: E731
    total, app = s("total"), s("app")

    reach = {}
    for ch in A.CHANNELS:
        block = {
            "count": s(f"reach_{ch}"),
            "of_total": _rate(s(f"reach_{ch}"), total),
            "campaign_ready": s(f"ready_{ch}"),
            "app_portion": s(f"reach_{ch}_app"),
            "no_app_portion": s(f"reach_{ch}_no_app"),
            "basis": ("requires app install + live push token"
                      if ch == "push" else "member record, app not required"),
        }
        if ch == "push":
            # Deliverable push is the app-installed portion only. Computed here
            # so every endpoint carries it: when this lived in the route, the
            # cohort LIST omitted it and the chart silently plotted zero.
            block["with_app"] = block["app_portion"]
            block["stale_tokens"] = block["count"] - block["app_portion"]
        reach[ch] = block

    org_breakdown = {}
    for org in ORG_KEYS:
        oc = [c for c in cells if c["org"] == org]
        if not oc:
            continue
        o_total = sum(c["total"] for c in oc)
        org_breakdown[org] = {
            "label": A.ORG_TYPE_LABELS[org],
            "total": o_total,
            "share_of_cohort": _rate(o_total, total),
            "app": sum(c["app"] for c in oc),
            "app_share": _rate(sum(c["app"] for c in oc), o_total),
            "mau": sum(c["mau"] for c in oc),
            "th_booked": sum(c["th_booked"] for c in oc),
            "hc_booked": sum(c["hc_booked"] for c in oc),
            "dnd": sum(c["dnd"] for c in oc),
            "dnd_share": _rate(sum(c["dnd"] for c in oc), o_total),
            "reach": {ch: sum(c[f"reach_{ch}"] for c in oc) for ch in A.CHANNELS},
            "ready": {ch: sum(c[f"ready_{ch}"] for c in oc) for ch in A.CHANNELS},
            "ios": sum(c["ios"] for c in oc),
            "android": sum(c["android"] for c in oc),
            "note": A.SEGMENT_ADOPTION_NOTES.get(org),
        }

    return {
        "key": cohort_key,
        "label": meta["label"],
        "age_range": {"lo": meta["lo"], "hi": meta["hi"]},
        "org_filter": org_filter,

        "total": total,
        "share_of_base": _rate(total, A.TOTAL_ELIGIBLE),

        "app": app,
        "app_share": _rate(app, total),
        "no_app": s("no_app"),
        "no_app_share": _rate(s("no_app"), total),
        "mau": s("mau"),
        "mau_share_of_app": _rate(s("mau"), app),
        "app_dormant": s("app_dormant"),

        "ios": s("ios"),
        "android": s("android"),
        "ios_share_of_app": _rate(s("ios"), app),
        "android_share_of_app": _rate(s("android"), app),

        "male": s("male"),
        "female": s("female"),
        "female_share": _rate(s("female"), total),

        "reach": reach,
        "dnd": s("dnd"),
        "dnd_share": _rate(s("dnd"), total),

        "th_funnel": _funnel(cells, "th", A.TH_FUNNEL, app),
        "hc_funnel": _funnel(cells, "hc", A.HC_FUNNEL, app),
        "th_booked": s("th_booked"),
        "hc_booked": s("hc_booked"),
        "th_booked_of_base": _rate(s("th_booked"), total),
        "hc_booked_of_base": _rate(s("hc_booked"), total),
        "th_booked_of_app": _rate(s("th_booked"), app),
        "hc_booked_of_app": _rate(s("hc_booked"), app),

        "org_breakdown": org_breakdown,
        "peak_hour": A.PEAK_HOUR[cohort_key],
    }


def all_cohorts(model: dict, org_filter: str | None = None) -> list[dict]:
    return [cohort_summary(model, ck, org_filter) for ck in COHORT_KEYS]


def totals(model: dict, org_filter: str | None = None) -> dict:
    cells = [c for c in model["cells"].values()
             if org_filter is None or c["org"] == org_filter]
    s = lambda k: sum(c[k] for c in cells)  # noqa: E731
    total, app = s("total"), s("app")
    return {
        "eligible": total,
        "app": app,
        "app_share": _rate(app, total),
        "no_app": s("no_app"),
        "no_app_share": _rate(s("no_app"), total),
        "mau": s("mau"),
        "mau_share_of_app": _rate(s("mau"), app),
        "app_dormant": s("app_dormant"),
        "ios": s("ios"),
        "android": s("android"),
        "ios_share_of_app": _rate(s("ios"), app),
        "android_share_of_app": _rate(s("android"), app),
        "male": s("male"),
        "female": s("female"),
        "female_share": _rate(s("female"), total),
        "dnd": s("dnd"),
        "dnd_share": _rate(s("dnd"), total),
        "reach": {
            ch: {
                "count": s(f"reach_{ch}"),
                "of_total": _rate(s(f"reach_{ch}"), total),
                "campaign_ready": s(f"ready_{ch}"),
                **({"with_app": s("reach_push_app"),
                    "stale_tokens": s("reach_push") - s("reach_push_app")}
                   if ch == "push" else {}),
            } for ch in A.CHANNELS
        },
        "th_funnel": _funnel(cells, "th", A.TH_FUNNEL, app),
        "hc_funnel": _funnel(cells, "hc", A.HC_FUNNEL, app),
        "th_booked": s("th_booked"),
        "hc_booked": s("hc_booked"),
    }


if __name__ == "__main__":
    m = build()
    print("=== VERIFICATION ===")
    for c in verify(m):
        print(f"  ok   {c}")

    t = totals(m)
    print("\n=== ELIGIBLE BASE (scoped: active + non-test orgs) ===")
    print(f"  Eligible               {t['eligible']:>9,}")
    print(f"  App installed          {t['app']:>9,}   {t['app_share']:.1%}")
    print(f"  No app                 {t['no_app']:>9,}   {t['no_app_share']:.1%}")
    print(f"  Active 30d (derived)   {t['mau']:>9,}   {t['mau_share_of_app']:.1%} of app")
    print(f"  Installed but quiet    {t['app_dormant']:>9,}")
    print(f"  Android / iOS          {t['android']:>9,} / {t['ios']:,}"
          f"   {t['android_share_of_app']:.0%} / {t['ios_share_of_app']:.0%}")
    print(f"  Female share           {t['female_share']:>9.1%}")
    print(f"  DND-suppressed         {t['dnd']:>9,}   {t['dnd_share']:.1%}")

    print("\n  Reachability            reachable    of base   campaign-ready")
    for ch in A.CHANNELS:
        r = t["reach"][ch]
        print(f"    {A.CHANNEL_LABELS[ch]:<10}         {r['count']:>9,}"
              f"    {r['of_total']:>6.1%}    {r['campaign_ready']:>9,}")

    print("\n=== AGE COHORTS ===")
    print(f"  {'Cohort':<10}{'Users':>9}{'Share':>7}{'App':>9}{'App%':>7}"
          f"{'30d':>8}{'Push':>9}{'WhatsApp':>10}{'TH bkd':>8}{'HC bkd':>8}")
    for c in all_cohorts(m):
        print(f"  {c['label']:<10}{c['total']:>9,}{c['share_of_base']:>7.1%}"
              f"{c['app']:>9,}{c['app_share']:>7.1%}{c['mau']:>8,}"
              f"{c['reach']['push']['count']:>9,}"
              f"{c['reach']['whatsapp']['count']:>10,}"
              f"{c['th_booked']:>8,}{c['hc_booked']:>8,}")
    print(f"  {'TOTAL':<10}{t['eligible']:>9,}{1.0:>7.1%}{t['app']:>9,}"
          f"{t['app_share']:>7.1%}{t['mau']:>8,}"
          f"{t['reach']['push']['count']:>9,}"
          f"{t['reach']['whatsapp']['count']:>10,}"
          f"{t['th_booked']:>8,}{t['hc_booked']:>8,}")

    print("\n=== TH FUNNEL (120d, scoped) ===")
    for st in t["th_funnel"]:
        print(f"  {st['stage']:<15}{st['count']:>9,}   step {st['from_prev']:>6.1%}"
              f"   cum {st['cumulative']:>6.2%}")
    print("=== HC FUNNEL (120d, scoped) ===")
    for st in t["hc_funnel"]:
        print(f"  {st['stage']:<15}{st['count']:>9,}   step {st['from_prev']:>6.1%}"
              f"   cum {st['cumulative']:>6.2%}")
