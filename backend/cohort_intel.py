"""
Cohort intelligence: real clinical and behavioural patterns per age cohort.

Source: aggregate extraction from Plum's own telehealth consultation file
(34,528 valid members, 133,218 consults, 24 specialties) and health checkup
file (36,526 bookings, 148 biomarker columns). Both were aggregated in place;
this module holds distributions and rates only, never a member row, never
free text. doctor_notes was never read.

Everything here is OBSERVED. It is the deepest evidence the product has, and
it is what lets the assistant answer questions like "what is the dermatology
pattern in this cohort" or "which biomarker is most off at 36-40" with a real
number instead of a plausible sentence.

Three data-quality decisions, all auditable:
  1. patient_age is dirty in the source (values from -517 to 2026). Rows are
     filtered to 15-80, which drops 2.87%. The filter is reported, not hidden.
  2. appointment_created_at is stored in UTC. Converted to IST (UTC+5:30).
     Without this the booking curve peaks at 05:00, which is nonsense for
     India, and it silently corrupts every timing recommendation.
  3. The health checkup file carries no age column, so ages come from joining
     member_id to the telehealth file. That matches 42.6% of bookings, and the
     match rate is surfaced with every biomarker figure.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

_PATH = os.path.join(os.path.dirname(__file__), "aggregates", "real_aggregates.json")


@lru_cache(maxsize=1)
def data() -> dict:
    with open(_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Provenance, surfaced anywhere these numbers appear
# ---------------------------------------------------------------------------

def provenance() -> dict:
    d = data()
    return {
        "th": {
            "members_valid": d["th_quality"]["rows_valid"],
            "members_raw": d["th_quality"]["rows_raw"],
            "dropped_pct": d["th_quality"]["dropped_pct"],
            "filter": d["th_quality"]["filter"],
            "consults": d["booking_clock_ist"]["total"],
            "specialties": len(d["specialty_totals"]),
            "window": d["booking_clock_ist"]["window"],
        },
        "hc": {
            "bookings": d["hc_meta"]["bookings"],
            "age_matched": d["hc_join"]["age_matched"],
            "match_rate": d["hc_join"]["match_rate"],
            "join": d["hc_join"]["how"],
        },
        "timezone": d["booking_clock_ist"]["tz_note"],
        "label": "OBSERVED",
    }


# ---------------------------------------------------------------------------
# Specialty patterns
# ---------------------------------------------------------------------------

def specialty_mix(cohort: str) -> list[dict]:
    """Top specialties for a cohort, as share of that cohort's consults."""
    mix = data()["specialty_by_cohort"].get(cohort, {})
    return [{"specialty": k, "share": v} for k, v in mix.items()]


def specialty_index(cohort: str, specialty: str) -> dict | None:
    """
    One specialty in one cohort, indexed against every other cohort.

    The index is what makes this useful: dermatology is 13.8% of 26-35
    consults, which only means something next to the 18.2% it reaches at
    21-25. Index 100 is the cross-cohort average.
    """
    d = data()["specialty_by_cohort"]
    if cohort not in d:
        return None
    shares = {c: v.get(specialty) for c, v in d.items() if specialty in v}
    if cohort not in shares or not shares:
        return None
    avg = sum(shares.values()) / len(shares)
    peak = max(shares, key=lambda c: shares[c])
    return {
        "specialty": specialty,
        "cohort": cohort,
        "share": shares[cohort],
        "index_vs_average": round(shares[cohort] / avg * 100) if avg else 100,
        "peak_cohort": peak,
        "peak_share": shares[peak],
        "all_cohorts": shares,
        "label": "OBSERVED",
    }


# Words that appear in ordinary questions and must never resolve to a
# specialty. Kept explicit rather than inferred, because a silent
# mis-resolution here produces a confident answer about the wrong condition.
STOPWORDS = {
    "is", "the", "in", "on", "at", "of", "for", "and", "a", "an", "to", "as",
    "what", "which", "who", "how", "why", "when", "where", "do", "does", "did",
    "are", "was", "can", "should", "would", "will", "most", "least", "more",
    "less", "common", "commonly", "pattern", "patterns", "cohort", "cohorts",
    "band", "bands", "age", "group", "groups", "people", "users", "members",
    "me", "my", "i", "it", "its", "that", "this", "these", "those", "with",
    "by", "vs", "versus", "than", "then", "about", "into", "from", "have",
    "has", "had", "get", "give", "show", "tell", "problem", "problems",
    "health", "issue", "issues", "consult", "consults", "consultation",
    "consultations", "book", "books", "booked", "booking", "bookings",
    "send", "sending", "sent", "reach", "target", "segment", "campaign",
}


def find_specialty(term: str) -> str | None:
    """
    Resolve a loose mention to a real specialty name, or None.

    Returning None is the correct answer far more often than it looks, and is
    much better than a confident wrong specialty.
    """
    t = term.lower().strip()
    names = list(data()["specialty_totals"].keys())
    for n in names:
        if t == n.lower():
            return n
    aliases = {
        "derma": "Dermatologist", "dermatology": "Dermatologist", "skin": "Dermatologist",
        "gynae": "Obstetrician-Gynecologist", "gyno": "Obstetrician-Gynecologist",
        "obgyn": "Obstetrician-Gynecologist", "gynecologist": "Obstetrician-Gynecologist",
        "mental": "Psychologist", "therapy": "Psychologist", "psychology": "Psychologist",
        "psych": "Psychologist", "counsel": "Psychologist",
        "gp": "General Physician", "physician": "General Physician",
        "nutrition": "Nutrition-Dietetics", "diet": "Nutrition-Dietetics",
        "dietician": "Nutrition-Dietetics", "dietitian": "Nutrition-Dietetics",
        "ortho": "Orthopedics", "bone": "Orthopedics", "joint": "Orthopedics",
        "paed": "Pediatrician", "ped": "Pediatrician", "child": "Pediatrician",
        "kid": "Pediatrician", "ent": "ENT Surgeon", "cardio": "Cardiologist",
        "heart": "Cardiologist", "diabet": "Diabetologist", "endo": "Endocrinologist",
        "thyroid": "Endocrinologist", "gut": "Gastroenterologist",
        "stomach": "Gastroenterologist", "gastro": "Gastroenterologist",
        "neuro": "Neurologist", "eye": "Ophthalmologist", "physio": "Physiotherapist",
        "psychiatr": "Psychiatrist",
    }
    # An alias only counts if the token STARTS with it. "cardio" matching
    # "cardiologist" is intended; a bare substring match is not.
    for k, v in aliases.items():
        if t.startswith(k) and v in names:
            return v

    # The loose pass used to accept any substring, which let stopwords resolve
    # to real specialties: "is" matched Cardiologist, "the" matched
    # Physiotherapist, "in" matched Endocrinologist. A question about
    # dermatology therefore answered about cardiology, because "is" appears
    # before "dermatology" in the sentence. Now a token must be at least four
    # characters, must not be a stopword, and must share a prefix with a whole
    # word inside the specialty name.
    if len(t) < 4 or t in STOPWORDS:
        return None
    for n in names:
        for word in re.split(r"[^a-z]+", n.lower()):
            if len(word) < 4:
                continue
            if word.startswith(t) or t.startswith(word):
                return n
    return None


def rising_specialties(cohort: str, top: int = 3) -> list[dict]:
    """Specialties this cohort over-indexes on. The 'what is different here'
    answer, computed rather than narrated."""
    d = data()["specialty_by_cohort"]
    if cohort not in d:
        return []
    out = []
    for spec, share in d[cohort].items():
        idx = specialty_index(cohort, spec)
        if idx and idx["index_vs_average"] > 105 and share >= 0.01:
            out.append({"specialty": spec, "share": share,
                        "index": idx["index_vs_average"]})
    out.sort(key=lambda x: -x["index"])
    return out[:top]


# ---------------------------------------------------------------------------
# Biomarkers
# ---------------------------------------------------------------------------

SHORT = {
    "Vitamin D 25-OH": "Vitamin D",
    "Vitamin B12": "Vitamin B12",
    "Glycosylated Haemoglobin (HbA1c)": "HbA1c",
    "Cholesterol LDL - Direct": "LDL cholesterol",
    "Cholesterol HDL": "HDL cholesterol",
    "Cholesterol Total": "Total cholesterol",
    "Triglycerides": "Triglycerides",
    "Glucose Fasting": "Fasting glucose",
    "Alanine Aminotransferase (SGPT)": "Liver enzyme (SGPT)",
    "Uric Acid": "Uric acid",
    "Haemoglobin": "Haemoglobin",
    "TSH": "TSH",
}


def biomarkers(cohort: str) -> dict | None:
    """Biomarker abnormality rates for a cohort, worst first."""
    d = data()["biomarkers_by_cohort"].get(cohort)
    if not d:
        return None
    overall = data()["biomarkers_overall"]
    marks = []
    for col, v in d["markers"].items():
        base = overall.get(col, {})
        marks.append({
            "marker": SHORT.get(col, col),
            "raw": col,
            "abnormal_pct": v["abnormal_pct"],
            "median": v["median"],
            "n": v["n"],
            "basis": base.get("basis", ""),
            "threshold": base.get("threshold"),
            "direction": base.get("direction"),
            "vs_all_cohorts": round(v["abnormal_pct"] - base.get("abnormal_pct", v["abnormal_pct"]), 1),
        })
    marks.sort(key=lambda m: -m["abnormal_pct"])
    return {"bookings": d["bookings"], "markers": marks, "label": "OBSERVED"}


def biomarker_trend(marker_short: str) -> dict | None:
    """One marker across every cohort: the age gradient, which is where the
    campaign angle actually comes from."""
    raw = next((k for k, v in SHORT.items() if v.lower() == marker_short.lower()), None)
    if not raw:
        raw = next((k for k in SHORT if marker_short.lower() in k.lower()), None)
    if not raw:
        return None
    series = {}
    for c, v in data()["biomarkers_by_cohort"].items():
        m = v["markers"].get(raw)
        if m:
            series[c] = m["abnormal_pct"]
    if not series:
        return None
    lo = min(series, key=lambda c: series[c])
    hi = max(series, key=lambda c: series[c])
    base = data()["biomarkers_overall"].get(raw, {})
    return {
        "marker": SHORT[raw], "raw": raw, "series": series,
        "worst_cohort": hi, "worst_pct": series[hi],
        "best_cohort": lo, "best_pct": series[lo],
        "spread": round(series[hi] - series[lo], 1),
        "overall_pct": base.get("abnormal_pct"),
        "basis": base.get("basis", ""),
        "label": "OBSERVED",
    }


def find_marker(term: str) -> str | None:
    t = term.lower()
    aliases = {
        "vitamin d": "Vitamin D", "vit d": "Vitamin D", "vitd": "Vitamin D",
        "b12": "Vitamin B12", "b-12": "Vitamin B12", "cobalamin": "Vitamin B12",
        "hba1c": "HbA1c", "a1c": "HbA1c", "sugar": "HbA1c", "diabet": "HbA1c",
        "ldl": "LDL cholesterol", "hdl": "HDL cholesterol",
        "cholesterol": "LDL cholesterol", "lipid": "LDL cholesterol",
        "triglyc": "Triglycerides", "glucose": "Fasting glucose",
        "liver": "Liver enzyme (SGPT)", "sgpt": "Liver enzyme (SGPT)",
        "alt": "Liver enzyme (SGPT)", "uric": "Uric acid", "gout": "Uric acid",
        "haemoglobin": "Haemoglobin", "hemoglobin": "Haemoglobin",
        "anaemia": "Haemoglobin", "anemia": "Haemoglobin", "iron": "Haemoglobin",
        "thyroid": "TSH", "tsh": "TSH",
    }
    for k, v in aliases.items():
        if k in t:
            return v
    return None


def worst_marker(cohort: str) -> dict | None:
    b = biomarkers(cohort)
    return b["markers"][0] if b and b["markers"] else None


def steepest_gradient(top: int = 3) -> list[dict]:
    """Markers that change most across the age range. These are the strongest
    age-targeted campaign angles in the whole dataset."""
    out = []
    for short in set(SHORT.values()):
        t = biomarker_trend(short)
        if t and t["spread"] >= 5:
            out.append(t)
    out.sort(key=lambda t: -t["spread"])
    return out[:top]


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------

def th_engagement(cohort: str) -> dict | None:
    m = data()["cohort_th_meta"].get(cohort)
    if not m:
        return None
    all_meta = data()["cohort_th_meta"]
    avg = sum(v["consults_per_member"] for v in all_meta.values()) / len(all_meta)
    return {**m, "intensity_index": round(m["consults_per_member"] / avg * 100) if avg else 100,
            "label": "OBSERVED"}


def booking_clock(cohort: str | None = None) -> dict:
    """The real booking clock in IST. This is the evidence behind send timing."""
    d = data()
    if cohort and cohort in d.get("booking_clock_by_cohort", {}):
        c = d["booking_clock_by_cohort"][cohort]
        shares = {int(k): v for k, v in c["shares"].items()}
        n = c["n"]
    else:
        shares = {int(k): v for k, v in d["booking_clock_ist"]["shares"].items()}
        n = d["booking_clock_ist"]["total"]
    ranked = sorted(shares, key=lambda h: -shares[h])
    return {
        "shares": shares, "n": n,
        "peak_hour": ranked[0],
        "top_hours": ranked[:4],
        "morning_share": round(sum(shares[h] for h in range(9, 14)), 4),
        "evening_share": round(sum(shares[h] for h in range(17, 21)), 4),
        "night_share": round(sum(shares[h] for h in range(21, 24)), 4),
        "dead_share": round(sum(shares[h] for h in range(1, 7)), 4),
        "weekday": d["booking_weekday_ist"],
        "tz": "IST",
        "label": "OBSERVED",
    }


def consulter_vs_base(cohort: str, base_share: float) -> dict | None:
    """
    How a cohort's share of actual telehealth consulters compares to its share
    of the eligible base. Over-indexing means the cohort already leans in.

    This is a comparison of two different populations and is labelled as such:
    consulters are self-selected and include dependents, the base is employees.
    """
    m = data()["cohort_th_meta"].get(cohort)
    if not m or not base_share:
        return None
    ratio = m["share_of_consulters"] / base_share
    return {
        "consulter_share": m["share_of_consulters"],
        "base_share": round(base_share, 4),
        "index": round(ratio * 100),
        "reads": ("over-indexes on telehealth" if ratio > 1.15
                  else "under-indexes on telehealth" if ratio < 0.85
                  else "uses telehealth in line with its size"),
        "caveat": ("consulters are self-selected and include dependents; "
                   "the base is employees, so treat this as direction not a rate"),
        "label": "DERIVED",
    }


def gender_split() -> dict:
    return {**data()["th_gender"], "label": "OBSERVED",
            "basis": "telehealth consulters, 34,528 members"}


# ===========================================================================
# Age band x gender
# ===========================================================================
#
# "Which age bracket and gender faces which health problem most commonly."
#
# Two readings, deliberately kept apart, because they answer different
# questions and the naive one is misleading on its own:
#
#   leading    the specialty this group consults most, excluding General
#              Physician. GP is first in every one of the twelve cells, so
#              reporting it says nothing about the group.
#   distinctive the specialty most over-represented against the same gender's
#              overall mix. This is what actually separates one band from
#              another, and it is the useful one for targeting.
#
# Structural specialties are excluded from the distinctive reading: a
# pediatrician indexing at 15x in the under-20 band is an age-eligibility
# artefact, not a health pattern.

GENERIC_SPECIALTY = {"General Physician"}
STRUCTURAL = {"u20": {"Pediatrician"}}


def gender_available() -> bool:
    return bool(data().get("specialty_by_cohort_gender"))


def gender_cell(cohort_key: str, gender: str) -> dict | None:
    g = (gender or "").strip().upper()
    if g in ("F", "WOMEN", "WOMAN", "FEMALES"):
        g = "FEMALE"
    if g in ("M", "MEN", "MAN", "MALES"):
        g = "MALE"
    d = data()
    cell = (d.get("specialty_by_cohort_gender", {}).get(cohort_key, {}) or {}).get(g)
    if not cell:
        return None

    rows = cell["top"]
    leading = next((r for r in rows if r["specialty"] not in GENERIC_SPECIALTY), None)
    excluded = GENERIC_SPECIALTY | STRUCTURAL.get(cohort_key, set())
    candidates = [r for r in rows
                  if r["specialty"] not in excluded and r["index_vs_gender"]]
    distinctive = max(candidates, key=lambda r: r["index_vs_gender"], default=None)
    generic = next((r for r in rows if r["specialty"] in GENERIC_SPECIALTY), None)

    markers = (d.get("biomarkers_by_cohort_gender", {})
               .get(cohort_key, {}) or {}).get(g) or []
    return {
        "gender": g,
        "consults": cell["consults"],
        "leading": leading,
        "distinctive": distinctive,
        "generic": generic,
        "markers": markers[:3],
        "all": rows,
    }


def gender_compare(cohort_key: str) -> dict | None:
    """Both genders for one band, so the contrast is the answer."""
    f, m = gender_cell(cohort_key, "FEMALE"), gender_cell(cohort_key, "MALE")
    if not f and not m:
        return None
    return {"FEMALE": f, "MALE": m}


def gender_quality() -> dict:
    return data().get("gender_crosstab_quality", {})


def gender_sweep() -> list[dict]:
    """Every band x gender cell, for a 'which group has the worst X' question."""
    out = []
    for band in (data().get("specialty_by_cohort_gender") or {}):
        for g in ("FEMALE", "MALE"):
            c = gender_cell(band, g)
            if c:
                out.append({"cohort": band, **c})
    return out
