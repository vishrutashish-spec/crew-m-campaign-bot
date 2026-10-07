# CleverTap Platform Reference — Crew M Build Guide

> **Purpose**: Complete CleverTap platform knowledge for building Crew M. Covers API
> endpoints, data model, segmentation engine, campaign analytics, intelligent features,
> and operational constraints. Cross-referenced with Plum's actual CT setup from the
> Master Bible.
>
> **Not a replacement for the Bible** — the Bible (CREW_M_MASTER_CT_BIBLE.md) has
> Plum-specific segment definitions, event names, funnel numbers, and domain rules.
> This document covers the platform itself.

---

## 1. Authentication & Infrastructure

### Credentials

Every API request requires two headers:

```
X-CleverTap-Account-Id: <Project ID>
X-CleverTap-Passcode: <Account Passcode or User-Passcode>
Content-Type: application/json   (POST only)
```

Get from: CleverTap Dashboard → Settings → Project.

- **Account Passcode**: org-level, up to 100 per account, shareable across integrations
- **User Passcode**: per-dashboard-user, finite (1–365 days) or infinite (10-year) validity — recommended for API integrations (smaller blast radius if leaked)

**For Crew M**: Store in `.env.local` as `CT_ACCOUNT_ID` and `CT_PASSCODE`. Never hardcode.

### Regional Base URLs

Account is pinned to one region; must use the matching endpoint for all calls:

| Region | Code | Base URL |
|--------|------|----------|
| India | in1 | `https://in1.api.clevertap.com/1/` |
| US | us1 | `https://us1.api.clevertap.com/1/` |
| Singapore | sg1 | `https://sg1.api.clevertap.com/1/` |
| Europe | eu1 | `https://eu1.api.clevertap.com/1/` |
| Indonesia | aps3 | `https://aps3.api.clevertap.com/1/` |
| Middle East | mec1 | `https://mec1.api.clevertap.com/1/` |

**For Plum**: Almost certainly `in1` (India region). Confirm with Vishrut.

### Rate Limits

CleverTap uses **concurrency limits, not time-window rate limits**:

| API Type | Concurrent Limit |
|----------|-----------------|
| Data upload (events, profiles, device tokens) | 15 concurrent requests |
| Everything else (campaigns, segments, reports, counts, trends) | 3 concurrent requests |
| Campaign create/stop | 3 req/sec |
| Campaign report | 60 req/min per campaign |

Exceeding → HTTP 429 "Too many concurrent requests".

**Design implication for Crew M**: Backend needs a semaphore/queue limiting CT API calls to 3 concurrent. Use exponential backoff on 429/500/503. Set 60s timeout per request.

### Async Polling Pattern

Many CT endpoints are async — they return `{"status":"partial","req_id":"..."}` on first call. Poll with `GET ...?req_id=` every 30 seconds until `status: "success"`.

Affected endpoints: Event Count, Profile Count, Trends, Top Property Counts.

---

## 2. CleverTap Data Model

### Events

- A timestamped action a user took (e.g. "Consultation Booked")
- Each event has a **name** + up to **256 properties** (key-value pairs)
- **System events**: auto-captured by SDK, properties prefixed `CT` (e.g. App Launched, App Installed, Notification Viewed)
- **Custom events**: developer-defined (e.g. `healthCheckupbooking_confirmed`, `Telehealth_DoctorList_Viewed`)
- Property types: String, Boolean, Integer, Float, Double, Date, nested objects
- Scalar values capped at 512 chars, keys at 120 chars

**Plum's CT**: 993 events (628 active, 39 system, 954 custom). Top by volume: pathViewed (5.2M), nativeDisplay_home_card (1.5M), App Launched (570K). See Bible Section 3 for confirmed event names.

### User Profiles

Three pillars: **Identifiers**, **Properties**, **Events**.

- Every user gets a unique **CleverTap ID**
- Optional external identifiers: email, phone, Facebook ID, custom user ID
- **System properties**: Name, Email, Identity, Phone, Gender, DOB, Age, Timezone, channel opt-in flags (MSG-email, MSG-push, MSG-sms, MSG-whatsapp)
- Up to **256 custom property keys** per account
- Multi-value arrays: max 100 entries × 512 chars each

**Plum's CT**: 249 active user properties. Key ones: `is_in_DND_CT` (373 campaigns), `warehouse_production_inviteCreatedAt` (339), `warehouse_production_organisationId` (267). See Bible Section 4.

### Identity Resolution

- Anonymous profiles carry only CleverTap ID (no addressable identity)
- **Addressable/identified profiles** have email or phone → reachable directly
- When anonymous device logs in with known identity → event history merges into existing profile
- Same login across multiple devices → unified cross-device profile
- "Customer" sub-classification applies once a purchase event is recorded

### Campaigns vs Journeys

| | Campaign | Journey |
|--|----------|---------|
| **Structure** | One message, one moment | Multi-step, branching flow |
| **Channels** | Single channel per send | Combines channels in sequence |
| **Targeting** | Static segment at send time | Entry criteria + reactive branching |
| **Use case** | Broadcast, one-off moments | Nurture, habit building, lifecycle |
| **API access** | Full CRUD + reporting | Limited (no "list journeys" endpoint) |

**Plum context**: Adoption growth (12% → 35%) is Journey territory. Campaigns support one-off moments (open enrolment, seasonal weeks).

### Segments

Four types:

1. **Past Behavior** — historical criteria combining actions, inactions, property filters
2. **Live User** — real-time qualification on behavior match
3. **Custom List** — uploaded user lists (CSV)
4. **Partner Segments** — synced from ad partners

**System segments** (pre-built): All Users, First-time Users, Engaged Users (4+ weekly sessions), Test Users.

**Segment Builder** has three rule families:
- **USER PROPERTY**: static facts (partner_type, org ID, DND flag, plan status)
- **USER BEHAVIOR**: actions taken/not taken (`Event Did` / `Event Have Not Done` / `Event Combination Did Any Of`) with count operators and time windows
- **USER INTERESTS**: event property values, time of day, day of week

---

## 3. API Endpoints Reference

### 3.1 Events API

**Get Events** — two-step cursor flow:

```
POST /1/events.json
{
  "event_name": "Telehealth_DoctorList_Viewed",
  "from": 20260101,
  "to": 20260801,
  "batch_size": 5000    // default 500, max 5000
}
→ {"status":"success", "cursor":"..."}

GET /1/events.json?cursor=<cursor>
→ {records: [{profile, events, ts, event_props, session_props}], next_cursor}
```

- Cursor expires: **4 hours after creation** or **1 hour of inactivity**
- Repeat GET with `next_cursor` until exhausted

**Get Event Count** — async:

```
POST /1/counts/events.json
{
  "event_name": "healthCheckupbooking_confirmed",
  "from": 20260101,
  "to": 20260801,
  "event_properties": [
    {"name": "package", "operator": "equals", "value": "CORPORATE"}
  ]
}
```

Operators: `equals`, `contains`, `not_contains`, `in`, `not_in`, `gt/gte/lt/lte`, `exists/not_exists`. Properties are AND-combined.

Returns `{"status":"partial","req_id":"..."}` → poll every 30s.

### 3.2 User Profiles API

**Get Profiles by event** — same cursor pattern:

```
POST /1/profiles.json
{
  "event_name": "App Launched",
  "from": 20260101,
  "to": 20260801
}
→ {"cursor":"..."}

GET /1/profiles.json?cursor=<cursor>
→ {records: [{identity, email, name, profileData, events, platformInfo}]}
```

Cursor valid **4 days** (longer than Events cursor).

**Get Profile by ID**:

```
GET /1/profile.json?identity=<user_id>
→ {record: {identity, email, profileData, events}}
```

Exactly one identifier param: `email`, `identity`, or `objectId`.

**Get Profile Count** — async, same polling pattern as Event Count.

### 3.3 Campaigns API

**List Campaigns**:

```
POST /1/targets/list.json
{"from": 20260101, "to": 20260801}
→ [{id, name, scheduled_on, status}]
```

Status values: `scheduled`, `pending`, `running`, `paused`, `stopped`, `completed`.

**Get Campaign Report** (single campaign):

```
POST /1/targets/result.json
{"id": 1234567890}
→ {"result": {"sent": N, "clicked": N}}
```

Only `sent` + `clicked`. No delivered/opened/converted. 409s until campaign fully completed. Rate limit: 60 req/min per campaign.

### 3.4 Message Reports API (THE KEY ENDPOINT)

This is the richest analytics endpoint for Crew M:

```
POST /1/message/report.json
{
  "from": 20260101,
  "to": 20260801,
  "channel": ["push", "email", "sms", "whatsapp"],
  "delivery": ["one_time", "inaction", "action", "recurring"],
  "status": ["completed"],
  "daily": true    // day-wise split
}
```

**Filter params**:
- `channel[]`: push, email, sms, browser, inapp, webhooks, web_pop_up, exit_intent, native_display, inbox, tiktok, nativedisplay
- `delivery[]`: one_time, inaction, action, recurring, property_time, api, multiple_dates
- `status[]`: campaign status filter
- `message_type[]`: single, ab, message_on_user_property
- `label[]`: campaign label filter
- `daily`: boolean — if true, returns day-wise breakdown

**Response** per message:
- `message_name`, `channel`, `delivery`, `start_date`, `status`
- `sent`, `viewed`, `clicked`
- `conversion_event`, `labels`, `device`

**Crew M usage**: This is the primary endpoint for building the campaign performance dataset. Pull all campaigns with `daily: true` to get temporal patterns. Filter by channel to build channel-preference models.

**Gaps**: No explicit "delivered" count or numeric conversion count field in the documented response. Viewed ≈ delivered for push; for email, viewed = opened.

### 3.5 Trends API

```
POST /1/counts/trends.json
{
  "event_name": "healthCheckupbooking_confirmed",
  "from": 20260101,
  "to": 20260801,    // max 1 year span
  "unique": true,
  "groups": {
    "by_channel": {
      "property_type": "event_properties",
      "name": "channel",
      "top_n": 5,
      "order": "desc"
    }
  },
  "trend_type": "weekly"    // daily|weekly|monthly
}
```

- Max **1 year span** (aligns with Plum's data governance guardrail)
- Up to **5 group-by dimensions**
- Async polling pattern
- Returns time-bucketed counts (daily=YYYYMMDD, weekly=YYYYWW, monthly=YYYYMM keys)

### 3.6 Top Property Counts API

```
POST /1/counts/top.json
{
  "event_name": "Telehealth_DoctorList_Viewed",
  "from": 20260101,
  "to": 20260801,
  "groups": {
    "specialty": {
      "property_type": "event_properties",
      "name": "specialist_specialty",
      "top_n": 20,
      "order": "desc"
    }
  }
}
```

`property_type` options: `event_properties`, `profile_fields`, `session_properties`, `app_fields`, `demographics`, `technographics`, `reachability`, `geo_fields`.

### 3.7 Real-Time Counts

```
POST /1/now.json
{
  "user_type": true,
  "session_source": true,
  "browser": true,
  "os": true,
  "device": true
}
→ active users in last 5 minutes, with optional breakdowns
```

### 3.8 Segments (Limited API Access)

**API Segments** - Private Beta only, requires CSM access. Confirm availability on the current CleverTap tier before building against it.

**Custom List API** — Generally available, 3-step CSV upload:
1. `POST /1/get_custom_list_segment_url` → pre-signed URL (24h validity)
2. `PUT` CSV to the URL
3. `POST /1/upload_custom_list_segment_completed` with `{name, email, filename, creator, url, replace}`

Max 5GB via API, 50MB via dashboard.

---

## 4. Campaign Analytics Deep Dive

### Conversion Pipeline (All Channels)

```
Sent → Delivered → Viewed → Clicked → Converted
```

Conversion event counted **once per user per campaign** even if repeated.

### Channel-Specific Tracking

| Channel | Sent | Delivered | Viewed/Opened | Clicked | Notes |
|---------|------|-----------|---------------|---------|-------|
| Push | Yes | Yes (SDK ≥3.5.1) | Impressions | Yes | CTR = clicked/sent. View-through + click-through conversion tracked separately |
| Email | Yes | Yes | Opens (pixel) | Yes | Requires email-provider integration |
| SMS | Yes | Yes | N/A | Link clicks | Via SMS provider integration |
| WhatsApp | Yes | Yes | Read receipts | Yes | Supports two-way messaging via Conversations inbox |
| In-App | N/A | N/A | Impressions | Yes | Shown while user is in-app |
| App Inbox | N/A | Fetched on app launch/session | Views | Yes | Persistent on-device message center |

### Report Types Available

| Report | What It Shows | Crew M Relevance |
|--------|--------------|------------------|
| **Campaign Reports** | Per-campaign sent/viewed/clicked/converted | Training data for prediction models |
| **Journey Reports** | Node-level funnel stats along journey paths | Understanding multi-step campaign sequences |
| **Funnels** | Step-by-step event drop-off with conversion window | Validating TH/HC funnel numbers |
| **Cohort Analysis** | Retention/behavior tracking over time by starting behavior | Adoption trajectory analysis |
| **Trends** | Event counts over time with property breakdowns | Temporal pattern discovery |
| **Flows** | Open-ended multi-path exploration | Discovery mode for user paths |
| **RFM** | Recency × Frequency grid with monetary overlay | User value segmentation |

### A/B Testing

- Control variant + up to **7 test variants** on templated keys
- Statistical significance via **Welch's t-test**
- Confidence threshold = `100 - (5 / (variants - 1))`
- Up to 5 conversion goals per test
- Partial rollout via "test group %"
- Winner declaration is **manual**, not auto-promoted

### Funnel Analysis Features

- Ordered sequence of events with configurable conversion window (default 5 days)
- **Actionable funnels**: can launch a campaign/journey targeting the drop-off cohort directly
- **Flows** tab: sibling feature for open-ended, multi-path exploration

---

## 5. Intelligent Features

### IntelliTime (Best Time to Send)

- Splits each day into **twelve 2-hour buckets** (absolute clock time)
- Assigns each user to their historically best-performing bucket using up to **180 days** of activity
- Falls back to admin-defined window for users lacking history
- Max **10 IntelliTime configs** per account; one must be marked Default for Journey use
- Supported on: Email, SMS, Push, WhatsApp, Web Push
- Automatically applies user timezone (cannot disable)
- If computed bucket collides with user's DND window → **message discarded, not rescheduled**
- Incompatible with global throttle limits

**Crew M implication**: We can pull user activity timestamps to build our own send-time model, validated against CT's IntelliTime buckets.

### IntelliNODE (Journey Path Testing)

- Journey controller node for live multivariate path testing
- Up to **7 parallel paths** varying timing/messaging/channel/creative
- **Automated Mode**: equal traffic split, re-evaluates every 5 minutes, shifts traffic toward better-converting path
- **Manual Mode**: fixed distribution percentages
- Uses one shared Goal event for optimization

### IntelliChannel (Preferred Channel)

- ML scoring of each user's most-responsive channel (Push/Email/SMS/WhatsApp)
- Rolling **90-day window** based on sent/viewed/clicked interactions
- Refreshed **daily**
- Requires: ≥2 active channels, multi-channel reach, ≥3 total engagements (else "Not Enough Data")
- Usable as: segment filter or Journey Conditional-Split branch

**Crew M implication**: We can build our own channel preference model from the same underlying data, but CT already has one running. Our model should add persona-level channel preferences that CT's per-user model doesn't surface.

### Frequency Capping (Two Tiers)

1. **Global Frequency Caps**: per-channel message ceilings (e.g. "3 pushes in 7 days"), dwell-time minimums between messages (15 min–7 days), Global/Ad-hoc Throttle limits
2. **Message-level caps**: per-campaign re-qualification limits (send-every-time vs enforce minimum gap of 5 min–30 days)

Stricter of the two always wins. Violations appear in campaign error reports.

### DND & Delivery Controls

- Configurable DND days/hours per campaign
- Choice: **discard** vs **defer** messages qualifying during DND
- Campaign cut-off times
- Per-user-timezone delivery scheduling (skip-or-reschedule-next-day)
- TTL for delivery retry duration

### CleverAI / Predictive Features

- **Predictions Agent**: predictive segmentation for conversion/churn/uninstall likelihood, continuously refreshed
- **Recommendations Agent**: in-journey product/content suggestions
- **Journey Builder Agent**: journey construction optimization
- **Path Optimizer Agent**: journey path optimization
- **Lifecycle Agent**: next-best-action across acquisition → activation → retention → cross-sell → win-back
- **Psychographic Segmentation**: ML-driven clustering by inferred likes/interests (beyond behavioral actions)
- **Intent-Based Segments**: ML-bucketed Most/Moderately/Least Likely to convert/churn, with built-in 5% control group

### RFM Analysis (Built-In)

- Recency and Frequency scored 1-5 via percentile ranking on a selected event
- Monetary reported as Average Monetary Value (total spend / users in segment)
- **10 named segments**: Champions, Loyal Users, Potential Loyalists, New Users, Promising, Needing Attention, About to Sleep, At Risk, Cannot Lose Them, Hibernating
- Analysis window configurable (recommended under 512 days)
- Segments are campaign-actionable directly
- Transitions between segments trackable over time

---

## 6. Data Export Options

| Method | Best For | Format | Notes |
|--------|----------|--------|-------|
| **Cursor APIs** (Events/Profiles) | Moderate, scriptable pulls | JSON | Not for full historical bulk export |
| **S3/GCS/Azure Partner Exports** | Large historical backfills | JSON, CSV, XML, Parquet | Scheduled or one-time bulk dumps |
| **Webhooks** | Real-time event streaming | JSON POST | Push campaign interaction events to a URL |
| **BI Connectors** | Warehouse sync | Various | Integration guides available |

**For bulk reads**: Use cursor APIs for targeted pulls (specific events, date ranges). For full historical data, use the S3 export route if available on the account's plan.

---

## 7. Crew M API Strategy

### What to Pull & How

| Data Need | Endpoint | Priority |
|-----------|----------|----------|
| Campaign performance history | `POST /1/message/report.json` with `daily:true` | 🔴 Critical — training data for prediction models |
| Event counts by time | `POST /1/counts/trends.json` | 🔴 Critical — temporal patterns |
| User profiles (sample) | `POST /1/profiles.json` + cursor | 🔴 Critical — feature engineering |
| Top event properties | `POST /1/counts/top.json` | 🟡 Important — property distribution |
| Campaign list | `POST /1/targets/list.json` | 🟡 Important — campaign metadata |
| Individual campaign stats | `POST /1/targets/result.json` | 🟡 Important — per-campaign detail |
| Real-time active users | `POST /1/now.json` | 🟢 Nice-to-have — live dashboard |

### Architecture Pattern

```
CT API → Backend Queue (3 concurrent max)
       → Async Polling Loop (for partial/req_id endpoints)
       → Response Cache (SQLite/Parquet)
       → ML Pipeline reads from cache
       → Frontend reads from backend API, never CT directly
```

### What the API Cannot Give Us (Dashboard-Only)

- IntelliTime bucket assignments per user
- A/B variant-level results breakdown
- DND suppression counts
- Journey canvas/node structure
- Segment definitions/rules
- IntelliChannel per-user scores
- Psychographic segment membership

These would need manual export (screenshots, CSV downloads from dashboard) per Bible Section 19.3.

---

## 8. Key Constraints for Crew M Build

### From CT Platform

1. **3 concurrent API requests max** for analytics endpoints — queue and throttle
2. **Async polling** on count/trend endpoints — build a polling loop, don't assume sync
3. **Cursor TTLs differ**: Events = 4 hours (1h idle), Profiles = 4 days
4. **1-year max on Trends API** — aligns with data governance guardrail
5. **No "list all segments" API** without beta access — use segment definitions from Bible
6. **No journey list API** — journey data must come from manual exports
7. **Message Reports only gives sent/viewed/clicked** — no explicit "delivered" or conversion count

### From Data Governance (CLAUDE.md)

1. **All queries must specify date range; max 1-year window**
2. **No raw data export buttons in the UI** — display only
3. **Audit logging** on all data access (who, when, what)
4. **Secrets in env vars** — CT credentials in `.env.local`
5. **Move data only through the kit** — CT API access through backend, never client-side

### Synthetic Fallback Trigger Conditions

Use synthetic data when:
- CT API credentials not yet configured
- API returns errors or is unreachable
- Data volume insufficient for reliable clustering (< 1000 users)
- Campaign history too sparse for prediction training (< 20 campaigns)

Architecture must abstract data source — real CT and synthetic are interchangeable at the pipeline level.

---

## 9. Quick Reference: CT Concepts → Crew M Features

| CT Concept | How Crew M Uses It |
|------------|-------------------|
| Events + Properties | Feature engineering for user clustering |
| User Profiles + Properties | Demographics and attribute features for personas |
| Segments (Past Behavior) | Audience targeting recommendations |
| Campaign Reports | Training data for conversion prediction models |
| Trends | Temporal pattern discovery, send-time optimization |
| RFM Scores | Input features for persona clustering |
| IntelliChannel | Validation for our channel preference model |
| Funnel Analysis | Validating our funnel-stage predictions |
| A/B Results | Highest-quality training signal for copy/channel models |
| DND/Frequency Caps | Hard constraints on campaign recommendations |

---

## 10. Campaign Setup — Step-by-Step Guide

This section covers the complete process of creating, configuring, testing, and launching a campaign in CleverTap's dashboard.

### 10.1 Campaign Creation Flow

1. Navigate to **Messages > Campaigns** in the left nav
2. Click **+ Campaign**
3. Select a **Messaging Channel** (Push, Email, SMS, WhatsApp, In-App, Web Push, App Inbox, Webhook)
4. The campaign builder opens with five sections:

| Section | What You Configure |
|---------|-------------------|
| **Start Here** | Qualification criteria, conversion goal, service provider |
| **Who** | Target audience (segment, filters, control group) |
| **What** | Message content, A/B variants, personalization |
| **When** | Schedule, delivery preferences, DND, frequency caps |
| **Publish** | Review summary and launch |

### 10.2 Start Here — Qualification & Goals

**Qualification Criteria** — how users enter the campaign:

| Type | Behavior |
|------|----------|
| Past behavior / Custom list | Target based on historical actions or uploaded user lists |
| Live behavior | Real-time trigger when user performs or fails to perform an event |
| External trigger | Campaign delivery triggered via API call (Push, Email, Webhook only) |

**Conversion Goal** (optional but recommended):
- Select a **Conversion Event** (e.g. "Charged", "healthCheckupbooking_confirmed")
- Set a **Conversion Time** window: 1 minute to 5 months (Minutes / Hours / Days / Weeks / Months)
- Conversion counted once per user per campaign

**Service Provider** — select the configured provider for the chosen channel (e.g. which SMS provider, which Email ESP).

### 10.3 Campaign Types

#### By Delivery Type

| Type | Description | When to Use |
|------|-------------|-------------|
| **One Time** | Sends once to qualifying users at a specific time | Announcements, one-off promotions |
| **Recurring** | Repeats daily / every N days / weekly / monthly | Weekly digests, regular nudges |
| **Action (Triggered)** | Fires in real-time when user performs a specific event | Welcome messages, feature usage triggers |
| **Inaction** | Fires when user does NOT perform an expected action within a time window | Cart abandonment, incomplete onboarding |
| **On a Date/Time** | Fires based on a date property on the user profile | Birthday campaigns, renewal reminders |
| **Multiple Date** | Sends on several specified dates/times | Multi-day events, phased rollouts |
| **API (External Trigger)** | Triggered by server-side API call with dynamic payload | Order confirmations, server-side events |

#### By Message Structure

| Type | Description |
|------|-------------|
| **Single Message** | One message to all qualifying users (per-user personalization still works) |
| **A/B Test** | Up to 3 variants tested; winner auto-deployed to remaining audience |
| **Split Delivery** | Percentage-based distribution across variants, no winner selection |
| **Message on User Property** | Up to 50 variants based on user property values (language, tier, etc.) |

### 10.4 Audience Targeting (The "Who" Section)

#### Segment Types Available

**Past Behavior Segments (PBS):** Historical actions, inactions, and user properties combined. Example: "Users who launched the app in the last 30 days AND have not booked a consultation."

**Live User Segments (6 sub-types):**
- User Actions — triggers the moment a user performs a specific event
- Inaction in Time Frame — user does event A but NOT event B within X minutes
- On a Date or Time — segments by date/time property values
- Page Visit — triggers on specific URL visit
- Referrer Entry — segments by referring source
- Page Count — segments by number of pages visited

**Custom List Segments:** Upload CSV (50MB via dashboard, 5GB via API). Two required columns: Type (`g` for CleverTap ID, `i` for Identity) and the Identity value.

**Intent-Based Segments:** ML-predicted likelihood of conversion/churn. Three micro-segments: Most Likely, Moderately Likely, Least Likely. Takes up to 24 hours to generate. Advanced/Cutting Edge plans only.

**System Segments (pre-built):** All Users, Test Users, First-time App Users, Engaged Users (4+ weekly interactions).

#### Filter Rule Builder

Three rule families, combinable with AND/OR logic:

| Rule Family | What It Filters On |
|-------------|-------------------|
| **User Property** | Custom attributes, demographics, geography, technographics, reachability (MSG-push/sms/email/whatsapp), app fields, segment membership |
| **User Behavior** | Event Did / Have Not Done / Combination (any-of OR logic), with count, sum, average operators |
| **User Interest** | Event property values, time of day patterns, day of week — "Predominantly" or "At Least %" threshold |

#### Control Groups

| Type | Scope | Size |
|------|-------|------|
| System Control Group | All campaigns, entire user base | 2–5% (1 per account) |
| Custom Control Group | Selected campaigns, entire user base | 2–5% (up to 10 per account) |
| Campaign Control Group | This campaign's audience only | 2–99% |

#### Targeting Caps

- All qualifying users (with optional safety: "Don't send if segment exceeds X users")
- Send to at most X qualified users total
- Send to at most X qualified users per day (Live Behavior only) with optional lifetime cap
- Minimum: 100 users

Click **Calculate** to preview estimated reach (total users, platform breakdown, device count).

### 10.5 Message Content (The "What" Section)

#### Content Fields by Channel

**Push:** Title, Body, Image (rich push), Deep Link, Custom Key-Value Pairs, Action Buttons

**Email:**
- From (sender name) — mandatory
- Subject line — mandatory
- Preheader (summary text after subject in inbox) — optional
- Plain-text body (fallback for non-HTML clients) — optional
- CC/BCC (up to 20 total, Private Beta) — optional
- Template selection: rich editor, drag-and-drop, or HTML

**SMS:** Message body, URL shortening (max 5 per variant), Template ID (mandatory for India/MSG91), click tracking

**WhatsApp:** Pre-approved template, personalization variables, Quick Reply buttons (up to 3, 128 chars each), CTA buttons, media headers (image/video/document/location)

**In-App:** Template type (header, footer, interstitial, half-interstitial, cover, custom HTML), images/GIFs/videos, action buttons

**Web Push:** Title, body, icon, image, action URL, action buttons

**App Inbox:** Template type (Simple, Carousel, Message with Icon), tags for categories, CTA (link, copy-to-clipboard, open URL, key-value)

#### Personalization

**Inline (@):** Type `@` or `{{}}` in any text field to open the personalization menu. Works in media URLs, deep links, button text.

**Liquid Tags:** Full scripting for dynamic content:

```liquid
{{ Profile.PropertyName | default: "fallback" }}
{{ Event.PropertyName | default: "fallback" }}

{% if Profile.Language == "Hindi" %}
  नमस्ते!
{% else %}
  Hello!
{% endif %}

{% abort %}  ← prevents delivery if condition fails
```

**Linked Content:** Send-time API calls to external sources (weather, product catalogs).

**Catalog Personalization:** Pull product info from uploaded CSV catalogs.

Note: Event properties are only available for live user segments (triggered campaigns). Profile properties work for all segment types.

#### A/B Testing

- Up to **3 variants**
- Minimum recommended audience: 5,000 users (optimal: 10,000+)
- Past Behavior segments: set test % or absolute count; variants distribute equally
- Live segments: set fixed test audience size; system alternates variants
- Winner declared by: clicks (push/SMS) or views (email/WhatsApp). Ties default to Variant A
- Winning variant auto-deploys to remaining audience
- **Split Delivery** alternative: percentage distribution, no winner selection

### 10.6 Scheduling & Delivery (The "When" Section)

#### Schedule Options

**For Past Behavior / Custom List campaigns:**
- Send Now — immediate, account timezone
- Schedule for Later — specific date/time
- Multiple Dates — fires on several dates
- Recurring — Daily (every N days), Weekly, Monthly

**For Live Behavior (Action/Inaction) campaigns:**
- Start: "Now" or specific date/time
- End: "Never" (runs until stopped) or specific date/time
- Delay: configurable wait before delivery (seconds → days)

#### Timezone Delivery

Check **"Timezone"** in delivery preferences. Delivers at the scheduled time in each user's local timezone (requires "Tz" key in user profiles). If the user's timezone has already passed the scheduled time:
- "Drop the campaign" — no message sent
- "Deliver the next day" — queued for tomorrow

#### IntelliTime (Best Time to Send)

Configured at: Settings > Setup > IntelliTime

- Splits day into **12 two-hour buckets**
- Assigns users based on **180 days** of activity history
- Up to 10 IntelliTime configs per account
- **Fallback time** (manually set) for users without enough history — cannot overlap with DND
- Supported on: Email, SMS, Push, WhatsApp, Web Push
- DND overrides IntelliTime — messages discarded, not delayed
- Incompatible with global throttle limits

#### DND (Do Not Disturb)

Check **"Do Not Disturb (DND)"** in delivery preferences. Select inactive days/hours (e.g. 9 PM – 9 AM). Per-day customization supported. "Copy Time To All" applies the same window to every day.

When a message qualifies during DND:
- **Discard** — permanently dropped
- **Send After DND / Delay** — held and delivered when DND ends

#### Frequency Capping (Two Tiers)

**Global** (Settings > Setup > Campaign Limits):
- Max messages per user per channel across all campaigns (e.g. "3 push in 7 days")
- Dwell Time: minimum gap between messages (15 min – 7 days)

**Per-Campaign** (in the When section):
- "Send every time user qualifies" (default)
- "Send with minimum gap of" (5 min – 30 days)

**Recurring engagement limits:** Send each time / Max N sends ever (1–250) / interval-based

Stricter of global vs campaign always wins. Clear the **"Global Campaign Limit"** checkbox in the Who section to exempt a priority campaign.

#### TTL, Cut-off, Throttle

- **TTL (Time to Live):** Relative (duration from send) or Absolute (specific expiry date/time)
- **Cut-off Time:** Prevents delivery after a timestamp; undelivered messages resume at midnight
- **Global Throttle:** Settings > Setup > Campaign Limits — controls delivery rate per interval (e.g. 100K per 15 min)
- **Ad Hoc Throttle:** Per-campaign override in When section (minimum > 100)

### 10.7 Conversion Tracking

Defined in the **Start Here** section:

1. Select a **Conversion Event** (any tracked event)
2. Set a **Conversion Time** (attribution window: 1 minute to 5 months)

**Attribution types tracked:**
- **Click-Through:** User clicked the message then converted
- **View-Through (Influenced):** User was sent the message and converted without clicking
- **Control Group:** Baseline from users who didn't receive the message

Counting: once per user per conversion event. Multi-campaign: if a user converts across multiple active campaigns, each gets credit. Conversion window and event are editable post-campaign.

### 10.8 Testing & QA

#### Test Sends

In the **What** section, click **Preview & Test**:

| Method | How |
|--------|-----|
| Test Profiles | Select from users marked as "Test profile" in the dashboard |
| All Profiles | Select by email, CleverTap ID, or Identity |
| Device Token | Manual entry of Android/iOS device tokens |

Test response window shows: delivery status, errors, Linked Content responses, Liquid Tag errors.

#### Email-Specific Testing

**Inbox Previews** (Email add-on): Preview rendering across email clients and devices. Spam analysis report.

**Seed Testing:** Send to seed list (dummy addresses across ISPs) to measure inbox placement. Seed providers: Validity, Email on Acid, Litmus, InboxMonster. Upload via CSV or API. Send separately from real audience to prevent metric distortion.

#### Validation

- Real-time Liquid Tag syntax checking in the editor
- Campaign summary review screen before publishing
- Estimated reach calculation

### 10.9 Campaign Approval Workflow

Enable at: Settings > Security > Campaign Approval > Toggle ON

| Role | Can Do |
|------|--------|
| Creator | Drafts and submits; cannot publish without approval |
| Approver | Reviews, approves, or rejects with comments |
| Admin | Has approver capabilities by default |

Flow: Creator submits → email notification to approvers → Approver reviews segment/timing/content → Approve or Reject (with comments) → Creator can edit and resubmit if rejected.

If not approved by scheduled send time: campaign expires (must clone and reschedule). Recurring campaigns return to pending status after copy edits.

### 10.10 Post-Launch Monitoring

#### Live Stats by Channel

| Channel | Metrics Available |
|---------|------------------|
| Push | Qualified, Sent, Impressions (SDK 3.5.1+), Clicks, CTR, Conversions (view-through + click-through), Errors |
| Email | Sent, Viewed (opens), Clicks, CTR, Conversions, Soft Bounces (temporary), Hard Bounces (permanent), Subscribe/Unsubscribe |
| SMS | Sent, Delivered, Clicks (shortened URLs), Errors |
| WhatsApp | Sent, Delivered, Read, Clicks, Errors |

#### Analytics Views

- **Message Trend:** Daily/weekly/monthly performance charts
- **Conversion Performance:** Revenue metrics and funnel analysis
- **Users Conversion Funnel:** Drop-offs across Sent → Viewed → Clicked → Converted
- **Split of Clicks:** Per-link click distribution (email)
- **OS/Device Split:** Breakdown by platform and device type
- **Error Reporting:** Stats > Errors tab

#### Campaign Reports (Subscription-Based)

Campaigns page > select campaigns > **"Subscribe to reports"**

- **One-Time Reports:** Snapshot for selected campaigns
- **Recurring Reports:** Daily (previous day) or Weekly (last 7 days)
- Delivery: email or partner export (S3 / GCS / Azure Blob)
- Limits: stats for max 2,500 campaigns; detailed stats for max 2,000

#### Campaign Lifecycle

| Status | Meaning |
|--------|---------|
| Draft | Created but not published |
| Scheduled | Published, waiting for send time |
| Running | Currently delivering |
| Awaiting Next Run | Recurring campaign between runs |
| Stopped | Manually stopped (permanent — cannot pause/resume) |
| Completed | Finished all deliveries |
| Approval Pending | Awaiting approver |
| Rejected | Rejected by approver |

**Operations:** Stop (permanent), Clone (to same or different project, as draft), Archive (remove from active view).

**Message Labels:** Up to 900 labels for categorization, recorded on "Notification Sent" events. Cannot contain: `"`, `,`, `%`, `>`, `<`, `!`.

---

## 11. Channel Setup Requirements

What needs to be configured before each channel can send campaigns.

### Push Notifications

**Dashboard:** Settings > Channels > Mobile push

**Android:** FCM Server Key or Firebase service account JSON (for HTTP v1 API). Optional: Xiaomi (Package Name, App ID, App Key, App Secret), Baidu, Huawei.

**iOS (Auth Key recommended):** Upload .p8 file from Apple Developer portal. Alternative: .p12 push certificate. Bundle ID must match.

**Push Impressions:** Settings > Schema > Events > "Push Impressions" > toggle on "Mobile Push" (requires SDK 3.5.1+).

### Email

**Dashboard:** Settings > Engage > Channels > Email > + Provider

**Supported:** Amazon SES, SendGrid, Postmark, Mandrill, Gmail/Google Apps, Generic SMTP.

**Required fields:** Provider, Nickname (unique), Host, Port, API Key/credentials, Default From Address, Default Reply Address.

**DNS:** SPF, DKIM, DMARC must be configured. Required by Gmail/Yahoo for senders over 5,000 daily emails.

**Provider-specific:**
- Amazon SES: SMTP settings from SES Dashboard; From Address must be verified in SES; configure SNS Topic for bounces
- SendGrid: API Key only (since Dec 2020); configure Event Notification webhook

### SMS

**Dashboard:** Settings > Engage > Channels > SMS > + Add Provider

**18+ providers:** Twilio, Nexmo/Vonage, MSG91, Exotel, Infobip, Kaleyra, Plivo, Route Mobile, Sinch, TextLocal, and more. Generic SMS for any HTTP-capable provider.

**India-specific:** DLT registration required; Template IDs mandatory for MSG91.

**Provider Groups (Failover):** Group up to 10 providers with priority ordering for automatic failover.

### WhatsApp

**Dashboard:** Settings > Channels > WhatsApp. **Paid add-on** — contact sales@clevertap.com.

**Three integration paths:**

| Path | Setup |
|------|-------|
| CleverTap BSP (Direct) | Settings > WhatsApp Direct > + Provider > "CleverTap BSP" > Continue with Facebook. Requires verified Facebook Business Manager, dedicated phone number |
| Third-Party BSP (No-Code) | Supported: Gupshup, Nexmo, ValueFirst, Exotel. Settings > WhatsApp Connect > + Provider |
| Generic WhatsApp API | For any unsupported BSP. Configure HTTP Endpoint, Auth, Max Concurrent Requests (30–1000) |

User opt-in: all profiles opted out by default. Enable with `"MSG-whatsapp": true` profile property.

Template Management: Settings > WhatsApp > Provider > Templates tab. Types: Standard Text, Media (image/video/document/location header), Interactive (CTA + Quick Reply buttons).

### In-App

**No dashboard channel setup required.** SDK-driven (requires CleverTap SDK 3.3.0+). Templates: header, footer, interstitial, half-interstitial, cover, custom HTML.

### Web Push

**Dashboard:** Settings > Channels > Web push. VAPID-based only (legacy FCM tokens must be migrated). Supports Chrome, Firefox, Safari, KaiOS. Soft prompt options: Card Popup, Bell Icon.

### App Inbox

**SDK:** CleverTap SDK 3.4.0+. Templates: Simple Message, Carousel (with/without content), Message with Icon.

**Web Inbox:** Settings > Channels > Web Inbox. Configure: Panel Title, Categories (up to 10), Element ID (mandatory), Display Limit.

---

## 12. Journeys (Multi-Step Campaign Orchestration)

Journeys are separate from single campaigns — they provide multi-step, multi-channel orchestration.

**Creation flow:** Set Up > Define Goals > Define Entry Segment > Define Journey Path > Personalize Content > Publish > Monitor

**Node types:**

| Category | Nodes |
|----------|-------|
| Segment | Action, Inaction, Past Behavior, Date Time, Journey Trigger, Custom List, Page Visit, Referrer Entry, Page Count |
| Engagement | Push, SMS, Email, Webhook, Web Push, Web Pop-up, WhatsApp, Exit Intent, In-App, Web Native Display, Inbox, Facebook, Google, Amazon EventBridge |
| Controller | Force Exit, User Profile Update, IntelliNODE (A/B path testing with up to 7 paths) |

**Sleep Time:** Configurable delays between nodes (minutes, hours, days).

**Key difference from campaigns:** Journeys combine channels in sequence, support reactive branching, and have limited API access (no "list journeys" endpoint).

---

> **Sources**: developer.clevertap.com (API reference), docs.clevertap.com (product docs).
> Cross-referenced with CREW_M_MASTER_CT_BIBLE.md Sections 2-4, 13, 19.
> Last updated: 21 August 2026.
