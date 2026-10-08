# Audience Rules

**What this file is for.** The plain-English, checkable rules for "who is this
campaign allowed to reach." Anyone drafting, reviewing, or shipping a Welcome or
Renewal campaign through Crew M should be able to open this file and see, in
order, exactly what the audience must pass before it leaves the building.

**Scope:** Welcome and Renewal campaigns. Benefits-usage campaigns are not yet
covered here — see Section 4.

---

## 1. The rule everyone must pass

Every targeted profile must satisfy all four of these, with no exceptions:

| # | Property | Required value |
|---|---|---|
| 1 | `warehouse_production_organisationStatus` | `== ACTIVE` |
| 2 | `warehouse_production_isTestOrganisation` | `!= true` |
| 3 | `is_in_DND_CT` | `!= true` |
| 4 | `warehouse_production_removed` | `!= true` |

Rule 1 is the only authoritative signal for "is this organisation live." Do not
substitute `isActive`, `status`, or any inferred field — they can and do drift.

Rules 2 and 4 keep internal test orgs and tombstoned records out of the send.
Rule 3 honours the Do-Not-Disturb list; it is not optional, and it is not
negotiated per-campaign.

A profile that fails any one of these does not receive the campaign. There is no
"close enough" tier.

---

## 2. The mandatory safety check

Before any Welcome or Renewal campaign is scheduled, run the following, in
order:

1. **Call `estimate_only` first.** Compare the returned reach against the known
   organisation headcount for the targeted segment. If the estimate exceeds the
   expected size by more than 2×, stop and investigate — this is the signature
   of the CleverTap targeting bug documented in `KNOWN_ISSUES.md`.
2. **Add throttle limits** on the campaign itself (per-minute cap), so a
   mis-targeted send cannot drain the whole audience before anyone notices.
3. **Hard caps per campaign:**
   - Welcome: **50,000**
   - Renewal: **50,000**
   A single scheduled send that would exceed its cap must be split or
   re-scoped; it is not raised ad hoc.
4. **Until the CleverTap targeting bug is fixed**, use **saved segment IDs
   built by hand in the CleverTap UI**, not rule-expression segments assembled
   via API. The hand-built segments reconcile correctly; the API-assembled
   equivalents silently return the entire profile base (~680K). See
   `KNOWN_ISSUES.md` for the full evidence.

---

## 3. Quiet hours

No campaign in scope sends between **21:00 and 09:00 Asia/Kolkata**, local to
the recipient's record. This applies to WhatsApp, push, email and SMS — all
channels, no overrides for "urgent" or "small test."

Schedule into the next permitted window instead; nothing in these two campaign
families is time-critical enough to breach quiet hours.

---

## 4. Not yet covered

**Benefits-usage campaigns** (reminders, nudges, feature announcements for
members who already have access) are out of scope for this file. They have
different suppression rules, a different cadence tolerance, and in some cases
run against a cohort — not an org — definition.

A separate rules file will be added when that lane is formalised. Until then,
do not reuse the Welcome/Renewal caps or quiet-hour window as if they applied
to usage campaigns.
