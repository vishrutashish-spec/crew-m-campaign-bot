"""
SIGNAL: the campaign analyst in the product.

Replaces the earlier assistant. Three things changed and they are the whole
point:

  1. It reads the clinical evidence. Specialty mix, biomarker abnormality and
     the real booking clock are now first-class answers, so "what is the
     dermatology pattern here" or "which biomarker is most off at 36-40"
     returns a measured number instead of a plausible sentence.
  2. It builds segments. Ask what filters to use and it emits real CleverTap
     rules with the literal event and property names, in the order a segment
     is actually assembled.
  3. It has a voice. SIGNAL leads with the number that decides the question,
     is blunt about what is unreliable, and does not pad. Openers and
     transitions vary deterministically off the question text, so it reads
     like a person without ever being random.

Still deterministic and still grounded: nothing is generated, every figure is
fetched from the verified model or the aggregate extraction, and every reply
scores itself against the published 10-parameter rubric.

--- Data access note (governance) ---
Reads in-memory aggregates only. No member rows, no free text, nothing leaves
the process.
"""

from __future__ import annotations

import re

import anchors as A
import population as P
import copy_engine as CE
import decisions as D
import cohort_intel as CI
import timing as T

RUBRIC_VERSION = "2.0"

# ---------------------------------------------------------------------------
# Voice. Varied deterministically by question, never randomly.
# ---------------------------------------------------------------------------

OPENERS = {
    "lead": ["Here is the number that decides it.", "Short answer first.",
             "The data is unambiguous here.", "One figure settles this."],
    "caution": ["Worth slowing down on this one.", "This is where people get burned.",
                "Careful here, the obvious read is wrong."],
    "finding": ["This one is genuinely interesting.", "There is a real pattern here.",
                "The evidence has a clear shape."],
    "plain": ["Straight answer.", "Here is what the model holds.",
              "Pulling that from the cohort model."],
}


def _pick(bucket: str, seed: str) -> str:
    opts = OPENERS[bucket]
    return opts[sum(ord(c) for c in seed[:24]) % len(opts)]


def _n(x) -> str:
    return f"{int(x):,}"


def _pct(x: float, dp: int = 1) -> str:
    return f"{x * 100:.{dp}f}%"


def _clean(t: str) -> str:
    return t.replace(" — ", ", ").replace("—", ",").replace("–", "-")


# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

INTENTS = [
    ("segment", ["filter", "filters", "segment", "segmentation", "build", "rules",
                 "how do i target", "who should i target", "audience should",
                 "criteria", "user propert", "event propert", "properties",
                 "property", "attribute", "condition", "query", "targeting",
                 "target for", "install targeting", "target"]),
    ("gender", ["gender", "male", "female", "=men", "women", "woman", "=man",
                "boys", "girls", "sex split", "by gender", "male vs",
                "female vs", "men vs", "women vs"]),
    ("specialty", ["mental health", "anxiety", "stress", "burnout", "therapy",
                   "counsel", "skin", "acne", "hair fall", "bone", "joint",
                   "knee", "back pain", "gut", "acidity", "eyesight", "vision",
                   "physio", "orthoped", "ortho",
                   "dermat", "specialty", "speciality", "gynae", "gyno", "psycholog",
                   "psychiatr", "nutrition", "ortho", "pediatric", "paediatric",
                   "cardio", "endocrin", "gastro", "neurolog", "ent surgeon",
                   "consult pattern", "consultation pattern", "which doctor",
                   "what doctors", "physician", "specialist"]),
    ("biomarker", ["biomarker", "marker", "vitamin", "b12", "hba1c", "cholesterol",
                   "ldl", "hdl", "triglyc", "glucose", "thyroid", "tsh", "liver",
                   "uric", "haemoglobin", "hemoglobin", "anaemia", "anemia",
                   "deficien", "most off", "blood", "lipid", "sugar"]),
    ("copy", ["copy", "message", "write", "draft", "utility", "emoji", "subject line"]),
    ("timing", ["time", "when", "hour", "schedule", "send at", "best time", "timing"]),
    ("channel", ["channel", "whatsapp or", "push or", "email or", "which channel",
                 "best channel", "gmail"]),
    ("conversion", ["conversion", "convert", "funnel", "drop", "book rate", "cvr"]),
    ("reach", ["reach", "audience size", "how many", "addressable", "deliverable",
               "reachab"]),
    ("push_gap", ["stale", "token", "push gap", "push problem", "push"]),
    ("dnd", ["dnd", "suppress", "opt out", "do not disturb"]),
    ("device", ["ios", "android", "device", "platform"]),
    ("activation", ["activation", "activated", "activate", "adoption",
                    "adopted", "org rate", "employee rate", "penetration",
                    "activation gap"]),
    ("compare", ["compare", "which cohort", "best cohort", "biggest cohort",
                 "which age group", "which band", "which is the",
                 "versus", " vs ", "rank", "ladder"]),
    ("accuracy", ["accurate", "accuracy", "trust", "provenance", "source",
                  "how do you know", "reliable", "where does"]),
    ("views", ["screen", "page", "panel", "chart", "graph", "=tab", "view",
               "dashboard", "what does this show", "explain this",
               "walk me through", "what am i looking at", "how do i read",
               "overview", "simulator", "methodology", "settings",
               "push gap", "booking clock", "copy studio", "projected funnel"]),
]

COHORT_ALIASES = {
    "u20": ["under 20", "under20", "teen", "u20"],
    "21_25": ["21-25", "21 to 25", "early 20s", "twenties", "21_25"],
    "26_35": ["26-35", "26 to 35", "late 20s", "thirties", "26_35"],
    "36_40": ["36-40", "36 to 40", "late 30s", "36_40", "pivot"],
    "41_50": ["41-50", "41 to 50", "forties", "41_50"],
    "51p": ["51+", "51 plus", "over 50", "fifties", "older", "51p"],
}


def _kw_hit(low: str, kw: str) -> bool:
    """
    Match a keyword on word boundaries.

    Anchored at a word START only, deliberately. A full boundary on both ends
    breaks stems: "dermat" would stop matching "dermatologist". A start-only
    anchor keeps stems working while still killing the bug that mattered, where
    the ENT keyword matched inside "segment for" and "event properties" because
    the "ent" there is preceded by a letter.

    A keyword prefixed with "=" opts into a FULL word boundary instead, for
    short words where a start anchor is not enough. "man" was matching "many"
    and "management", and "men" was matching "mental health", so a question
    like "how many people can I reach" was being read as a question about men.
    """
    kw = kw.strip()
    if kw.startswith("="):
        return re.search(r"(?<![a-z])" + re.escape(kw[1:]) + r"(?![a-z])",
                         low) is not None
    return re.search(r"(?<![a-z])" + re.escape(kw), low) is not None


# Common misspellings and shorthand seen in real use. Normalised before intent
# detection so a typo does not silently fall through to the generic answer.
NORMALISE = {
    "whatsap": "whatsapp", "whatsapp's": "whatsapp", "wa ": "whatsapp ",
    "biomarkers": "biomarker", "bio marker": "biomarker", "bio-marker": "biomarker",
    "dermatalogist": "dermatologist", "dermetologist": "dermatologist",
    "gynacologist": "gynaecologist", "psycologist": "psychologist",
    "pyschologist": "psychologist", "nutritionist": "nutrition",
    "cohorts": "cohort", "segmant": "segment", "segement": "segment",
    "propertys": "properties", "propeties": "properties", "proeprties": "properties",
    "recomend": "recommend", "converion": "conversion", "convertion": "conversion",
    "relaible": "reliable", "accurate?": "accurate", "vitd": "vitamin d",
    "hb a1c": "hba1c", "a1 c": "hba1c", "cholestrol": "cholesterol",
    "tellhealth": "telehealth", "telehalth": "telehealth", "healthcheckup": "checkup",
    "health check up": "checkup", "reachablity": "reachability",
    "reachabilty": "reachability", "supression": "suppression",
}


def _normalise(msg: str) -> str:
    low = " " + msg.lower().strip() + " "
    for wrong, right in NORMALISE.items():
        low = low.replace(wrong, right)
    return low


def _detect(msg: str) -> list[str]:
    """
    Rank intents rather than taking them in declaration order.

    A question like "which channel and what time for 26-35" carries two real
    intents, and the one with more evidence in the text should lead. Scoring by
    the number and length of matched keywords does that, and it stops a single
    incidental keyword from hijacking a question that is clearly about
    something else.
    """
    low = _normalise(msg)
    scored: list[tuple[int, int, str]] = []
    for name, keys in INTENTS:
        hits = [k for k in keys if _kw_hit(low, k)]
        if hits:
            # weight by how much of the question the match accounts for
            weight = sum(len(k) for k in hits) + len(hits) * 2
            scored.append((weight, len(hits), name))
    if not scored:
        return ["help"]
    scored.sort(reverse=True)
    return [n for _, _, n in scored]


def _explicit_cohorts(msg: str) -> list[str]:
    """
    Cohorts the question itself names, as distinct from whatever the interface
    has selected. The difference matters: if someone asks about 36-40, the
    answer must open on 36-40, not on whichever band happens to peak.
    """
    low = _normalise(msg)
    return [k for k, al in COHORT_ALIASES.items() if any(a in low for a in al)]


def _cohorts_from(msg: str, fallback: list[str]) -> list[str]:
    named = _explicit_cohorts(msg)
    return named or [k for k in fallback if k in CE.BANDS] or ["26_35"]


def _label(keys: list[str]) -> str:
    m = {c["key"]: c["label"] for c in A.AGE_COHORTS}
    return ", ".join(m[k] for k in keys if k in m)


def _objective_from(msg: str, fallback: str) -> str:
    low = _normalise(msg)
    if "cross" in low or "report" in low:
        return "hc_crosssell"
    if "install" in low or "download" in low:
        return "app_install"
    if "dormant" in low or "re-engage" in low or "reengage" in low or "win back" in low:
        return "reengagement"
    if "checkup" in low or "check up" in low or "hc" in low.split():
        return "hc_activation"
    if "telehealth" in low or "consult" in low or "doctor" in low:
        return "th_activation"
    return fallback if fallback in A.OBJECTIVE_CONVERSION else "th_activation"


# ---------------------------------------------------------------------------
# Handlers. Each returns (paragraphs, action, facts appended in place).
# ---------------------------------------------------------------------------

def _sum(model, keys, org):
    return [c for c in (P.cohort_summary(model, k, org) for k in keys) if c]


def h_specialty(model, keys, org, msg, facts, seed):
    cohort = keys[0]
    lab = _label([cohort])
    # Take the LONGEST token that resolves, not the first. Taking the first let
    # an early word in the sentence win over the actual subject of the question.
    named = None
    _best = 0
    for tok in re.findall(r"[a-zA-Z\-]+", msg):
        hit = CI.find_specialty(tok)
        if hit and len(tok) > _best:
            named, _best = hit, len(tok)

    prov = CI.provenance()["th"]
    if named:
        idx = CI.specialty_index(cohort, named)
        if not idx:
            return [f"No {named} signal for {lab} in the consultation file."], "", facts
        facts += [
            {"label": f"{named} share of {lab} consults",
             "value": _pct(idx["share"]), "provenance": "OBSERVED"},
            {"label": "Index vs cohort average",
             "value": f"{idx['index_vs_average']}", "provenance": "DERIVED"},
            {"label": "Peaks in",
             "value": f"{_label([idx['peak_cohort']])} at {_pct(idx['peak_share'])}",
             "provenance": "OBSERVED"},
            {"label": "Evidence base",
             "value": f"{_n(prov['consults'])} consults, {_n(prov['members_valid'])} members",
             "provenance": "OBSERVED"},
        ]
        others = sorted(idx["all_cohorts"].items(), key=lambda kv: -kv[1])
        ladder = ", ".join(f"{_label([c])} {_pct(v, 0)}" for c, v in others[:4])
        direction = ("over-indexes" if idx["index_vs_average"] > 110
                     else "under-indexes" if idx["index_vs_average"] < 90
                     else "sits at the average")
        text = (
            f"{_pick('finding', seed)} {named} is {_pct(idx['share'])} of all {lab} "
            f"consults, which {direction} at {idx['index_vs_average']} against the "
            f"cross-cohort average. It peaks in {_label([idx['peak_cohort']])} at "
            f"{_pct(idx['peak_share'])}. Full ladder: {ladder}. That is measured off "
            f"{_n(prov['consults'])} real consults, not a model."
        )
        facts.append({"label": "Targeting call",
                      "value": f"lead with {_label([idx['peak_cohort']])}",
                      "provenance": "RECOMMENDED"})
        act = (f"If you are building a {named} angle, target "
               f"{_label([idx['peak_cohort']])} first; it carries the strongest "
               f"existing demand signal.")
        return [text], act, facts

    mix = CI.specialty_mix(cohort)[:5]
    rising = CI.rising_specialties(cohort)
    eng = CI.th_engagement(cohort)
    facts += [
        {"label": f"Top specialty in {lab}",
         "value": f"{mix[0]['specialty']} at {_pct(mix[0]['share'])}", "provenance": "OBSERVED"},
        {"label": "Consults per member",
         "value": f"{eng['consults_per_member']} (index {eng['intensity_index']})",
         "provenance": "DERIVED"},
        {"label": "Evidence base",
         "value": f"{_n(prov['consults'])} consults", "provenance": "OBSERVED"},
    ]
    top = ", ".join(f"{m['specialty']} {_pct(m['share'], 0)}" for m in mix)
    text = (
        f"{_pick('plain', seed)} {lab} consult mix, largest first: {top}. "
        f"Members in this cohort book {eng['consults_per_member']} consults each, "
        f"an intensity index of {eng['intensity_index']} against the average."
    )
    if rising:
        r = ", ".join(f"{x['specialty']} at index {x['index']}" for x in rising)
        text += f" What is distinctive rather than just large: {r}."
    facts.append({"label": "Creative call",
                  "value": f"lead on {mix[0]['specialty']}", "provenance": "RECOMMENDED"})
    act = (f"Lead {lab} telehealth copy with {mix[0]['specialty']} for volume, and "
           f"use {rising[0]['specialty'] if rising else mix[1]['specialty']} as the "
           f"differentiated angle.")
    return [text], act, facts


def h_biomarker(model, keys, org, msg, facts, seed):
    cohort = keys[0]
    lab = _label([cohort])
    named = CI.find_marker(msg)
    prov = CI.provenance()["hc"]

    if named:
        t = CI.biomarker_trend(named)
        if not t:
            return [f"No {named} readings joined to age in the checkup file."], "", facts
        facts += [
            {"label": f"{t['marker']} abnormal, {_label([t['worst_cohort']])}",
             "value": f"{t['worst_pct']}%", "provenance": "OBSERVED"},
            {"label": f"{t['marker']} abnormal, all bookings",
             "value": f"{t['overall_pct']}%", "provenance": "OBSERVED"},
            {"label": "Age spread", "value": f"{t['spread']} points", "provenance": "DERIVED"},
            {"label": "Reference", "value": t["basis"], "provenance": "OBSERVED"},
        ]
        series = ", ".join(f"{_label([c])} {v}%" for c, v in t["series"].items())
        here = t["series"].get(cohort)
        asked = bool(_explicit_cohorts(msg)) and here is not None

        if asked:
            # The band was named in the question, so open on it.
            peak_note = (
                f" The worst band is {_label([t['worst_cohort']])} at "
                f"{t['worst_pct']}%."
                if t["worst_cohort"] != cohort
                else " That is also the worst band of the six."
            )
            text = (
                f"{_pick('finding', seed)} In {lab}, {t['marker']} runs abnormal "
                f"in {here}% of bookings, against {t['overall_pct']}% across all "
                f"ages.{peak_note} Threshold used: {t['basis']}. "
                f"Across the age range: {series}. A {t['spread']}-point spread, "
                "which is what makes this an age-targeted angle."
            )
        else:
            text = (
                f"{_pick('finding', seed)} {t['marker']} runs abnormal in {t['worst_pct']}% "
                f"of {_label([t['worst_cohort']])} bookings against {t['overall_pct']}% "
                f"across all of them. Threshold used: {t['basis']}. "
                f"Across the age range: {series}. That is a {t['spread']}-point spread, "
                f"which is why this is an age-targeted angle rather than a general one."
            )
            if here is not None:
                text += f" For {lab} specifically it is {here}%."
        facts.append({"label": "Angle call",
                      "value": f"target {_label([t['worst_cohort']])}",
                      "provenance": "RECOMMENDED"})
        act = (f"Build the {t['marker']} angle against {_label([t['worst_cohort']])} "
               f"first and let the number carry the message; no fear framing needed "
               f"when the base rate is already this high.")
        return [text], act, facts

    b = CI.biomarkers(cohort)
    if not b:
        return [f"Not enough age-matched checkup bookings for {lab} to report markers."], "", facts
    worst = b["markers"][:4]
    facts += [
        {"label": f"Most abnormal in {lab}",
         "value": f"{worst[0]['marker']} at {worst[0]['abnormal_pct']}%", "provenance": "OBSERVED"},
        {"label": "Bookings behind this", "value": _n(b["bookings"]), "provenance": "OBSERVED"},
        {"label": "Age match rate", "value": _pct(prov["match_rate"]), "provenance": "DERIVED"},
    ]
    ladder = ", ".join(f"{m['marker']} {m['abnormal_pct']}%" for m in worst[1:])
    w = worst[0]
    text = (
        f"{_pick('finding', seed)} In {lab}, the marker most often out of range is "
        f"{w['marker']} at {w['abnormal_pct']}% of bookings, median {w['median']} "
        f"against a threshold of {w['threshold']}. Then: {ladder}. "
        f"Based on {_n(b['bookings'])} age-matched checkup bookings."
    )
    steep = CI.steepest_gradient(2)
    if steep:
        s = steep[0]
        text += (f" The sharpest age gradient in the whole panel is {s['marker']}, "
                 f"climbing from {s['best_pct']}% in {_label([s['best_cohort']])} to "
                 f"{s['worst_pct']}% in {_label([s['worst_cohort']])}.")
    facts.append({"label": "Hook call", "value": f"use {w['marker']}",
                  "provenance": "RECOMMENDED"})
    act = (f"Use {w['marker']} as the {lab} checkup hook. It is the single most "
           f"common abnormal finding in this cohort, so the claim is defensible.")
    return [text], act, facts


def h_segment(model, keys, org, msg, facts, seed):
    """
    Emit a real, buildable CleverTap segment, grouped the way the segment
    builder is actually organised: base user properties, then product
    eligibility, then event conditions, then suppression. Age is called out
    separately because it is not a property and has to be derived.
    """
    obj = _objective_from(msg, "th_activation")
    lab = _label(keys)
    cs = _sum(model, keys, org)
    app = sum(c["app"] for c in cs)
    no_app = sum(c["no_app"] for c in cs)
    dnd = sum(c["dnd"] for c in cs)
    total = sum(c["total"] for c in cs) or 1
    ready = sum(c["reach"]["whatsapp"]["campaign_ready"] for c in cs)

    # group -> list of (kind, name, operator, value, why)
    groups: dict[str, list[tuple]] = {
        "Base user properties": [
            ("USER PROPERTY", "warehouse_production_organisationStatus", "equals",
             "ACTIVE", "only live organisations"),
            ("USER PROPERTY", "warehouse_production_isTestOrganisation", "not equals",
             "true", "drops internal test orgs"),
        ],
        "Product eligibility": [],
        "Event conditions": [],
        "Suppression": [
            ("USER PROPERTY", "is_in_DND_CT", "not equals", "true",
             f"{_n(dnd)} people here carry the flag, and nothing enforces it centrally"),
        ],
    }

    if obj in ("th_activation",):
        groups["Product eligibility"].append(
            ("USER PROPERTY", "warehouse_production_telehealthMembershipCreatedAtTimestamp",
             "exists", "in last 365 days", "telehealth entitlement is live"))
        groups["Event conditions"] += [
            ("EVENT", "App Launched", "Did", "in last 180 days",
             f"has the app, {_n(app)} of {_n(total)} here"),
            ("EVENT", "EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed",
             "Have Not Done", "ever",
             "never booked. This is the canonical booked event, not AppointmentCreated"),
        ]
    elif obj == "hc_activation":
        groups["Product eligibility"].append(
            ("USER PROPERTY", "warehouse_production_plumHealthCheckupMembershipCreatedAtTimestamp",
             "exists", "in last 365 days", "checkup entitlement is live"))
        groups["Event conditions"] += [
            ("EVENT", "App Launched", "Did", "in last 180 days",
             f"has the app, {_n(app)} of {_n(total)} here"),
            ("EVENT", "healthCheckupbooking_confirmed", "Have Not Done", "ever",
             "never booked. This is the canonical confirmed event"),
        ]
    elif obj == "app_install":
        groups["Event conditions"].append(
            ("EVENT", "App Installed", "Have Not Done", "in last 365 days",
             f"the no-app pool, {_n(no_app)} people. Note push cannot reach these"))
    elif obj == "reengagement":
        groups["Event conditions"] += [
            ("EVENT", "App Launched", "Did", "in last 180 days", "has the app"),
            ("EVENT", "App Launched", "Have Not Done", "in last 30 days",
             "installed but quiet, the cheapest group to reactivate"),
        ]
    else:  # hc_crosssell
        groups["Event conditions"] += [
            ("EVENT", "healthCheckupreport_viewed", "Did", "in last 120 days",
             "the trigger moment, they have just seen their own numbers"),
            ("EVENT", "healthCheckuptelehealthBooking_done", "Have Not Done", "ever",
             "has not crossed over yet"),
        ]

    n_rules = sum(len(v) for v in groups.values())
    facts += [
        {"label": "Selection", "value": f"{_n(total)} in {lab}", "provenance": "OBSERVED"},
        {"label": "Rules emitted", "value": f"{n_rules} across 4 groups",
         "provenance": "RECOMMENDED"},
        {"label": "DND to exclude", "value": _n(dnd), "provenance": "OBSERVED"},
        {"label": "Campaign-ready after suppression", "value": _n(ready),
         "provenance": "DERIVED"},
    ]

    lines = [
        f"{_pick('plain', seed)} Here is a buildable segment for "
        f"{obj.replace('_', ' ')} across {lab}, grouped the way the builder is "
        f"organised. {n_rules} conditions."
    ]
    for group, rules in groups.items():
        if not rules:
            continue
        lines.append(f"{group}")
        for kind, name, op, val, why in rules:
            lines.append(f"  {kind} · {name} · {op} · {val}\n    {why}")

    lines.append(
        "Age band: not a CleverTap property. Derive it from "
        "warehouse_production_dateOfBirth, which is Active, never from the `age` "
        "event property, which has single-digit fill against millions of rows. "
        "Org type has no partner_type property either and has to be joined via "
        "warehouse_production_organisationId."
    )

    # A clinical hook, so the segment arrives with an angle attached.
    if obj in ("hc_activation", "hc_crosssell"):
        m = CI.worst_marker(keys[0])
        if m:
            facts.append({"label": f"Angle for {lab}",
                          "value": f"{m['marker']} abnormal in {m['abnormal_pct']}%",
                          "provenance": "OBSERVED"})
            lines.append(
                f"Angle to pair with it: {m['marker']} is abnormal in "
                f"{m['abnormal_pct']}% of {lab} checkup bookings, median "
                f"{m['median']} against a {m['threshold']} threshold."
            )
    else:
        mix = CI.specialty_mix(keys[0])[:1]
        if mix:
            facts.append({"label": f"Angle for {lab}",
                          "value": f"{mix[0]['specialty']} at {_pct(mix[0]['share'])}",
                          "provenance": "OBSERVED"})
            lines.append(
                f"Angle to pair with it: {mix[0]['specialty']} is already "
                f"{_pct(mix[0]['share'])} of {lab} consults, the strongest existing "
                f"demand in this cohort."
            )

    act = ("Build it top to bottom in that order, then check the reachability panel "
           "on the real filtered segment before treating it as campaign-ready.")
    return lines, act, facts


def h_timing(model, keys, org, msg, facts, seed):
    low = msg.lower()
    ch = ("email" if "email" in low or "gmail" in low
          else "push" if "push" in low
          else "whatsapp")
    r = T.recommend(ch, keys)
    c = r["clock"]
    facts += [
        {"label": f"{r['channel_label']} primary send",
         "value": f"{r['primary']['send_at']} IST", "provenance": "RECOMMENDED"},
        {"label": "Observed intent peak",
         "value": f"{r['primary']['intent_peak']} IST at {_pct(r['primary']['intent_share'])}",
         "provenance": "OBSERVED"},
        {"label": "Observations", "value": _n(c["observations"]), "provenance": "OBSERVED"},
        {"label": "Dead zone", "value": f"{_pct(c['dead_share'])} of bookings 01:00 to 06:00",
         "provenance": "OBSERVED"},
    ]
    facts.append({"label": "Clock source", "value": r["clock"]["source"],
                  "provenance": "DERIVED"})
    text = (
        f"{_pick('caution', seed)} For {_label(keys)}, send {r['channel_label']} at "
        f"{r['primary']['send_at']} IST, with {r['secondary']['send_at']} as the "
        f"second slot. Booking intent is twin-peaked, not single-peaked: "
        f"{_pct(c['morning_share'])} of real bookings land between 09:00 and 14:00 "
        f"and {_pct(c['evening_share'])} between 17:00 and 21:00. "
        f"{r['why']}, which is why the send sits {r['primary']['lead_minutes']} "
        f"minutes ahead of the {r['primary']['intent_peak']} peak."
    )
    corr = r["corrections"][0]
    text += f" Worth knowing: the often-quoted 20:00 to 23:00 window holds only {_pct(c['night_share'])} of bookings."
    act = (f"Schedule {r['channel_label']} for {r['primary']['send_at']} IST and keep "
           f"the journey day-gaps as designed: day 0, 2, 4 and 9.")
    return [text], act, facts


def h_channel(model, keys, org, msg, facts, seed):
    cs = _sum(model, keys, org)
    total = sum(c["total"] for c in cs) or 1
    dnd = sum(c["dnd"] for c in cs)
    options = {
        "whatsapp": sum(c["reach"]["whatsapp"]["count"] for c in cs),
        "email": sum(c["reach"]["email"]["count"] for c in cs),
        "push": sum(c["reach"]["push"].get("with_app", 0) for c in cs),
    }
    sc = D.score_channels(total, options, 1 - dnd / total)
    win = sc["selected"]
    w = sc["channels"][win]
    runner = sorted(sc["channels"].items(), key=lambda kv: -kv[1]["total"])[1]
    facts += [
        {"label": f"{w['label']} rubric score", "value": f"{w['total']}/100", "provenance": "DERIVED"},
        {"label": f"{runner[1]['label']} rubric score", "value": f"{runner[1]['total']}/100", "provenance": "DERIVED"},
        {"label": f"{w['label']} addressable", "value": _n(w["addressable"]), "provenance": "DERIVED"},
    ]
    text = (
        f"{_pick('lead', seed)} {w['label']} for {_label(keys)}, scoring "
        f"{w['total']}/100 against {runner[1]['total']}/100 for {runner[1]['label']}. "
        f"The rubric weighs deliverable reach at 40, open propensity at 22, clicks at "
        f"12, delivery at 10, frequency headroom at 9 and DND safety at 7. It can "
        f"address {_n(w['addressable'])} people here."
    )
    facts.append({"label": "Rubric",
                  "value": f"6 weighted parameters, v{D.RULES_VERSION}",
                  "provenance": "RECOMMENDED"})
    tm = T.recommend(win, keys)
    clk = tm["clock"]
    facts.append({"label": f"Best {w['label']} slot",
                  "value": f"{tm['primary']['send_at']} IST",
                  "provenance": "RECOMMENDED"})
    text += (
        f" Pair it with the observed clock: this selection books hardest around "
        f"{tm['primary']['intent_peak']} IST, so the send belongs at "
        f"{tm['primary']['send_at']}, measured off {_n(clk['observations'])} real bookings."
    )
    mix = CI.specialty_mix(keys[0])[:2]
    if mix:
        facts.append({"label": "Top demand in cohort",
                      "value": f"{mix[0]['specialty']} at {_pct(mix[0]['share'])}",
                      "provenance": "OBSERVED"})
        text += (f" For creative, their strongest existing demand is "
                 f"{mix[0]['specialty']} at {_pct(mix[0]['share'])} of consults.")
    act = (f"Run the simulator on {w['label']}, send at {tm['primary']['send_at']} IST, "
           f"and open the rubric breakdown to audit the components.")
    return [text], act, facts


def h_reach(model, keys, org, msg, facts, seed):
    cs = _sum(model, keys, org)
    total = sum(c["total"] for c in cs) or 1
    wa = sum(c["reach"]["whatsapp"]["count"] for c in cs)
    em = sum(c["reach"]["email"]["count"] for c in cs)
    real = sum(c["reach"]["push"].get("with_app", 0) for c in cs)
    rep = sum(c["reach"]["push"]["count"] for c in cs)
    lab = _label(keys)
    facts += [
        {"label": f"{lab} selection", "value": _n(total), "provenance": "OBSERVED"},
        {"label": "WhatsApp deliverable", "value": f"{_n(wa)} ({_pct(wa/total)})", "provenance": "DERIVED"},
        {"label": "Email deliverable", "value": f"{_n(em)} ({_pct(em/total)})", "provenance": "DERIVED"},
        {"label": "Push deliverable", "value": f"{_n(real)} ({_pct(real/total)})", "provenance": "DERIVED"},
    ]
    # If the question names one channel, answer about THAT channel first
    # instead of reciting all three in the same order every time.
    low = _normalise(msg)
    named_ch = None
    for ch, words in (("whatsapp", ("whatsapp", "wa ")),
                      ("email", ("email", "gmail", "inbox")),
                      ("push", ("push", "notification", "token"))):
        if any(_kw_hit(low, w) for w in words):
            named_ch = ch
            break
    if named_ch:
        n_reach = {"whatsapp": wa, "email": em, "push": real}[named_ch]
        pretty = A.CHANNEL_LABELS[named_ch]
        extra = ""
        if named_ch == "push":
            extra = (f" The panel will quote {_n(rep)}, but {_n(rep - real)} of "
                     "those are stale tokens on apps that are gone.")
        else:
            extra = (" It keys off the member record, so no app install is "
                     "needed and the number does not decay.")
        lines = [
            f"{_pick('lead', seed)} On {pretty}, {lab} gives you "
            f"{_n(n_reach)} deliverable, {_pct(n_reach / total)} of the "
            f"{_n(total)} in the selection.{extra}"
        ]
        facts += [
            {"label": f"{lab} selection", "value": _n(total),
             "provenance": "OBSERVED"},
            {"label": f"{pretty} deliverable",
             "value": f"{_n(n_reach)} ({_pct(n_reach / total)})",
             "provenance": "DERIVED"},
        ]
        if named_ch == "push":
            facts.append({"label": "Stale tokens excluded",
                          "value": _n(rep - real), "provenance": "DERIVED"})
        else:
            alt = "push" if named_ch != "push" else "whatsapp"
            facts.append({"label": "Deliverable push, for contrast",
                          "value": _n(real), "provenance": "DERIVED"})
        act = (f"Size the campaign on {_n(n_reach)}, not on the cohort total.")
        return lines, act, facts

    text = (
        f"{_pick('lead', seed)} {lab} holds {_n(total)} people. WhatsApp reaches "
        f"{_n(wa)} ({_pct(wa/total)}), email {_n(em)} ({_pct(em/total)}), and push "
        f"genuinely reaches {_n(real)} ({_pct(real/total)}). The panel will quote "
        f"{_n(rep)} for push; the gap is stale tokens on uninstalled apps that "
        f"report as sent and land nowhere."
    )
    cmp = CI.consulter_vs_base(keys[0], cs[0]["share_of_base"]) if cs else None
    if cmp:
        facts.append({"label": "Telehealth use vs cohort size",
                      "value": f"index {cmp['index']}", "provenance": "DERIVED"})
        text += (
            f" Worth pairing with intent: this cohort {cmp['reads']} at index "
            f"{cmp['index']}, comparing its {_pct(cmp['consulter_share'])} share of "
            f"real consulters against its {_pct(cmp['base_share'])} share of the base."
        )
    facts.append({"label": "Sizing rule", "value": "deliverable, not reported",
                  "provenance": "RECOMMENDED"})
    act = "Plan push against the deliverable figure and lead with WhatsApp for anything base-wide."
    return [text], act, facts


def h_conversion(model, keys, org, msg, facts, seed):
    obj = _objective_from(msg, "th_activation")
    kind, basis = A.CONVERSION_PROVENANCE[obj]
    rate = A.OBJECTIVE_CONVERSION[obj]
    cs = _sum(model, keys, org)
    app = sum(c["app"] for c in cs)
    lab = _label(keys)
    facts += [
        {"label": f"Click to convert, {obj.replace('_',' ')}", "value": _pct(rate, 2), "provenance": kind},
        {"label": f"App base in {lab}", "value": _n(app), "provenance": "OBSERVED"},
    ]
    lines = []
    if obj in ("th_activation", "hc_activation"):
        f = A.TH_FUNNEL if obj == "th_activation" else A.HC_FUNNEL
        i = min(range(1, len(f)), key=lambda j: f[j][2] / f[j-1][2])
        step = f[i][2] / f[i-1][2]
        facts.append({"label": f"Worst step: {f[i-1][0]} to {f[i][0]}",
                      "value": f"{_pct(step)} continue", "provenance": "OBSERVED"})
        lines.append(
            f"{_pick('lead', seed)} {_pct(rate, 2)}, and it is {kind}: {basis}. "
            f"For {lab} that sits on an app base of {_n(app)}. The biggest leak is "
            f"{f[i-1][0]} to {f[i][0]}, where only {_pct(step)} continue, so fixing "
            f"that step beats buying more traffic into the top."
        )
    else:
        lines.append(
            f"{_pick('caution', seed)} {_pct(rate, 2)}, and it is {kind}: {basis}. "
            f"Audience sizing for {lab} stays exact either way; treat this rate as "
            f"directional."
        )
    if obj in ("hc_activation", "hc_crosssell"):
        m = CI.worst_marker(keys[0])
        if m:
            facts.append({"label": f"Clinical hook in {lab}",
                          "value": f"{m['marker']} abnormal in {m['abnormal_pct']}%",
                          "provenance": "OBSERVED"})
            lines.append(
                f"On lifting that rate: {m['marker']} runs abnormal in "
                f"{m['abnormal_pct']}% of {lab} checkup bookings, median {m['median']} "
                f"against a {m['threshold']} threshold. A hook built on a base rate "
                f"that high does not need urgency language to work."
            )
    else:
        mix = CI.specialty_mix(keys[0])[:1]
        if mix:
            facts.append({"label": f"Strongest demand in {lab}",
                          "value": f"{mix[0]['specialty']} at {_pct(mix[0]['share'])}",
                          "provenance": "OBSERVED"})
            lines.append(
                f"On lifting that rate: {mix[0]['specialty']} is already "
                f"{_pct(mix[0]['share'])} of {lab} consults, so leading with existing "
                f"demand beats introducing a new one."
            )
    facts.append({"label": "Method", "value": "target off observed, test the leak step",
                  "provenance": "RECOMMENDED"})
    act = "Set the target off the observed rate and A/B only the step above the biggest leak."
    return lines, act, facts


def h_push_gap(model, keys, org, msg, facts, seed):
    cs = _sum(model, keys, org)
    rep = sum(c["reach"]["push"]["count"] for c in cs)
    real = sum(c["reach"]["push"].get("with_app", 0) for c in cs)
    lab = _label(keys)
    facts += [
        {"label": "Push reported", "value": _n(rep), "provenance": "OBSERVED"},
        {"label": "Push deliverable", "value": _n(real), "provenance": "DERIVED"},
        {"label": "Stale tokens", "value": _n(rep - real), "provenance": "DERIVED"},
    ]
    text = (
        f"{_pick('caution', seed)} In {lab} the panel reports {_n(rep)} push-reachable "
        f"but only {_n(real)} hold an app install signal. The {_n(rep - real)} in "
        f"between are stale tokens: App Uninstalled never fires in this account, so "
        f"tokens are never invalidated. Those sends report as delivered and reach nobody."
    )
    ios = sum(c["ios"] for c in cs)
    android = sum(c["android"] for c in cs)
    app = sum(c["app"] for c in cs) or 1
    facts += [
        {"label": "App base", "value": _n(app), "provenance": "OBSERVED"},
        {"label": "iOS share of app base",
         "value": f"{_pct(ios/app, 0)} ({_n(ios)})", "provenance": "MODELED"},
        {"label": "Fix", "value": "exclude no-app from push segments",
         "provenance": "RECOMMENDED"},
    ]
    text += (
        f" There is a second loss underneath the first: of the {_n(app)} real app "
        f"users here, {_n(ios)} are iOS ({_pct(ios/app, 0)}) and iOS requires an "
        f"explicit notification opt-in, so effective push is lower again than the "
        f"{_n(real)} install signal implies."
    )
    act = "Exclude the no-app segment from every push campaign and size against the deliverable count."
    return [text], act, facts


def h_dnd(model, keys, org, msg, facts, seed):
    cs = _sum(model, keys, org)
    dnd = sum(c["dnd"] for c in cs)
    total = sum(c["total"] for c in cs) or 1
    facts += [
        {"label": "DND-suppressed", "value": f"{_n(dnd)} ({_pct(dnd/total)})", "provenance": "OBSERVED"},
        {"label": "Enforcement", "value": "per-campaign, not central", "provenance": "OBSERVED"},
    ]
    text = (
        f"{_pick('caution', seed)} {_n(dnd)} people in {_label(keys)}, "
        f"{_pct(dnd/total)} of the selection, carry is_in_DND_CT. Nothing enforces it "
        f"centrally: the flag-setting journey only sets the flag, so every campaign "
        f"has to exclude it itself. It also skews Enterprise, so do not model it flat."
    )
    ready = sum(c["reach"]["whatsapp"]["campaign_ready"] for c in cs)
    facts += [
        {"label": "Campaign-ready on WhatsApp", "value": _n(ready), "provenance": "DERIVED"},
        {"label": "Documented P1 dark, both products",
         "value": _n(A.P1_DARK_BOTH), "provenance": "OBSERVED"},
        {"label": "DND-locked, telehealth",
         "value": _n(A.DND_TH_LOCKED), "provenance": "OBSERVED"},
        {"label": "Property", "value": "is_in_DND_CT, 373 campaigns use it",
         "provenance": "OBSERVED"},
        {"label": "Rule", "value": "exclude explicitly, per campaign",
         "provenance": "RECOMMENDED"},
    ]
    text += (
        f" After suppression this selection leaves {_n(ready)} campaign-ready on "
        f"WhatsApp. For scale context, {_n(A.DND_TH_LOCKED)} employees are DND-locked "
        f"on telehealth base-wide and {_n(A.P1_DARK_BOTH)} sit in the documented P1 "
        f"dark-on-both segment. Those are P1, never P0."
    )
    act = ("Add is_in_DND_CT != true to every segment and confirm the comparison value "
           "is actually set; a blank once inflated a count past 3.8 million.")
    return [text], act, facts


def h_device(model, keys, org, msg, facts, seed):
    cs = _sum(model, keys, org)
    ios = sum(c["ios"] for c in cs)
    android = sum(c["android"] for c in cs)
    app = sum(c["app"] for c in cs) or 1
    facts += [
        {"label": "Android", "value": f"{_n(android)} ({_pct(android/app, 0)})", "provenance": "MODELED"},
        {"label": "iOS", "value": f"{_n(ios)} ({_pct(ios/app, 0)})", "provenance": "MODELED"},
        {"label": "App base", "value": _n(app), "provenance": "OBSERVED"},
    ]
    text = (
        f"{_pick('plain', seed)} Of {_n(app)} app users in {_label(keys)}, the model "
        f"carries {_n(android)} Android ({_pct(android/app, 0)}) and {_n(ios)} iOS "
        f"({_pct(ios/app, 0)}). This split is MODELED and labelled so: no device "
        f"distribution exists in any source, and CleverTap's counts endpoint ignores "
        f"platform filters, which was verified by direct query. iOS needs explicit "
        f"notification opt-in, so iOS-heavy pockets lose more push than installs suggest."
    )
    act = "Pull CT OS Version on App Launched from the dashboard if device targeting has to be exact."
    return [text], act, facts


# Metrics a "which cohort is most/least X" question can rank on. Each entry is
# the label, the words that select it, a sort key, and a formatter. Adding a
# metric here makes it askable; nothing else needs touching.
RANKABLE = [
    ("size", ("biggest", "largest", "smallest", "size", "headcount",
              "most people", "fewest people"),
     lambda c: c["total"], lambda c: _n(c["total"])),
    ("app ownership", ("app", "install", "ownership", "owns the app"),
     lambda c: c["app_share"], lambda c: _pct(c["app_share"])),
    ("telehealth booking rate", ("telehealth", "teleconsult", "consult rate",
                                 "th rate"),
     lambda c: c["th_booked_of_app"], lambda c: _pct(c["th_booked_of_app"])),
    ("checkup booking rate", ("checkup", "health check", "hc rate", "panel"),
     lambda c: c["hc_booked_of_app"], lambda c: _pct(c["hc_booked_of_app"])),
    ("WhatsApp reach", ("whatsapp", "wa reach"),
     lambda c: c["reach"]["whatsapp"]["count"],
     lambda c: _n(c["reach"]["whatsapp"]["count"])),
    ("email reach", ("email", "gmail", "inbox"),
     lambda c: c["reach"]["email"]["count"],
     lambda c: _n(c["reach"]["email"]["count"])),
    ("deliverable push", ("push", "token"),
     lambda c: c["reach"]["push"].get("with_app") or 0,
     lambda c: _n(c["reach"]["push"].get("with_app") or 0)),
    ("DND suppression", ("dnd", "suppress", "opt out"),
     lambda c: c["dnd_share"], lambda c: _pct(c["dnd_share"])),
]

ASCENDING = ("least", "lowest", "worst", "fewest", "smallest", "bottom",
             "weakest", "poorest")


def _ranked(model, org, msg):
    """
    Resolve a most/least question to (label, direction, ordered cohorts).

    Returns None when no metric is named, so the caller can fall back to the
    general comparison instead of ranking on something arbitrary.
    """
    low = _normalise(msg)
    chosen = None
    best = 0
    for label, words, key, fmt in RANKABLE:
        for w in words:
            if _kw_hit(low, w) and len(w) > best:
                chosen, best = (label, key, fmt), len(w)
    if not chosen:
        return None
    label, key, fmt = chosen
    asc = any(_kw_hit(low, w) for w in ASCENDING)
    cs = [c for c in (P.cohort_summary(model, k, org) for k in CE.BANDS) if c]
    cs.sort(key=key, reverse=not asc)
    return label, ("lowest" if asc else "highest"), cs, key, fmt


def h_activation(model, keys, org, msg, facts, seed):
    """
    The org-versus-employee activation gap, which was falling through to the
    generic fallback despite being one of the two headline findings.
    """
    org_rate = A.ORG_ACTIVATION_RATE
    emp_rate = A.EMPLOYEE_ACTIVATION_RATE
    gap = A.ACTIVATION_GAP_POINTS
    cs = [c for c in (P.cohort_summary(model, k, org) for k in CE.BANDS) if c]
    best = max(cs, key=lambda c: c["th_booked_of_app"]) if cs else None

    lines = [
        f"{_pick('caution', seed)} {_pct(org_rate, 0)} of organisations have "
        f"activated, against {_pct(emp_rate, 0)} of employees. That is a "
        f"{gap} point gap, and it is the whole shape of the problem: getting "
        "the company to say yes is largely solved, reaching the individual "
        "inside it is not."
    ]
    lines.append(
        "The earlier version of this number was wrong and worth knowing about. "
        "It asked whether anyone in a group had ever booked, which is always "
        "true, so org activation came out at 100% and the gap looked like 92 "
        "points. The real comparison is the one above."
    )
    sel = next((c for c in cs if c["key"] in (keys or [])), None)
    if sel:
        lines.append(
            f"For {sel['label']} specifically: {_n(sel['total'])} people, "
            f"{_pct(sel['app_share'])} holding the app, and "
            f"{_pct(sel['th_booked_of_app'])} of that app base has booked "
            "telehealth. The employee-side gap is what you are working on in "
            "this band, not the account-side one."
        )
    if best:
        lines.append(
            f"Where the employee side is least bad: {best['label']} books "
            f"telehealth at {_pct(best['th_booked_of_app'])} of its app base. "
            "That is the ceiling to argue from, not an average."
        )
    implied = round(A.TOTAL_ELIGIBLE * emp_rate)
    lines.append(
        f"In absolute terms that is roughly {_n(implied)} employees who have "
        f"ever booked, out of {_n(A.TOTAL_ELIGIBLE)} eligible. The remaining "
        f"{_n(A.TOTAL_ELIGIBLE - implied)} are the actual addressable space."
    )
    facts += [
        {"label": "Employees who have ever booked", "value": _n(implied),
         "provenance": "DERIVED"},
        {"label": "Organisation activation", "value": _pct(org_rate, 0),
         "provenance": "OBSERVED"},
        {"label": "Employee activation", "value": _pct(emp_rate, 0),
         "provenance": "OBSERVED"},
        {"label": "Gap", "value": f"{gap} points", "provenance": "DERIVED"},
    ]
    if best:
        facts.append({"label": "Best cohort on booking rate",
                      "value": f"{best['label']}, {_pct(best['th_booked_of_app'])}",
                      "provenance": "DERIVED"})
    facts.append({
        "label": "Where the effort belongs",
        "value": "employee reach inside already-activated organisations",
        "provenance": "RECOMMENDED"})
    facts.append({
        "label": "Org share is modeled",
        "value": "org type split is a distribution, not a CleverTap property",
        "provenance": "MODELED"})
    act = ("Spend the effort on employee reach inside already-activated "
           "organisations. The account-level argument is already won.")
    return lines, act, facts


def h_compare(model, keys, org, msg, facts, seed):
    # If the question names a metric, rank on THAT and lead with the answer,
    # rather than returning the same three-metric summary for every question.
    ranked = _ranked(model, org, msg)
    if ranked:
        label, direction, cs, key, fmt = ranked
        win, lose = cs[0], cs[-1]
        ladder = ", ".join(f"{c['label']} {fmt(c)}" for c in cs)

        # The ranking alone is half an answer. Whether the spread is wide
        # enough to act on is the other half, and it is computable rather
        # than assertable: a 1.4x spread and a 57x spread call for opposite
        # decisions, and saying the same closing line for both is what makes
        # an assistant feel templated.
        hi, lo = max(key(c) for c in cs), min(key(c) for c in cs)
        ratio = (hi / lo) if lo else None
        if ratio is None:
            verdict = ("One band sits at zero, so the ratio is undefined and "
                       "the gap is the whole story.")
        elif ratio >= 3:
            verdict = (f"That is a {ratio:.1f}x spread, wide enough that one "
                       "campaign across all six bands wastes most of it. "
                       "Split it.")
        elif ratio >= 1.6:
            verdict = (f"A {ratio:.1f}x spread. Real, but not dramatic: worth "
                       "a variant, not a separate campaign.")
        else:
            verdict = (f"Only a {ratio:.2f}x spread, so this metric barely "
                       "separates the bands. Do not segment on it. Whatever "
                       "is holding the number down is common to everyone.")

        lines = [
            f"{_pick('lead', seed)} On {label}, {win['label']} is {direction} "
            f"at {fmt(win)}, against {fmt(lose)} at the other end. "
            f"Full order: {ladder}. {verdict}"
        ]
        facts += [
            {"label": f"{direction.capitalize()} on {label}",
             "value": f"{win['label']}, {fmt(win)}", "provenance": "DERIVED"},
            {"label": "Other end",
             "value": f"{lose['label']}, {fmt(lose)}", "provenance": "DERIVED"},
            {"label": "Bands compared", "value": f"{len(cs)}",
             "provenance": "OBSERVED"},
            {"label": "Ranked on", "value": label, "provenance": "DERIVED"},
            {"label": "Spread",
             "value": (f"{hi / lo:.2f}x" if lo else "undefined, one band at zero"),
             "provenance": "DERIVED"},
        ]
        act = (f"Lead with {win['label']} on {label}. "
               f"{lose['label']} needs a different argument, not the same one "
               f"sent harder.")
        return lines, act, facts

    cs = [c for c in (P.cohort_summary(model, k, org) for k in CE.BANDS) if c]
    biggest = max(cs, key=lambda c: c["total"])
    best_app = max(cs, key=lambda c: c["app_share"])
    best_th = max(cs, key=lambda c: c["th_booked_of_app"])
    facts += [
        {"label": "Largest", "value": f"{biggest['label']}, {_n(biggest['total'])}", "provenance": "OBSERVED"},
        {"label": "Highest app ownership", "value": f"{best_app['label']}, {_pct(best_app['app_share'])}", "provenance": "DERIVED"},
        {"label": "Best TH rate of app base", "value": f"{best_th['label']}, {_pct(best_th['th_booked_of_app'])}", "provenance": "DERIVED"},
    ]
    text = (
        f"{_pick('plain', seed)} {biggest['label']} is largest at {_n(biggest['total'])} "
        f"and carries the most absolute headroom. {best_app['label']} owns the app most "
        f"at {_pct(best_app['app_share'])}, so push works best there. On booking rate "
        f"inside the app base, {best_th['label']} leads telehealth at "
        f"{_pct(best_th['th_booked_of_app'])}."
    )
    over = []
    for c in cs:
        cmp = CI.consulter_vs_base(c["key"], c["share_of_base"])
        if cmp and cmp["index"] > 115:
            over.append(f"{c['label']} at index {cmp['index']}")
    if over:
        text += (f" Against their share of the base, these cohorts over-index on actual "
                 f"telehealth use: {', '.join(over)}.")
    facts.append({"label": "Sequencing call",
                  "value": f"{biggest['label']} then {best_th['label']}",
                  "provenance": "RECOMMENDED"})
    act = f"Start with {biggest['label']} for volume and {best_th['label']} for efficiency."
    return [text], act, facts


def h_copy(model, keys, org, msg, facts, seed, channel):
    obj = _objective_from(msg, "th_activation")
    ch = channel if channel in A.CHANNELS else "whatsapp"
    gen = CE.generate(obj, keys[:1], ch)
    v = gen["groups"][0]["variants"][0]
    a, p = v["analysis"], v["prediction"]
    facts += [
        {"label": "Source", "value": v["source"], "provenance": "GENERATED"},
        {"label": "Category", "value": f"{A.CHANNEL_LABELS[ch]} {a['category']}", "provenance": "DERIVED"},
        {"label": "Style score", "value": f"{a['style_score']}/100", "provenance": "DERIVED"},
        {"label": "Predicted open", "value": f"{_pct(p['predicted']['open'])} vs {_pct(p['baseline']['open'])} prior", "provenance": "PREDICTED"},
    ]
    band = gen["groups"][0]["band_label"]
    body = v["body"] if len(v["body"]) <= 400 else v["body"][:397] + "..."
    lines = [
        f"{_pick('plain', seed)} Approved-library {A.CHANNEL_LABELS[ch]} "
        f"{a['category']} for {band}, {a['chars']} characters, {a['emoji_count']} "
        f"emojis, style {a['style_score']}/100:",
        body if not v["title"] else f"{v['title']}\n{body}",
        f"Predicted open {_pct(p['predicted']['open'])} against a "
        f"{_pct(p['baseline']['open'])} channel baseline, at {p['confidence']} "
        f"confidence. {p.get('channel_evidence', {}).get('basis', '')}",
    ]
    marker = CI.worst_marker(keys[0])
    if marker and obj in ("hc_activation", "hc_crosssell"):
        lines.append(
            f"If you want a sharper hook for this cohort, {marker['marker']} runs "
            f"abnormal in {marker['abnormal_pct']}% of their checkup bookings."
        )
    act = "Open the copy studio for every variant, the utility alternative and the full discipline checks."
    return lines, act, facts


def h_accuracy(model, keys, org, msg, facts, seed):
    prov = CI.provenance()
    facts += [
        {"label": "Model invariants", "value": "25 asserted at boot", "provenance": "OBSERVED"},
        {"label": "Simulation sweep", "value": "20 combinations per boot", "provenance": "DERIVED"},
        {"label": "Clinical evidence",
         "value": f"{_n(prov['th']['consults'])} consults, {_n(prov['hc']['bookings'])} checkup bookings",
         "provenance": "OBSERVED"},
        {"label": "Known data defects", "value": "3 documented and filtered", "provenance": "OBSERVED"},
    ]
    text = (
        f"{_pick('plain', seed)} Four labels, never blurred: OBSERVED off the source "
        f"of record, DERIVED as exact arithmetic on observed facts, MODELED as a "
        f"calibrated assumption that still reconciles to the anchors, PREDICTED as a "
        f"forecast. The 956,050 base reconciles to "
        f"{model.get('invariant_count', len(P.verify(model)))} "
        f"invariants at boot, and a simulation sweep runs every start. The clinical "
        f"layer sits on {_n(prov['th']['consults'])} real consults and "
        f"{_n(prov['hc']['bookings'])} checkup bookings."
    )
    text += (
        f" Three defects are handled openly: patient age in the source ranges from "
        f"-517 to 2026 so rows are filtered to 15-80, dropping "
        f"{prov['th']['dropped_pct']}%; consultation timestamps are UTC and are "
        f"converted to IST or the booking curve peaks at 05:00; and checkup bookings "
        f"carry no age, so age is joined via member id and matches "
        f"{_pct(prov['hc']['match_rate'])}."
    )
    facts.append({"label": "Where to verify", "value": "Methodology page, live checks",
                  "provenance": "RECOMMENDED"})
    act = "Open Methodology for field-level provenance and the live invariant list."
    return [text], act, facts


def h_help(model, keys, org, msg, facts, seed):
    prov = CI.provenance()
    # If the question had content but matched nothing, say so plainly and point
    # at the nearest capabilities instead of returning a generic brochure.
    unmatched = len(msg.split()) > 2
    t = P.totals(model)
    steep = CI.steepest_gradient(1)
    facts += [
        {"label": "Eligible base", "value": _n(t["eligible"]), "provenance": "OBSERVED"},
        {"label": "Consults readable",
         "value": f"{_n(prov['th']['consults'])} across 24 specialties", "provenance": "OBSERVED"},
        {"label": "Checkup bookings readable",
         "value": f"{_n(prov['hc']['bookings'])} across 11 scored markers", "provenance": "OBSERVED"},
        {"label": "Model invariants", "value": "25 asserted at boot", "provenance": "DERIVED"},
        {"label": "Scope", "value": "aggregates only, no member rows", "provenance": "RECOMMENDED"},
    ]
    text = (
        f"{_pick('plain', seed)} I read four things: the cohort model over "
        f"{_n(t['eligible'])} eligible people, Plum's own "
        f"{_n(prov['th']['consults'])} telehealth consults across 24 specialties, "
        f"{_n(prov['hc']['bookings'])} checkup bookings across 11 scored biomarkers, "
        f"and the approved copy library. Everything I say is a figure one of those "
        f"actually holds, labelled OBSERVED, DERIVED, MODELED or PREDICTED."
    )
    if steep:
        g = steep[0]
        text += (
            f" A taste of what is in there: {g['marker']} runs abnormal in "
            f"{g['worst_pct']}% of {_label([g['worst_cohort']])} bookings against "
            f"{g['best_pct']}% in {_label([g['best_cohort']])}, a {g['spread']}-point "
            f"age gradient and one of the strongest campaign angles in the data."
        )
    if unmatched:
        text = (
            f"I could not map that to something I hold, so rather than guess: here is "
            f"what I can actually answer. I read the cohort model over "
            f"{_n(t['eligible'])} eligible people, {_n(prov['th']['consults'])} "
            f"telehealth consults across 24 specialties, "
            f"{_n(prov['hc']['bookings'])} checkup bookings across 11 scored "
            f"biomarkers, and the approved copy library.\n\n"
            f"Reach and deliverable audience. Channel choice and why. Real send times "
            f"from the booking clock. Conversion and where the funnel leaks. Which "
            f"biomarker is most off in a cohort. Specialty and consult patterns. "
            f"Segment filters with literal CleverTap names. DND and suppression. "
            f"Device split. Copy for any channel. And how far to trust any of it."
        )
    act = ("Try: which biomarker is most off in 36-40, what the dermatology pattern is "
           "in 21-25, or what filters build a checkup segment for 26-35.")
    return [text], act, facts


HANDLERS = {
    "specialty": h_specialty, "biomarker": h_biomarker, "segment": h_segment,
    "timing": h_timing, "channel": h_channel, "reach": h_reach,
    "conversion": h_conversion, "push_gap": h_push_gap, "dnd": h_dnd,
    "device": h_device, "compare": h_compare, "accuracy": h_accuracy,
    "activation": h_activation,
    "help": h_help,
}

# ---------------------------------------------------------------------------
# The 10-parameter rubric
# ---------------------------------------------------------------------------

# ===========================================================================
# Dashboard views
# ===========================================================================
#
# SIGNAL is asked to explain the product itself, not only the data: "what is
# the push gap panel telling me", "why does the funnel label change". Each
# entry says what the view shows, where its numbers come from, how to read it,
# and the trap in it. Written here rather than in the UI so the explanation and
# the chart cannot drift apart.

VIEWS = {
    "overview": {
        "screen": "Overview",
        "what": "The whole eligible base at a glance: how much of it has the app, how much is reachable per channel, and where the two product funnels leak.",
        "panels": [
            ("Channel reachability",
             "Two bars per channel: reported reachable, and actually deliverable. WhatsApp and email key off the member record so the two match. Push needs a live app token, so its second bar is far shorter.",
             "The gap on push is the whole point of the panel. Do not read the first push bar as an audience."),
            ("The push gap",
             "The count of people who look push-reachable but cannot receive a push, because they sit in the no-app segment on tokens that were never invalidated.",
             "App Uninstalled never fires in this account, so stale tokens are never cleaned up. Any push plan built on reported reach is overstated."),
            ("Cohorts",
             "The six age cohorts, split into app-installed and no-app.",
             "Age composition is MODELED, not a CleverTap property. The totals are exact, the age split is a distribution."),
            ("Telehealth and health checkup funnels",
             "Stage counts over a 120-day window, each bar labelled with its share of the FIRST stage so the last bar is the true end-to-end rate.",
             "The red bar marks the steepest single-step drop, which is a different question from the labelled share. Bottleneck and cumulative rate are not the same number."),
            ("Live usage",
             "Annual actives, 30-day actives, DAU, installs and sessions, straight from the CleverTap counts API.",
             "Account-wide, including test and inactive organisations, because the counts endpoints accept no organisation filter. Never express these as a share of the eligible base."),
            ("Activation gap",
             "Org-level activation against employee-level activation.",
             "The gap is the real finding: getting the company to say yes is largely solved, reaching individual employees is not."),
        ],
    },
    "cohorts": {
        "screen": "Cohorts",
        "what": "One age cohort at a time, in depth: size, app ownership, deliverable reach per channel, both product funnels, when they book, what they consult about, and which biomarkers come back abnormal.",
        "panels": [
            ("Cohort tiles",
             "Six tiles, each with the cohort's size, its share of the base, and the proportion holding the app.",
             "Selecting a tile drives every panel below it. The org-type control filters all of them together."),
            ("Deliverable reach by cohort",
             "WhatsApp, email and push side by side, where push counts only tokens that can actually receive.",
             "Push is plotted as real capacity, so it will look small next to the other two. That is correct, not a rendering fault."),
            ("Bookings by cohort",
             "Absolute telehealth and checkup bookings in the 120-day funnel window.",
             "Absolute counts, not rates. The biggest cohort books most in absolute terms while converting less well."),
            ("Booking clock",
             "Share of bookings by hour, converted to IST.",
             "The raw timestamps are UTC. Read without converting, the curve peaks at 05:00, which is an artefact."),
            ("Consult mix and biomarkers",
             "Which specialties this cohort actually consults, and which markers come back most abnormal.",
             "Aggregated from consultation and checkup files in place. Ages outside 15 to 80 are dropped as unusable, and the drop is always reported."),
        ],
    },
    "simulator": {
        "screen": "Simulator",
        "what": "Plan one campaign end to end: pick cohorts, narrow the audience, size it against real reachability, get a channel and a send time, then write the message and see predicted performance.",
        "panels": [
            ("Choose cohorts and narrow the audience",
             "Cohort selection plus objective, org type, send hour, and the two suppression toggles.",
             "The objective pool and the channel are disjoint questions. App-install campaigns target people without the app, so push reach does not apply to them."),
            ("Audience sizing",
             "Objective pool, addressable, control group and sent, as exact integers.",
             "Sizing is exact and reconciles to the cohort model. A flat 5% control group comes out before the send count."),
            ("Recommended channel",
             "A weighted score across reach, engagement, click, delivery, frequency headroom and suppression, not simply the widest reach.",
             "Argmax on reach alone picks email over WhatsApp on a three-point edge, which is why the rubric exists. Weights are published."),
            ("Best time to send",
             "A primary and a secondary slot, built from real booking intent by hour plus per-channel lead time and inbox sweeps.",
             "Intent peak and send time are different instants: email is offset ahead of the peak because it waits in an inbox."),
            ("Projected funnel",
             "Sent, delivered, opened, clicked, converted, each labelled as a share of sent.",
             "Everything between send and click is an external prior. Click to convert is the one downstream rate with a real product anchor."),
            ("Copy studio",
             "Variants assembled from Plum's shipped copy library, scored against the ten discipline rules, with predicted performance per variant.",
             "WhatsApp Utility and Marketing are different products: Utility escapes the marketing frequency cap and carries no promotional device. Recommended copy states what it was modelled from; pasted copy is reported at low confidence because it has never shipped."),
        ],
    },
    "methodology": {
        "screen": "Methodology",
        "what": "Every anchor the product stands on, what kind of claim it is, and where it came from.",
        "panels": [
            ("Provenance",
             "Each figure tagged OBSERVED, DERIVED, MODELED or PREDICTED, with its source and pull date.",
             "The four labels are not decoration. A MODELED distribution and an OBSERVED count are different kinds of claim and are never averaged together."),
            ("Recorded conflicts",
             "Where two sources disagree, both are kept with the reason one was chosen.",
             "Conflicts are recorded, never averaged. Averaging two disagreeing sources produces a number neither supports."),
        ],
    },
    "settings": {
        "screen": "Settings",
        "what": "What the instance is connected to, the guardrails in force, the published rubrics, the startup invariants, and the CleverTap resync.",
        "panels": [
            ("Verified at startup",
             "The invariants asserted every boot. If any fails the API refuses to serve.",
             "It is a refusal, not a warning. A wrong number cannot be served quietly."),
            ("Resync with CleverTap",
             "Re-pulls the live usage block and reports drift against the anchored figures.",
             "It deliberately cannot refresh the eligible base. The counts endpoints ignore profile property filters, so no org-active figure can be sourced there."),
        ],
    },
}

VIEW_ALIASES = {
    "overview": ["overview", "home", "landing", "first page", "dashboard home",
                 "reachability", "push gap", "activation gap", "live usage",
                 "channel reach"],
    "cohorts": ["cohort", "cohorts", "age cohort", "tiles", "booking clock",
                "consult mix", "biomarker panel", "bookings by"],
    "simulator": ["simulator", "simulate", "campaign planner", "copy studio",
                  "projected funnel", "audience sizing", "best time",
                  "recommended channel", "variant"],
    "methodology": ["methodology", "provenance page", "conflicts", "anchors page"],
    "settings": ["settings", "guardrail", "invariant", "resync", "rubrics page",
                 "connections"],
}


def _view_facts(key, model, keys, facts):
    """Real figures for the screen being explained, with mixed provenance."""
    if key == "overview":
        facts.append({"label": "Eligible base", "value": f"{A.TOTAL_ELIGIBLE:,}",
                      "provenance": "OBSERVED"})
        facts.append({"label": "App ownership",
                      "value": f"{A.APP_INSTALLED:,} of the base, {A.APP_INSTALLED_SHARE:.1%}",
                      "provenance": "OBSERVED"})
        facts.append({"label": "Push tokens that cannot deliver",
                      "value": f"{A.REACH_DECOMPOSED['push']['no_app']:,}",
                      "provenance": "DERIVED"})
    elif key == "cohorts":
        facts.append({"label": "Cohorts", "value": f"{len(A.AGE_COHORTS)} age bands",
                      "provenance": "MODELED"})
        if keys:
            cs = P.cohort_summary(model, keys[0])
            if cs:
                facts.append({"label": f"{cs['label']} size",
                              "value": f"{cs['total']:,}", "provenance": "DERIVED"})
                facts.append({"label": f"{cs['label']} app ownership",
                              "value": f"{cs['app_share']:.1%}",
                              "provenance": "OBSERVED"})
    elif key == "simulator":
        facts.append({"label": "Control group",
                      "value": f"{A.CONTROL_GROUP_SHARE:.0%} flat, every campaign",
                      "provenance": "OBSERVED"})
        facts.append({"label": "Copy library",
                      "value": f"{A.PREDICTION_BASIS['copy'].split(':')[1].strip().split('.')[0]}",
                      "provenance": "OBSERVED"})
        facts.append({"label": "Campaign history to learn from",
                      "value": f"none, though {A.CT_CAMPAIGNS_IN_ACCOUNT} campaigns exist",
                      "provenance": "MODELED"})
    elif key == "methodology":
        facts.append({"label": "Anchors published",
                      "value": f"{len(A.ANCHOR_NOTES)} notes",
                      "provenance": "OBSERVED"})
        facts.append({"label": "Conflicts", "value": "recorded, never averaged",
                      "provenance": "DERIVED"})
        facts.append({"label": "Provenance kinds",
                      "value": "OBSERVED, DERIVED, MODELED, PREDICTED",
                      "provenance": "MODELED"})
    elif key == "settings":
        facts.append({"label": "Invariants asserted at boot",
                      "value": "26, or the API refuses to serve",
                      "provenance": "DERIVED"})
        facts.append({"label": "CleverTap campaigns in the account",
                      "value": f"{A.CT_CAMPAIGNS_IN_ACCOUNT:,}",
                      "provenance": "OBSERVED"})
        facts.append({"label": "What resync cannot refresh",
                      "value": "the eligible base, counts ignores profile filters",
                      "provenance": "MODELED"})
    return facts


def h_gender(model, keys, org, msg, facts, seed):
    """
    Which age band and gender consults for what, and which markers come back
    worst for them.

    Two readings, kept apart on purpose. The specialty a group consults MOST is
    General Physician in all twelve cells, so that answer is worthless on its
    own. The specialty most over-represented against the same gender's overall
    mix is the one that separates one group from another, and it is the one
    worth building a campaign on.
    """
    low = _normalise(msg)
    q = CI.gender_quality()

    want_f = any(_kw_hit(low, w) for w in ("female", "women", "woman", "she", "girls"))
    want_m = any(_kw_hit(low, w) for w in ("male", "men", "man", "boys"))

    # No band named: sweep every cell and answer the comparison directly.
    if not keys or (len(keys) > 2):
        cells = CI.gender_sweep()
        if want_f:
            cells = [c for c in cells if c["gender"] == "FEMALE"]
        elif want_m:
            cells = [c for c in cells if c["gender"] == "MALE"]
        ranked = sorted(
            (c for c in cells if c["distinctive"]),
            key=lambda c: -c["distinctive"]["index_vs_gender"])[:5]
        lines = [
            f"{_pick('finding', seed)} Across all twelve age band and gender "
            f"cells, built from {q.get('th_rows_used', 0):,} consultations, "
            "these are the sharpest concentrations."
        ]
        for c in ranked:
            lab = _label([c["cohort"]]) or c["cohort"]
            d = c["distinctive"]
            lines.append(
                f"  {lab} {c['gender'].lower()}\n"
                f"    {d['specialty']} at {d['index_vs_gender']}x that gender's "
                f"own average, {d['share']:.1%} of their {c['consults']:,} consults"
            )
        top = ranked[0] if ranked else None
        if top:
            facts.append({"label": "Sharpest concentration",
                          "value": (f"{_label([top['cohort']])} {top['gender'].lower()}, "
                                    f"{top['distinctive']['specialty']} at "
                                    f"{top['distinctive']['index_vs_gender']}x"),
                          "provenance": "OBSERVED"})
        facts.append({"label": "Consultations analysed",
                      "value": f"{q.get('th_rows_used', 0):,} across 24 specialties",
                      "provenance": "OBSERVED"})
        facts.append({"label": "Cells compared", "value": f"{len(cells)}",
                      "provenance": "DERIVED"})
        action = ("Target the over-indexed specialty, not the biggest one. "
                  "General Physician leads every cell and separates nothing.")
        return lines, action, facts

    band = keys[0]
    lab = _label([band]) or band
    both = CI.gender_compare(band)
    if not both:
        return ([f"I have no gender split for {lab}."],
                "Ask about another band.", facts)

    genders = (["FEMALE"] if want_f and not want_m
               else ["MALE"] if want_m and not want_f
               else ["FEMALE", "MALE"])

    lines = [f"{_pick('finding', seed)} {lab}, by gender, from real "
             f"consultation and checkup records."]

    for g in genders:
        c = both.get(g)
        if not c:
            continue
        block = [f"  {lab} {g.lower()}, {c['consults']:,} consults"]
        if c["leading"]:
            block.append(f"    Most consulted, past General Physician: "
                         f"{c['leading']['specialty']} at "
                         f"{c['leading']['share']:.1%}")
        if c["distinctive"]:
            d = c["distinctive"]
            block.append(f"    Most over-represented: {d['specialty']} at "
                         f"{d['index_vs_gender']}x this gender's own average")
        if c["markers"]:
            m = c["markers"][0]
            block.append(f"    Worst marker: {m['marker']} abnormal in "
                         f"{m['abnormal_pct']}% of {m['n']:,} results")
        lines.append("\n".join(block))

    # The contrast is usually the actual finding.
    f, m = both.get("FEMALE"), both.get("MALE")
    if len(genders) == 2 and f and m and f["leading"] and m["leading"]:
        if f["leading"]["specialty"] != m["leading"]["specialty"]:
            lines.append(
                f"The split matters here: {lab} women lead on "
                f"{f['leading']['specialty']}, men on {m['leading']['specialty']}. "
                "One creative for the band would miss one of them.")
        else:
            lines.append(
                f"Both genders in {lab} lead on {f['leading']['specialty']}, so "
                "the band can take one message. The over-represented "
                "specialties still differ, which is where a second variant earns "
                "its place.")

    for g in genders:
        c = both.get(g)
        if c and c["leading"]:
            facts.append({
                "label": f"{lab} {g.lower()}, leading specialty",
                "value": f"{c['leading']['specialty']}, {c['leading']['share']:.1%} of {c['consults']:,}",
                "provenance": "OBSERVED"})
    if q.get("hc_match_rate"):
        facts.append({
            "label": "Checkup age coverage",
            "value": f"{q['hc_match_rate']:.0%} of bookings, joined on member id",
            "provenance": "DERIVED"})
    facts.append({"label": "Consultations analysed",
                  "value": f"{q.get('th_rows_used', 0):,}, {q.get('th_dropped_pct', 0)}% dropped on unusable age",
                  "provenance": "OBSERVED"})

    lead = both.get(genders[0])
    action = ""
    if lead and lead["distinctive"]:
        action = (f"For {lab} {genders[0].lower()}, lead the creative on "
                  f"{lead['distinctive']['specialty']}: it is "
                  f"{lead['distinctive']['index_vs_gender']}x over-represented, "
                  "which General Physician volume hides.")
    return lines, action, facts


def h_views(model, keys, org, msg, facts, seed):
    """Explain a dashboard view: what it shows, how to read it, what to watch."""
    low = _normalise(msg)

    hit = None
    for key, words in VIEW_ALIASES.items():
        if any(_kw_hit(low, w) for w in words):
            hit = key
            break

    if hit is None:
        lines = [
            "I can walk you through any of the five screens. Ask about a screen "
            "or a specific panel on it.",
            "\n".join(f"  {v['screen']} · {v['what']}" for v in VIEWS.values()),
        ]
        facts.append({"label": "Screens I can explain", "value": f"{len(VIEWS)}",
                      "provenance": "DERIVED"})
        return lines, "Name a screen or a panel and I will take that one apart.", facts

    v = VIEWS[hit]
    lines = [f"{_pick('lead', seed)} {v['screen']}: {v['what']}"]
    facts = _view_facts(hit, model, keys, facts)

    # If a specific panel was named, lead with that one.
    named = [p for p in v["panels"]
             if _kw_hit(low, p[0].split(" and ")[0].lower()[:12])]
    panels = named or v["panels"][:3]

    for title, what, watch in panels:
        lines.append(
            f"  {title}\n    {what}\n    Watch: {watch}")

    # Close on the figures for the cohort in context, so an explanation of a
    # screen still hands back numbers rather than only prose about the UI.
    lab = _label(keys[:1])
    if lab:
        cs = P.cohort_summary(model, keys[0]) if keys else None
        if cs:
            lines.append(
                f"With {lab} selected, that screen is reading "
                f"{cs['total']:,} people, {cs['app_share']:.1%} of them holding "
                f"the app, {cs['reach']['whatsapp']['count']:,} reachable on "
                f"WhatsApp and {cs['reach']['push'].get('with_app') or 0:,} on "
                f"push once stale tokens come out."
            )

    facts.append({"label": "Panels explained", "value": str(len(panels)),
                  "provenance": "DERIVED"})
    action = (f"Open {v['screen']} and read the panel labels: every figure there "
              "carries the kind of claim it is.")
    return lines, action, facts


# h_views is defined below HANDLERS, so it registers itself here.
HANDLERS["views"] = h_views
HANDLERS["gender"] = h_gender


RUBRIC = {
    "id": "signal_quality",
    "label": "SIGNAL answer quality",
    "version": RUBRIC_VERSION,
    "parameters": [
        {"key": "grounding", "label": "Grounded in real data", "weight": 15,
         "desc": "Every claim traces to a figure the model or the source files actually hold"},
        {"key": "numbers", "label": "Numeric traceability", "weight": 12,
         "desc": "Exact counts and rates, never rounded storytelling"},
        {"key": "provenance", "label": "Provenance labelling", "weight": 11,
         "desc": "OBSERVED, DERIVED, MODELED and PREDICTED never blurred"},
        {"key": "depth", "label": "Evidence depth", "weight": 12,
         "desc": "Reaches the clinical and behavioural layer, not just headline counts"},
        {"key": "specificity", "label": "Cohort specificity", "weight": 10,
         "desc": "Answers about the selected cohorts by name"},
        {"key": "action", "label": "Actionability", "weight": 12,
         "desc": "Ends with something the marketer can do next"},
        {"key": "honesty", "label": "Confidence honesty", "weight": 10,
         "desc": "Predictions carry low confidence, unknowns are said plainly"},
        {"key": "voice", "label": "Voice and personality", "weight": 8,
         "desc": "Reads like an analyst with a view, not a data dump"},
        {"key": "brevity", "label": "Length discipline", "weight": 5,
         "desc": "Tight; no padding"},
        {"key": "hygiene", "label": "House hygiene", "weight": 5,
         "desc": "No em dashes, no fabricated statistics"},
    ],
}

_DEPTH_INTENTS = {"specialty", "biomarker", "segment", "timing", "accuracy",
                  "compare", "channel", "reach", "copy", "push_gap", "dnd",
                  "conversion", "help" "views", "gender", "activation",}


def _score(answer: str, facts: list[dict], action: str, intents: list[str],
           keys: list[str], seed: str) -> dict:
    n_num = len(re.findall(r"\d[\d,.]*%?", answer))
    provs = {f["provenance"] for f in facts}
    labels = [c["label"] for c in A.AGE_COHORTS if c["key"] in keys]
    opener_used = any(o in answer for b in OPENERS.values() for o in b)

    c = {
        "grounding": 1.0 if len(facts) >= 3 else 0.6 if facts else 0.2,
        "numbers": 1.0 if n_num >= 6 else 0.75 if n_num >= 3 else 0.35,
        "provenance": 1.0 if len(provs) >= 3 else 0.75 if len(provs) >= 2 else 0.4,
        "depth": 1.0 if set(intents) & _DEPTH_INTENTS else 0.65,
        "specificity": 1.0 if (any(l in answer for l in labels)
                               or {"accuracy", "help", "compare"} & set(intents)) else 0.5,
        "action": 1.0 if action else 0.0,
        "honesty": (1.0 if (not any(f["provenance"] == "PREDICTED" for f in facts)
                            or "low confidence" in answer.lower()) else 0.4),
        "voice": 1.0 if opener_used else 0.6,
        "brevity": 1.0 if len(answer.split()) <= 175 else 0.7 if len(answer.split()) <= 250 else 0.4,
        "hygiene": 1.0 if ("—" not in answer and "–" not in answer) else 0.0,
    }
    params, total = [], 0.0
    for p in RUBRIC["parameters"]:
        v = c.get(p["key"], 0.5)
        pts = p["weight"] * v
        total += pts
        params.append({"key": p["key"], "label": p["label"], "weight": p["weight"],
                       "score": round(v, 2), "points": round(pts, 1)})
    return {"total": round(total / 10, 1), "out_of": 10, "parameters": params,
            "rule_version": RUBRIC_VERSION}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

# ===========================================================================
# Fine tuning
# ===========================================================================
#
# Parameters that change how SIGNAL answers, published so the UI can render
# controls for them rather than hiding them in code. Each one does real work:
# nothing here is a decorative slider.
#
# What is deliberately NOT tunable: provenance labelling. Every figure carries
# the kind of claim it is, and no setting can switch that off, because the
# four-way distinction is what makes the numbers usable at all.

TUNING = {
    "version": "1.0",
    "parameters": [
        {"key": "detail", "label": "Detail", "type": "choice",
         "options": ["brief", "standard", "deep"], "default": "standard",
         "desc": "brief answers the single strongest reading of the question. "
                 "standard answers two. deep answers up to three and keeps "
                 "every supporting paragraph."},
        {"key": "max_facts", "label": "Facts listed", "type": "choice",
         "options": ["3", "5", "8"], "default": "5",
         "desc": "How many labelled figures are listed under the answer."},
        {"key": "action_first", "label": "Lead with the action", "type": "toggle",
         "default": False,
         "desc": "Put the recommended next step at the top instead of the end, "
                 "for when you already know the context."},
        {"key": "show_basis", "label": "Append the basis", "type": "toggle",
         "default": False,
         "desc": "Close every answer with the mix of claim types it rests on, "
                 "so you can see how much is observed against modeled."},
    ],
    "locked": [
        "Provenance labels are always on. No setting removes them.",
        "Figures are never rounded away: a count is shown as a count.",
    ],
}

_DETAIL_INTENTS = {"brief": 1, "standard": 2, "deep": 3}


def _tune(t):
    """Normalise a tuning payload to the published defaults."""
    out = {p["key"]: p["default"] for p in TUNING["parameters"]}
    if isinstance(t, dict):
        for p in TUNING["parameters"]:
            k = p["key"]
            if k not in t or t[k] is None:
                continue
            v = t[k]
            if p["type"] == "toggle":
                out[k] = bool(v)
            elif str(v) in p["options"]:
                out[k] = str(v)
    return out


def answer(model: dict, message: str, cohort_keys: list[str],
           org: str | None, objective: str | None, channel: str | None,
           tuning: dict | None = None) -> dict:
    tune = _tune(tuning)
    depth = _DETAIL_INTENTS[tune["detail"]]
    intents = _detect(message)
    keys = _cohorts_from(message, cohort_keys or [])
    seed = message.strip().lower()
    facts: list[dict] = []
    paras: list[str] = []
    action = ""

    for intent in intents[:depth]:
        if intent == "copy":
            lines, act, facts = h_copy(model, keys, org, message, facts, seed,
                                       channel or "whatsapp")
        else:
            fn = HANDLERS.get(intent, h_help)
            lines, act, facts = fn(model, keys, org, message, facts, seed)
        paras += lines
        action = action or act

    if tune["detail"] == "brief":
        paras = paras[:2]

    if tune["action_first"] and action:
        paras = [f"Do this first: {action}"] + paras

    facts = facts[:int(tune["max_facts"])]

    if tune["show_basis"]:
        mix = {}
        for f in facts:
            mix[f["provenance"]] = mix.get(f["provenance"], 0) + 1
        if mix:
            paras.append(
                "Resting on " + ", ".join(f"{v} {k.lower()}" for k, v in
                                          sorted(mix.items())) + "."
            )

    text = _clean("\n\n".join(paras))
    return {
        "label": "DERIVED",
        "agent": "SIGNAL",
        "tuning": tune,
        "intents": intents[:depth],
        "cohorts": [c["label"] for c in A.AGE_COHORTS if c["key"] in keys],
        "objective": _objective_from(message, objective or "th_activation"),
        "answer": text,
        "action": _clean(action),
        "facts": facts,
        "score": _score(text, facts, action, intents[:depth], keys, seed),
    }


def suggestions(cohort_keys: list[str]) -> list[str]:
    lab = _label(cohort_keys[:1]) or "26-35"
    return [
        f"Which biomarker is most off in {lab}?",
        f"What is the dermatology pattern in {lab}?",
        f"What filters build a checkup segment for {lab}?",
        f"Which health problem is most common for {lab} women?",
        f"When should I actually send WhatsApp?",
        f"Which channel for {lab}?",
        "How reliable are these numbers?",
    ]
