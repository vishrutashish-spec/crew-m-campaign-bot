"""
Ground-truth anchors for Crew M.

Every number here is tagged OBSERVED, REFERENCE, DERIVED or MODELED. Nothing is
a guess wearing a fact's clothing, and where sources disagree the disagreement
is recorded in ANCHOR_NOTES rather than averaged away.

--- Data access note (governance) ---
What: aggregate profile/event counts from CleverTap, plus documented segment
counts from the CT Bible. Why: every figure the product shows must reconcile to
a source of record. Protection: read-only credentials from the provisioned
bundle, all API queries bounded to <= 1 year, counts only, no individual
profiles are ever fetched and no PII is stored in this repo.

--- SCOPE WARNING (the single most important thing in this file) ---
There are two different populations in play and conflating them produces
garbage:

  ELIGIBLE BASE  956,050 people in active, non-test organisations.
                 Scoped. This is what the cohort model is built on.

  CT ACCOUNT     Every profile in the CleverTap account, including test and
                 inactive orgs. The /counts endpoints do NOT accept an org
                 filter, so live API pulls are always account-wide.

397,301 profiles fired App Launched account-wide in the last 364 days, but only
216,924 people inside the eligible base have an app install signal. Both are
true. An earlier version of this file "resolved" that by declaring the API the
winner and reporting a 58.4% no-app share. That was wrong, it compared an
unscoped numerator to a scoped denominator. The correct no-app share is 77.3%.
"""

from datetime import date

# ===========================================================================
# REFERENCE, data/CREW_M_MASTER_CT_BIBLE.md. Counts as of July 2026.
# Scoped: organisationStatus = ACTIVE and isTestOrganisation != true.
# ===========================================================================

TOTAL_ELIGIBLE = 956_050          # [B 6] "Base: Eligible & Real"
NO_APP_COUNT = 739_126            # [B 6] "No App (no install signal, 365d)"

# DERIVED by subtraction from the two figures above. Flagged because the Bible
# never states an app-installed count directly.
APP_INSTALLED = TOTAL_ELIGIBLE - NO_APP_COUNT   # 216,924
NO_APP_SHARE = NO_APP_COUNT / TOTAL_ELIGIBLE    # 0.7731
APP_INSTALLED_SHARE = APP_INSTALLED / TOTAL_ELIGIBLE  # 0.2269

# [B 6] Product-eligible sub-segments.
TH_ELIGIBLE_NEVER_BOOKED = 173_373
HC_ELIGIBLE_NEVER_BOOKED = 75_272

# [B 6] / [B 9] Priority segments. DND-locked users are P1, not P0.
P0_DARK_BOTH = 57_336
P0_DARK_EITHER = 70_129
P1_DARK_BOTH = 13_221
P1_DARK_EITHER = 16_008

# [B 19.5] DND sizing. DND is applied at whole-org level, unconditionally.
DND_TH_LOCKED = 13_835
DND_HC_LOCKED = 5_621

# ---------------------------------------------------------------------------
# REFERENCE, adoption. [B 1] / [P 3.1]
# Denominator is ELIGIBLE EMPLOYEES, never app-installed users, and "adopted"
# means at least one confirmed booking by a unique user, not a page view,
# not an app install.
# ---------------------------------------------------------------------------

EMPLOYEE_ACTIVATION_RATE = 0.10   # [B 1] ~10% of employees have ever booked
ORG_ACTIVATION_RATE = 0.74        # [B 1] ~74% of orgs have >= 1 booking
ACTIVATION_GAP_POINTS = 64        # [B 1] the "64-point gap", stated explicitly

# The old dashboard showed a 92-point gap against "100% org activation". That
# came from grouping 10,000 synthetic users by their 4 org types and asking
# "does ANY user in this group have a booking", which is always true, so org
# activation was always 1.0. The real, documented gap is 64 points.

ADOPTION_TARGETS = {"M3": 0.15, "M6": 0.25, "M9": 0.35}  # [B 1]

# [B 1] Per-segment adoption is NOT quantified anywhere. Only direction:
SEGMENT_ADOPTION_NOTES = {
    "ENT": "Worst adoption, single biggest lever. 1 point here outweighs a "
           "much larger gain in a smaller segment.",
    "MM":  "Most consistent multi-month improver.",
    "SMB": "Judge by accounts-activated, not employees, ~65% of accounts but "
           "only ~14% of employees.",
    "EOR": "Best per-employee performer, ~2x company average at M9.",
}

# ---------------------------------------------------------------------------
# REFERENCE, org composition. [B 16] EXPLICITLY LABELLED MODELED, NOT MEASURED.
# There is no partner_type property in the CT export, so org type is not
# directly segmentable, it has to be joined via org ID to warehouse data.
# ---------------------------------------------------------------------------

ORG_TYPE_SHARES = {"ENT": 0.585, "MM": 0.235, "SMB": 0.139, "EOR": 0.041}
assert abs(sum(ORG_TYPE_SHARES.values()) - 1.0) < 1e-9

ORG_TYPE_LABELS = {
    "ENT": "Enterprise", "MM": "Mid-Market",
    "SMB": "Small & Medium", "EOR": "Employer of Record",
}
ORG_SHARE_IS_MODELED = True  # [B 16]: "Label as MODELED, not measured."


# ===========================================================================
# OBSERVED, channel reachability. [B 6], the CT reachability panel.
#
# THE DENOMINATOR QUESTION, SETTLED.
# These percentages are shares of ALL SEGMENT MEMBERS, not of app-installed
# users. Proof from the table itself: the "No App" segment is 739,126 people
# with no install signal, and it still shows Push 11%. If push were expressed
# as a share of app-installed users, a no-app segment would read 0%.
#
# So push must NOT be re-based by dividing by an app count. Doing that inflates
# push reach roughly 4x. The old code did something worse, it drew a random
# threshold per user from a (0.11, 0.43) range and compared it to a second
# random number, yielding a meaningless ~27% unrelated to app ownership.
# ===========================================================================

SEGMENT_REACHABILITY = {
    # segment_key: (users, push, email, whatsapp)   -- SMS omitted: never used
    "base":              (956_050, 0.23, 0.80, 0.80),
    "no_app":            (739_126, 0.11, 0.77, 0.74),
    "hc_never_booked":   ( 75_272, 0.40, 0.85, 0.98),
    "th_never_booked":   (173_373, 0.36, 0.87, 0.97),
    "p0_dark_both":      ( 57_336, 0.38, 0.85, 0.98),
    "p0_dark_either":    ( 70_129, 0.43, 0.86, 0.98),
    "p1_dark_both":      ( 13_221, 0.35, 0.97, 0.98),
    "p1_dark_either":    ( 16_008, 0.40, 0.98, 0.99),
}

BASE_REACH = {"push": 0.23, "email": 0.80, "whatsapp": 0.80}
NO_APP_REACH = {"push": 0.11, "email": 0.77, "whatsapp": 0.74}

# ---------------------------------------------------------------------------
# DERIVED, reachability decomposed into app-installed vs no-app.
#
# The Bible gives reach for the whole base and for the no-app segment. Since
# those two segments partition the base exactly, the app-installed reach falls
# out by subtraction, and the result is a genuine, checkable finding rather
# than an assumption:
#
#   push:     23% of 956,050 = 219,892 total;  11% of 739,126 = 81,304 no-app
#             -> app-installed push = 138,588 = 63.9% of 216,924
#   whatsapp: 80% of 956,050 = 764,840 total;  74% of 739,126 = 547,053 no-app
#             -> app-installed whatsapp = 217,787, which EXCEEDS the 216,924
#                app base, so app users are effectively 100% WhatsApp-reachable
#                and the no-app rate carries the remainder
#   email:    80% of 956,050 = 764,840 total;  77% of 739,126 = 569,127 no-app
#             -> app-installed email = 195,713 = 90.2% of 216,924
# ---------------------------------------------------------------------------

def _decompose(channel: str) -> dict:
    total_reach = round(TOTAL_ELIGIBLE * BASE_REACH[channel])
    no_app_reach = round(NO_APP_COUNT * NO_APP_REACH[channel])
    app_reach = total_reach - no_app_reach
    capped = min(app_reach, APP_INSTALLED)
    return {
        "total": total_reach,
        "no_app": no_app_reach if capped == app_reach
                  else total_reach - capped,
        "app": capped,
        "app_rate": capped / APP_INSTALLED,
        "no_app_rate": (no_app_reach if capped == app_reach
                        else total_reach - capped) / NO_APP_COUNT,
    }

REACH_DECOMPOSED = {ch: _decompose(ch) for ch in ("push", "email", "whatsapp")}

# A real data-integrity anomaly, recorded not smoothed:
# 11% push reach on a segment defined as having NO install signal in 365 days
# should be impossible. The schema explains it, `App Uninstalled` has 0 data
# points (the event never fires, so push tokens are never invalidated) while
# `Push Unregistered` has 140,442. Stale tokens persist for uninstalled apps.
# Treat no-app push reach as unreliable deliverability, not real audience.
REACHABILITY_ANOMALY = (
    "The no-app segment shows 11% push reachability despite being defined as "
    "having no install signal in 365 days. App Uninstalled never fires (0 data "
    "points in the schema), so push tokens are never invalidated, these are "
    "stale tokens on uninstalled apps, not reachable people. Push to this "
    "segment will report as sent and land nowhere."
)


# ===========================================================================
# OBSERVED, funnels. [B 7.1] / [B 7.2]
# 120-day window, filtered to active + non-test orgs. Correctly scoped to the
# eligible base, which is why these are the primary funnel numbers rather than
# the account-wide figures a live API pull returns.
#
# Event names are the LITERAL names verified against
# data/ct-schema/events_schema.csv. The Bible writes them in shorthand and
# claims they are character-for-character exact; they are not. Every TH event
# actually carries an "EmployeeMobileApp_Telehealth_" prefix and every HC event
# a "healthCheckup" prefix. The old simulator emitted the shorthand forms
# `DoctorList_Viewed` and `AppointmentSuccessful_Viewed` as segment rules, the
# CT API rejects both as 'Invalid event', so those segments matched nobody.
# ===========================================================================

TH_FUNNEL = [
    ("Homepage",       "EmployeeMobileApp_Telehealth_Homepage_Viewed",             126_680),
    ("Doctor list",    "EmployeeMobileApp_Telehealth_DoctorList_Viewed",            41_461),
    ("Slot screen",    "EmployeeMobileApp_Telehealth_SlotScreen_Viewed",            22_789),
    ("Book clicked",   "EmployeeMobileApp_Telehealth_BookAppointment_Clicked",      16_818),
    ("Booked",         "EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed", 16_167),
]

HC_FUNNEL = [
    ("Homepage",       "healthCheckuphomepage_viewed",    82_838),
    ("Listing",        "healthCheckuplisting_viewed",     46_974),
    ("Item added",     "healthCheckupitem_added",         12_328),
    ("Slot selected",  "healthCheckupslot_selected",       6_787),
    ("Booked",         "healthCheckupbooking_confirmed",   5_085),
]

# [B 3.1] TH canonical booked event. AppointmentCreated is NOT the signal.
TH_BOOKED_EVENT = "EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed"
HC_BOOKED_EVENT = "healthCheckupbooking_confirmed"

# [B 7.2] Cross-sell: HC report viewed -> TH booking.
HC_TO_TH_CROSSSELL_RATE = 0.1432

# [B 1] Repeat-use shape. HC is capped at ~1 by design, one free checkup per
# year, so "book your checkup again" messaging is structurally wrong. [B 14]
TH_CONSULTS_PER_YEAR = 5.0
HC_BOOKINGS_PER_USER = 1.0


# ===========================================================================
# OBSERVED, CleverTap live telemetry.
# Pulled 2026-08-21 via POST /1/counts/profiles.json and /1/counts/events.json.
# ACCOUNT-WIDE, the counts endpoints accept no org filter, so these are NOT
# scoped to the eligible base and must never be divided by 956,050.
# ===========================================================================

CT_PULL_DATE = date(2026, 8, 21)
CT_WINDOW_DAYS = 364    # under the 1-year guardrail

CT_LIVE = {
    "annual_active_users": 397_301,   # App Launched, unique profiles, 364d
    "mau_30d":             147_003,   # App Launched, unique profiles, 30d
    "dau":                  16_503,   # App Launched, unique, last COMPLETE day
    "new_installs_30d":     34_396,   # App Installed, unique profiles, 30d
    "sessions_30d":        888_674,   # App Launched, total occurrences, 30d
}
CT_LIVE["sessions_per_mau"] = round(CT_LIVE["sessions_30d"] / CT_LIVE["mau_30d"], 2)
CT_LIVE["dau_mau_ratio"] = round(CT_LIVE["dau"] / CT_LIVE["mau_30d"], 4)

CT_LIVE_SCOPE = (
    "CleverTap account-wide, including test and inactive organisations. The "
    "/counts endpoints accept no organisation filter. Do not express these as "
    "a share of the 956,050 eligible base."
)

# The DAU bug worth remembering: querying from=today&to=today returns a partial
# day. It reported 11,703 against a true 16,503, a 29% understatement that
# drifted upward through the day. Always query the last complete day.
DAU_METHOD = "last complete day (not today, today returns a partial count)"


# ===========================================================================
# AGE COHORTS, the primary organising dimension.
# ===========================================================================

AGE_COHORTS = [
    {"key": "u20",   "label": "Under 20", "lo": 0,  "hi": 20},
    {"key": "21_25", "label": "21-25",    "lo": 21, "hi": 25},
    {"key": "26_35", "label": "26-35",    "lo": 26, "hi": 35},
    {"key": "36_40", "label": "36-40",    "lo": 36, "hi": 40},
    {"key": "41_50", "label": "41-50",    "lo": 41, "hi": 50},
    {"key": "51p",   "label": "51+",      "lo": 51, "hi": 120},
]

# MODELED. No age distribution exists in any source document, this was
# checked exhaustively. The docs offer age bands (18-25/26-35/36-45/46-55/55+)
# only as an analysis *hypothesis*, with zero counts attached, and state that
# age is not a CT user property. It is derivable from
# warehouse_production_dateOfBirth or DOB, both Active, but no distribution has
# ever been pulled.
#
# Shares below are a standard Indian white-collar group-health age pyramid.
# Labelled MODELED everywhere they surface.
AGE_COHORT_SHARES = {
    "u20": 0.008, "21_25": 0.152, "26_35": 0.455,
    "36_40": 0.168, "41_50": 0.152, "51p": 0.065,
}
assert abs(sum(AGE_COHORT_SHARES.values()) - 1.0) < 1e-9

AGE_DATA_PROVENANCE = (
    "MODELED. No age distribution exists in the CT Bible, the product context "
    "doc, or the schema exports. Age is not a CleverTap user property; it is "
    "derivable from warehouse_production_dateOfBirth (Active) but has never "
    "been pulled. The `age` event property is declared on 27 events with "
    "single-digit fill against millions of rows, so it is unusable."
)

# MODELED, relative app-install propensity by cohort. Normalised in
# population.py so the absolute total lands exactly on APP_INSTALLED.
APP_PROPENSITY = {
    "u20": 1.34, "21_25": 1.28, "26_35": 1.12,
    "36_40": 0.92, "41_50": 0.71, "51p": 0.47,
}

# MODELED, relative 30-day-active propensity within a cohort's app base.
MAU_PROPENSITY = {
    "u20": 1.22, "21_25": 1.16, "26_35": 1.06,
    "36_40": 0.95, "41_50": 0.82, "51p": 0.66,
}

# MODELED, iOS share of a cohort's app base. Corporate India skews Android
# heavily; iOS rises with seniority, which tracks age.
IOS_SHARE = {
    "u20": 0.07, "21_25": 0.11, "26_35": 0.17,
    "36_40": 0.23, "41_50": 0.27, "51p": 0.30,
}
IOS_MULTIPLIER_BY_ORG = {"ENT": 1.22, "MM": 0.94, "SMB": 0.68, "EOR": 1.05}

DEVICE_DATA_PROVENANCE = (
    "MODELED. No iOS/Android split exists in any source document. Live API "
    "filtering was attempted and failed: /counts/profiles.json silently "
    "ignores common_profile_properties, filtering App Launched by platform, "
    "isIOSLogin, isAndroidLogin and gender all returned the identical "
    "unfiltered total of 397,302, meaning the filter is dropped rather than "
    "applied. A real split would have to come from CT OS Version on App "
    "Launched (the only 100%-fill platform signal) via the dashboard, since "
    "funnel-event `platform` has only ~3% fill."
)

# MODELED, female share by cohort. No gender split exists in the docs either,
# though warehouse_production_gender IS Active and already used in 60
# campaigns, so this one is genuinely pullable, it just never has been.
FEMALE_SHARE = {
    "u20": 0.44, "21_25": 0.42, "26_35": 0.38,
    "36_40": 0.34, "41_50": 0.29, "51p": 0.24,
}

# MODELED, DND share by org. [B 16] is explicit: DND skews heavily Enterprise,
# so this must NOT be modelled as uniform. Calibrated so the base total lands
# near the documented ~13,221-16,008 P1 range.
DND_SHARE_BY_ORG = {"ENT": 0.024, "MM": 0.010, "SMB": 0.006, "EOR": 0.008}

# MODELED, reachability multiplier by org. Enterprise HR files are more
# complete; SMB and EOR records are patchier. Normalised in population.py so
# base-wide reach still lands exactly on the OBSERVED BASE_REACH figures.
REACH_MULTIPLIER_BY_ORG = {"ENT": 1.04, "MM": 1.00, "SMB": 0.93, "EOR": 0.88}

# [B 13] Peak activity window is 8-11 PM. MODELED skew within it by cohort.
PEAK_HOUR = {
    "u20": 21, "21_25": 21, "26_35": 20,
    "36_40": 20, "41_50": 19, "51p": 18,
}


# ===========================================================================
# CAMPAIGN BENCHMARKS, MODELED, and the honesty here matters.
#
# [B 19.2] flags "Campaign History Export" as CRITICAL and missing: "This is
# the training data for the prediction models. Without campaign-level
# performance data tied to segments, the models have nothing to learn from."
# No real delivery/open/click/conversion rate exists for any channel in any
# source document.
#
# THAT IS NO LONGER TRUE, and the correction matters more than the original
# caution. CleverTap's message report does expose per-campaign delivery, open
# and click for this account: 458 campaigns with volume and 11.3 million sends.
# Push and email rates are now learned from it. The Bible called the missing
# campaign export the single most critical data gap; the gap was in the reading,
# not in the data. WhatsApp is the one channel with genuinely nothing to learn
# from, because Plum sends WhatsApp through WATI rather than CleverTap.
# ===========================================================================

# Delivery, open and click, per channel.
#
# Push and email are now OBSERVED, aggregated from this account's own campaign
# history: 458 campaigns carrying volume, 11.3 million sends over a bounded
# 12-month window, read through CleverTap's message report. The modeled priors
# they replace were wrong by multiples in both directions, which means every
# funnel projection the simulator produced before this was wrong by multiples:
#
#   push  open     11.8% modeled  ->  39.88% observed   3.4x understated
#   push  click     4.1% modeled  ->   1.17% observed   3.5x OVERSTATED
#   email open     22.1% modeled  ->  61.83% observed   2.8x understated
#   email click     3.1% modeled  ->  27.39% observed   8.8x understated
#
# WhatsApp stays MODELED, and the reason is specific rather than a shrug: there
# is no WhatsApp campaign in CleverTap at all. Plum sends WhatsApp through WATI,
# which this account does not report on, so there is nothing here to learn from.
# Mixing an observed push rate and a modeled WhatsApp rate in one table is
# exactly why each carries its own provenance below.
CHANNEL_BENCHMARKS = {
    "whatsapp": {"delivery": 0.951, "open": 0.648, "click": 0.079},
    "email":    {"delivery": 0.969, "open": 0.6183, "click": 0.2739},
    "push":     {"delivery": 0.988, "open": 0.3988, "click": 0.0117},
}

CAMPAIGN_HISTORY_PULLED = date(2026, 8, 22)

CHANNEL_BENCHMARK_PROVENANCE = {
    "push": {
        "kind": "OBSERVED",
        "campaigns": 346,
        "sent": 9_272_808,
        "basis": ("346 push campaigns with volume, 9,272,808 sends. Delivery is "
                  "sends minus errors, open is views over delivered, click is "
                  "clicks over views."),
    },
    "email": {
        "kind": "OBSERVED",
        "campaigns": 112,
        "sent": 2_051_311,
        "basis": ("112 email campaigns with volume, 2,051,311 sends. The open "
                  "rate is high partly because inbox providers prefetch images, "
                  "which inflates opens industry-wide. It is still this "
                  "account's own measured behaviour, which is the right prior "
                  "for predicting this account."),
    },
    "whatsapp": {
        "kind": "MODELED",
        "campaigns": 0,
        "sent": 0,
        "basis": ("No WhatsApp campaign exists in CleverTap. Plum sends "
                  "WhatsApp through WATI, which this account does not report "
                  "on, so this row is an external prior and the only one left."),
    },
}

# Click-to-convert. A click lands on the product homepage, and the funnels
# MEASURED homepage-to-booked over 120 days, so three of these are computed
# from observed stage counts rather than typed in, and cannot drift from
# their anchors. Audit that forced this: the old modeled priors ran +36.8%
# optimistic on HC activation and -28.1% pessimistic on cross-sell.
OBJECTIVE_CONVERSION = {
    "th_activation": round(TH_FUNNEL[-1][2] / TH_FUNNEL[0][2], 4),   # 0.1276 OBSERVED
    "hc_activation": round(HC_FUNNEL[-1][2] / HC_FUNNEL[0][2], 4),   # 0.0614 OBSERVED
    "hc_crosssell":  HC_TO_TH_CROSSSELL_RATE,                        # 0.1432 OBSERVED
    "app_install":   0.152,                                          # MODELED
    "reengagement":  0.058,                                          # MODELED
}
CONVERSION_PROVENANCE = {
    "th_activation": ("OBSERVED", "TH funnel homepage to booked, 120-day window"),
    "hc_activation": ("OBSERVED", "HC funnel homepage to booked, 120-day window"),
    "hc_crosssell":  ("OBSERVED", "HC report viewed to TH booking, the cross-sell bridge"),
    "app_install":   ("MODELED", "industry prior, no install-campaign history exists"),
    "reengagement":  ("MODELED", "industry prior, no re-engagement history exists"),
}
# Superseded. Campaign performance data DOES exist for push and email, and is
# now used. Kept as a name because other modules import it, but it no longer
# claims the account has no history.
BENCHMARKS_ARE_MODELED = False
BENCHMARK_PROVENANCE = (
    "Push and email delivery, open and click are OBSERVED from this account's "
    "own campaign history: 458 campaigns with volume and 11.3 million sends "
    "over a bounded 12-month window. WhatsApp remains a MODELED external prior, "
    "because no WhatsApp campaign exists in CleverTap at all. The earlier "
    "modeled priors were wrong by up to 8.8x, so predictions made before this "
    "pull should not be compared with predictions made after it."
)

# What actually backs a copy performance prediction, stated per input so the
# UI can show it rather than a bare "low confidence" badge.
#
# CT_CAMPAIGNS_IN_ACCOUNT is counted from the real CleverTap schema export in
# data/ct-schema: the distinct campaign ids referencing any exported property.
# Declared "Campaign Count" matches the listed id list on all 32 rows that
# carry one, so the union is not truncated. It is the number of campaigns that
# EXIST, deliberately not described as campaigns learned from: no per-campaign
# performance export exists in this account, which is the whole point.
CT_CAMPAIGNS_IN_ACCOUNT = 500
CT_JOURNEYS_IN_ACCOUNT = 18
CT_SEGMENTS_IN_ACCOUNT = 74

PREDICTION_BASIS = {
    "copy": (
        "Plum's shipped copy library: 87 approved messages across 6 age bands "
        "and 3 channels. Recommended variants are assembled from it, so the "
        "wording itself has precedent."
    ),
    "delivery_open_click": (
        "Learned from this account's own campaign history for push and email: "
        "458 campaigns with volume and 11.3 million sends over a bounded "
        "12-month window. WhatsApp is the exception and stays an external "
        "prior, because no WhatsApp campaign exists in CleverTap at all: Plum "
        "sends WhatsApp through WATI, which this account does not report on."
    ),
    "convert": (
        "Observed product funnels over the 120-day window wherever one exists: "
        "telehealth 12.76% and health checkup 6.14% of homepage viewers. This "
        "is the one downstream rate with a real anchor."
    ),
}

# Recommended library copy carries less copy-side risk than pasted copy: it has
# shipped before and passes every discipline check by construction. The channel
# priors are equally modeled either way, so this moves one notch, never to high.
# Confidence now depends on the CHANNEL as well as the copy, because the
# channels no longer rest on the same evidence. Push and email rates are
# learned from real sends; WhatsApp is still an external prior.
CONFIDENCE_LIBRARY = "moderate"
CONFIDENCE_LIBRARY_REASON = (
    "Copy is drawn from the shipped library, so the wording has precedent and "
    "clears every discipline rule."
)
CONFIDENCE_CUSTOM = "low"
CONFIDENCE_CUSTOM_REASON = (
    "This wording has never shipped, so there is no precedent for it."
)


def confidence_for(channel: str, from_library: bool) -> tuple[str, str]:
    """
    Confidence and its reason, combining copy precedent with channel evidence.

    Observed channel rates plus library copy is the strongest position this
    tool can honestly claim, and it is still not "high": the rates are account
    averages rather than per-cohort, and no holdout has been run.
    """
    prov = CHANNEL_BENCHMARK_PROVENANCE.get(channel, {})
    observed = prov.get("kind") == "OBSERVED"
    if observed and from_library:
        return "moderate", (
            f"Copy has shipped before, and the {CHANNEL_LABELS.get(channel, channel)} "
            f"rates are learned from {prov['campaigns']} real campaigns and "
            f"{prov['sent']:,} sends. Not high: these are account averages, not "
            "per-cohort rates, and no holdout has been run."
        )
    if observed:
        return "low", (
            f"The {CHANNEL_LABELS.get(channel, channel)} rates are learned from "
            f"{prov['campaigns']} real campaigns, but this wording has never "
            "shipped, so the copy side has no precedent."
        )
    if from_library:
        return "low", (
            "Copy has shipped before, but no WhatsApp campaign exists in "
            "CleverTap, so the channel rates are an external prior rather than "
            "learned from Plum sends."
        )
    return "low", (
        "Neither side is anchored: unshipped wording on a channel with no "
        "campaign history in this account."
    )

CHANNELS = ["whatsapp", "email", "push"]          # never SMS
CHANNEL_LABELS = {"whatsapp": "WhatsApp", "email": "Email", "push": "Push"}

CONTROL_GROUP_SHARE = 0.05   # [B 13] 5% flat, no exceptions


# ===========================================================================
# Notes surfaced in the UI methodology panel.
# ===========================================================================

ANCHOR_NOTES = [
    {
        "title": "Two populations, never mix them",
        "body": (
            "The eligible base is 956,050 people in active, non-test orgs. "
            "CleverTap's live counts are account-wide because the /counts "
            "endpoints accept no org filter, 397,301 profiles launched the "
            "app in 364 days account-wide, while 216,924 people inside the "
            "eligible base have an install signal. Both are true; dividing one "
            "by the other is not."
        ),
    },
    {
        "title": "Push reach is a share of the whole base, not of app users",
        "body": (
            "The 23% base figure already includes everyone. It must not be "
            "re-based against an app-installed count, that inflates push "
            "reach roughly 4x. Confirmed by the no-app segment showing 11% "
            "push despite having no install signal."
        ),
    },
    {
        "title": "Stale push tokens inflate no-app reachability",
        "body": REACHABILITY_ANOMALY,
    },
    {
        "title": "The activation gap is 64 points, not 92",
        "body": (
            "~74% of orgs have at least one booking but only ~10% of employees "
            "ever have. The earlier 92-point figure was an artefact of "
            "computing org activation as 'does any user in this org type have "
            "a booking', which is always true."
        ),
    },
    {
        "title": "Funnel percentages are cumulative, not step-to-step",
        "body": (
            "TH 12.76% and HC 6.14% are homepage-to-booking conversion over "
            "120 days, not adoption rates. Adoption is ~10% of the eligible "
            "base and is a different metric with a different denominator. The "
            "HC report-view to download rate is 91.0% step-to-step; the 65%/59% "
            "figures quoted elsewhere are cumulative from booking confirmed."
        ),
    },
    {
        "title": "Age, gender and device are modeled",
        "body": (
            "None of the three exists in any source document, and CleverTap's "
            "aggregate counts endpoint silently ignores profile-property "
            "filters, so no live breakdown is obtainable. Cohort composition "
            "is calibrated so every aggregate reconciles exactly to the "
            "observed anchors above."
        ),
    },
    {
        "title": "Campaign performance is learned for push and email, modeled for WhatsApp",
        "body": BENCHMARK_PROVENANCE,
    },
]


def provenance() -> dict:
    """Machine-readable provenance for the UI methodology panel."""
    return {
        "observed": {
            "source": "CT Bible segment/funnel exports + CleverTap counts API",
            "pulled_at": CT_PULL_DATE.isoformat(),
            "window_days": CT_WINDOW_DAYS,
            "fields": [
                "total_eligible", "no_app_count", "segment_reachability",
                "th_funnel", "hc_funnel", "employee_activation_rate",
                "org_activation_rate", "dau", "mau_30d", "new_installs_30d",
                "sessions_30d", "annual_active_users",
            ],
        },
        "derived": {
            "fields": ["app_installed", "reach_decomposed"],
            "how": "Exact subtraction between the base and no-app segments.",
        },
        "modeled": {
            "fields": [
                "age_cohort_shares", "gender_split", "ios_android_split",
                "org_type_shares", "dnd_share_by_org", "campaign_benchmarks",
            ],
            "age": AGE_DATA_PROVENANCE,
            "device": DEVICE_DATA_PROVENANCE,
            "org": "[Bible 16] labels the org-type split MODELED, not measured.",
            "benchmarks": BENCHMARK_PROVENANCE,
        },
        "ct_live_scope": CT_LIVE_SCOPE,
        "dau_method": DAU_METHOD,
        "notes": ANCHOR_NOTES,
    }
