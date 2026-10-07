"""
CleverTap REST API connector for aggregate metrics.

Pulls real counts and trends — never individual profiles.
All queries require a date range (max 1-year window enforced).
Credentials read from ~/.insurwreck/credentials.json bundle.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("crewm.ct")

# Data access: aggregate event and profile counts from CleverTap API
# Protected by: read-only credentials, date range enforcement, no PII download


def _load_ct_credentials() -> dict:
    bundle_path = os.path.expanduser("~/.insurwreck/credentials.json")
    if os.path.exists(bundle_path):
        with open(bundle_path) as f:
            bundle = json.load(f)
        ct = bundle.get("services", {}).get("clevertap", {})
        if ct.get("account_id") and ct.get("passcode"):
            return ct
    return {
        "account_id": os.getenv("CT_ACCOUNT_ID", ""),
        "passcode": os.getenv("CT_PASSCODE", ""),
        "region": os.getenv("CT_REGION", "in1"),
    }


def _get_headers(creds: dict) -> dict:
    return {
        "X-CleverTap-Account-Id": creds["account_id"],
        "X-CleverTap-Passcode": creds["passcode"],
        "Content-Type": "application/json",
    }


def _base_url(creds: dict) -> str:
    region = creds.get("region", "in1")
    return f"https://{region}.api.clevertap.com/1/"


def _poll_result(url: str, headers: dict, req_id: str, max_wait: int = 30) -> Optional[dict]:
    poll_url = f"{url}?req_id={req_id}"
    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(2)
        try:
            r = requests.get(poll_url, headers=headers, timeout=10)
            data = r.json()
            if data.get("status") == "success":
                return data
        except Exception:
            pass
    return None


def _count_query(endpoint: str, event_name: str, from_date: int, to_date: int,
                 creds: dict, event_properties: Optional[list] = None) -> Optional[int]:
    url = _base_url(creds) + endpoint
    headers = _get_headers(creds)
    payload = {"event_name": event_name, "from": from_date, "to": to_date}
    if event_properties:
        payload["event_properties"] = event_properties
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=15)
        data = r.json()
        if data.get("status") == "success":
            return data.get("count", 0)
        if data.get("status") == "partial" and data.get("req_id"):
            result = _poll_result(url, headers, data["req_id"])
            if result:
                return result.get("count", 0)
        if data.get("status") == "fail":
            logger.warning(f"CT query failed for {event_name}: {data.get('error')}")
            return None
    except Exception as e:
        logger.warning(f"CT API error for {event_name}: {e}")
    return None


def _date_int(dt: datetime) -> int:
    return int(dt.strftime("%Y%m%d"))


def get_live_metrics() -> Optional[dict]:
    """Pull aggregate metrics from CleverTap. Returns None if credentials missing."""
    creds = _load_ct_credentials()
    if not creds.get("account_id") or not creds.get("passcode"):
        logger.info("No CT credentials — skipping live metrics")
        return None

    today = datetime.now()
    today_int = _date_int(today)
    thirty_days_ago = _date_int(today - timedelta(days=30))
    ninety_days_ago = _date_int(today - timedelta(days=90))
    year_start = _date_int(today.replace(month=1, day=1))

    logger.info("DATA_ACCESS: pulling aggregate CT metrics (counts only, no profiles)")

    metrics = {}

    # DAU — unique users who launched app today
    dau = _count_query("counts/profiles.json", "App Launched", today_int, today_int, creds)
    metrics["dau"] = dau

    # MAU — unique users who launched app in last 30 days
    mau = _count_query("counts/profiles.json", "App Launched", thirty_days_ago, today_int, creds)
    metrics["mau"] = mau

    # New installs last 30 days
    new_installs_30d = _count_query("counts/profiles.json", "App Installed", thirty_days_ago, today_int, creds)
    metrics["new_installs_30d"] = new_installs_30d

    # YTD total users who launched app
    ytd_active = _count_query("counts/profiles.json", "App Launched", year_start, today_int, creds)
    metrics["ytd_active_users"] = ytd_active

    # YTD total installs
    ytd_installs = _count_query("counts/profiles.json", "App Installed", year_start, today_int, creds)
    metrics["ytd_installs"] = ytd_installs

    # App Launched event count (last 30 days) — total sessions
    sessions_30d = _count_query("counts/events.json", "App Launched", thirty_days_ago, today_int, creds)
    metrics["total_sessions_30d"] = sessions_30d

    # App Uninstalled last 90 days
    uninstalls_90d = _count_query("counts/profiles.json", "App Uninstalled", ninety_days_ago, today_int, creds)
    metrics["uninstalls_90d"] = uninstalls_90d

    metrics["pulled_at"] = today.isoformat()
    metrics["date_range"] = f"{year_start}-{today_int}"

    # Filter out failed queries
    metrics = {k: v for k, v in metrics.items() if v is not None}

    logger.info(f"CT live metrics pulled: {len(metrics)} fields")
    return metrics if len(metrics) > 2 else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = get_live_metrics()
    if result:
        print(json.dumps(result, indent=2))
    else:
        print("No CT credentials or data available")


# ===========================================================================
# Resync
# ===========================================================================
#
# Data accessed: aggregate COUNTS from CleverTap's /1/counts endpoints only,
#   never a profile row. Five figures: annual actives, 30-day actives, DAU,
#   30-day installs, 30-day sessions.
# Why: the dashboard's live-usage block is a dated snapshot. This refreshes it
#   on demand so a demo is not quoting a stale day.
# What protects it: read-only credentials from the provisioned bundle, every
#   window explicitly bounded and never wider than a year (guardrail 5), counts
#   endpoints only, and an audit line per pull naming who asked and for what.

# Windows are expressed in complete days ending YESTERDAY. Today is never the
# end of a window: a same-day query returns a partial count. That bug reported
# DAU as 11,703 against a true 16,503, a 29% understatement that drifted
# upward through the day. See anchors.DAU_METHOD.
RESYNC_SPEC = [
    ("annual_active_users", "counts/profiles.json", "App Launched",  364,
     "unique profiles that launched the app, 364 complete days"),
    ("mau_30d",             "counts/profiles.json", "App Launched",   30,
     "unique profiles that launched the app, 30 complete days"),
    ("dau",                 "counts/profiles.json", "App Launched",    1,
     "unique profiles on the last COMPLETE day, never today"),
    ("new_installs_30d",    "counts/profiles.json", "App Installed",  30,
     "unique profiles that installed, 30 complete days"),
    ("sessions_30d",        "counts/events.json",   "App Launched",   30,
     "total App Launched occurrences, 30 complete days"),
]

MAX_WINDOW_DAYS = 365

# Serverless functions have a hard ceiling, and five sequential count queries
# with polling can exceed it. Past this budget the remaining fields are marked
# skipped and the partial result is returned: a resync that completes three of
# five and says so is worth more than a request that times out with nothing.
RESYNC_BUDGET_SECONDS = 22


def resync(requested_by: str = "unknown") -> dict:
    """
    Re-pull the live usage block from CleverTap and report it against what the
    app currently has anchored, so a stale figure is visible rather than
    silently replaced.

    Never raises: a failed pull is reported as a failed field, because a resync
    button that 500s tells the user nothing about which figure is stale.
    """
    import anchors as A

    creds = _load_ct_credentials()
    out: dict = {
        "ok": False,
        "requested_by": requested_by,
        "pulled_at": datetime.now().isoformat(),
        "anchored_at": A.CT_PULL_DATE.isoformat(),
        "scope": A.CT_LIVE_SCOPE,
        "dau_method": A.DAU_METHOD,
        "fields": [],
        "cannot_refresh": _cannot_refresh(),
    }
    if not creds.get("account_id") or not creds.get("passcode"):
        out["error"] = ("No CleverTap credentials in this environment, so "
                        "nothing was queried and the anchored figures stand.")
        return out

    yesterday = datetime.now() - timedelta(days=1)
    to_int = _date_int(yesterday)
    deadline = time.time() + RESYNC_BUDGET_SECONDS

    for key, endpoint, event, days, basis in RESYNC_SPEC:
        assert days <= MAX_WINDOW_DAYS, f"window for {key} exceeds a year"
        frm = _date_int(yesterday - timedelta(days=days - 1))
        logger.info(
            "DATA_ACCESS: ct resync by=%s field=%s event=%s window=%s..%s "
            "endpoint=%s (aggregate counts only)",
            requested_by, key, event, frm, to_int, endpoint,
        )
        if time.time() > deadline:
            out["fields"].append({
                "key": key, "label": key.replace("_", " "),
                "anchored": A.CT_LIVE.get(key), "live": None,
                "window": f"{frm} to {to_int}", "window_days": days,
                "basis": basis, "event": event, "status": "skipped",
            })
            continue
        value = _count_query(endpoint, event, frm, to_int, creds)
        anchored = A.CT_LIVE.get(key)
        row = {
            "key": key,
            "label": key.replace("_", " "),
            "anchored": anchored,
            "live": value,
            "window": f"{frm} to {to_int}",
            "window_days": days,
            "basis": basis,
            "event": event,
        }
        if value is None:
            row["status"] = "failed"
        elif anchored in (None, 0):
            row["status"] = "new"
        else:
            drift = value / anchored - 1
            row["drift"] = round(drift, 4)
            row["status"] = "moved" if abs(drift) >= 0.01 else "unchanged"
        out["fields"].append(row)

    got = [f for f in out["fields"] if f["live"] is not None]
    out["ok"] = len(got) > 0
    out["refreshed"] = len(got)
    out["failed"] = sum(1 for f in out["fields"] if f["status"] == "failed")
    out["skipped"] = sum(1 for f in out["fields"] if f["status"] == "skipped")
    if out["skipped"]:
        out["partial"] = (
            f"{out['skipped']} of {len(out['fields'])} figures were not "
            "queried: the pull ran past its time budget. The anchored values "
            "for those stand, and running it again picks up where it stopped."
        )
    if out["ok"]:
        out["live"] = {f["key"]: f["live"] for f in got}
        mau, sessions, dau = (out["live"].get("mau_30d"),
                              out["live"].get("sessions_30d"),
                              out["live"].get("dau"))
        if mau:
            if sessions:
                out["live"]["sessions_per_mau"] = round(sessions / mau, 2)
            if dau:
                out["live"]["dau_mau_ratio"] = round(dau / mau, 4)
    return out


def _cannot_refresh() -> list[dict]:
    """
    Figures this button deliberately does NOT touch, and why. Stating them is
    the point: a "resync" that silently leaves the most important number alone
    would imply the whole dashboard had just been re-verified.
    """
    return [
        {
            "field": "Eligible base and every cohort count",
            "reason": (
                "The eligible base must be filtered on "
                "warehouse_production_organisationStatus = active, and the "
                "/1/counts endpoints silently ignore profile property filters. "
                "A filtered query and a query with a deliberately nonsensical "
                "value both return the identical unfiltered total, so no "
                "org-active figure can be sourced or verified here. It has to "
                "come from a segment built in the CleverTap dashboard, where "
                "profile filters actually apply."
            ),
        },
        {
            "field": "Campaign performance, open and click rates",
            "reason": (
                "No per-campaign performance export exists in this account, so "
                "there is nothing to pull. Delivery, open and click stay "
                "external priors rather than learned rates."
            ),
        },
    ]
