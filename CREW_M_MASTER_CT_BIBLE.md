# Crew M — Master CleverTap & Campaign Intelligence Bible

> **Purpose**: The single source of truth for building, training, and operating the Crew M campaign intelligence platform. Every segment definition, event name, property, constraint, copy rule, and domain fact lives here. If it's not in this file, it's not confirmed. If it contradicts something elsewhere, this file wins.
>
> **Audience**: The engineering team building the campaign system, and anyone who needs to understand what CleverTap data looks like, what it means, and what rules the system must enforce.
>
> **How to use this**: Sections 1–8 are the **data layer** (what exists, what it's called, how it's structured). Sections 9–13 are the **rules layer** (what the system must enforce). Section 14 is the **data requirements appendix** (what we still need to collect/export to train the models properly).

---

## Table of Contents

- [1. The Business Context](#1-the-business-context)
- [2. CleverTap Core Concepts](#2-clevertap-core-concepts)
- [3. Confirmed Event Schema](#3-confirmed-event-schema)
- [4. Confirmed User Properties](#4-confirmed-user-properties)
- [5. Eligibility & Targeting Definitions](#5-eligibility--targeting-definitions)
- [6. Segment Definitions & Confirmed Counts](#6-segment-definitions--confirmed-counts)
- [7. Funnel Definitions & Confirmed Numbers](#7-funnel-definitions--confirmed-numbers)
- [8. Lifecycle & AARR Segment Framework](#8-lifecycle--aarr-segment-framework)
- [9. The P0/P1 Prioritisation Framework](#9-the-p0p1-prioritisation-framework)
- [10. The Four Adoption Gaps](#10-the-four-adoption-gaps)
- [11. Copy Style Rules (Hard Enforcement)](#11-copy-style-rules-hard-enforcement)
- [12. Narrative Playbook — Lifecycle → Messaging Angle](#12-narrative-playbook--lifecycle--messaging-angle)
- [13. Channel & Timing Constraints](#13-channel--timing-constraints)
- [14. Domain Rules & Product Knowledge](#14-domain-rules--product-knowledge)
- [15. The Four-Way Output Distinction (Non-Negotiable)](#15-the-four-way-output-distinction-non-negotiable)
- [16. The 15 Cohort Opportunities (Reference)](#16-the-15-cohort-opportunities-reference)
- [17. Data Hygiene Flags & Known Issues](#17-data-hygiene-flags--known-issues)
- [18. People & POCs](#18-people--pocs)
- [19. DATA REQUIREMENTS — What the Model Needs](#19-data-requirements--what-the-model-needs)

---

## 1. The Business Context

Plum is a corporate health benefits platform. Customers are **companies** (orgs). End users are **employees** at those companies. The two products driving adoption work:

**Telehealth (TH)**: Video and chat doctor consultations. 24x7, cashless, via app or WhatsApp. Chat is being pushed (faster, cheaper). Repeat usage is real (~5 consults/year once started). The problem is **early-funnel**: 67% never even open the doctor list.

**Health Checkups (HC)**: At-home biomarker screening. One free per year per employee. Priority is **first-time activation**, not repeat usage. The problem is **late-funnel**: friction persists through every stage after listing view. The right messaging angle: "you still haven't used the one already in your plan."

### Partner Segments

| Segment | Accounts Share | Employee Share | Adoption Character |
|---------|---------------|----------------|--------------------|
| **ENT** (Enterprise) | Fewest accounts | ~57% of all employees | Worst adoption — **single biggest lever** on company-wide number |
| **SMB** (Small Business) | ~65% of accounts | ~14% of employees | Judge by accounts-activated, not employees |
| **MM** (Mid-Market) | Middle of both | Middle | Most consistent multi-month improver |
| **EOR** (Employer of Record) | Smallest | Single-digit % | Best per-employee performer (~2x avg), use as proof point |

### Adoption Targets (Confirmed, Unique-User Based)

| Milestone | Target |
|-----------|--------|
| M3 (3 months since org activation) | 15% unique users / eligible employees |
| M6 | 25% |
| M9 | 35% |

These apply identically to both Telehealth and Health Checkups. Measured by **unique users**, not total bookings.

### The Structural Gap

- **74% of orgs** have at least one booking (org-level activation)
- **~10% of employees** have ever booked (employee-level activation)
- **64-point gap**: the "get the company to say yes" problem is solved; the real bottleneck is reaching individual employees inside already-activated companies

---

## 2. CleverTap Core Concepts

| Term | Definition |
|------|------------|
| **User** | One person with a Plum app profile — an employee at a corporate customer |
| **Event** | A timestamped action a user took (e.g. "Consultation Booked") |
| **Event property** | Extra detail on an event (e.g. doctor speciality, city) |
| **User property** | A stable fact about the user (e.g. partner_type, plan_tier) |
| **Segment** | A saved filter — a group of users sharing a behaviour or property |
| **Cohort** | A segment built to track a group's behaviour over time |
| **Campaign** | A single message, sent once, to a segment — no branching |
| **Journey** | A multi-step, branching flow reacting to what a user does or doesn't do |
| **Control group** | A held-out slice (5% flat, industry standard) that gets no message, to prove causal lift |
| **RFM** | CleverTap's Recency/Frequency/Monetary scoring model |
| **DND** | Do Not Disturb — org-level flag blocking all direct-to-employee messaging |

**One-line mental model**: Events tell you what happened. User properties tell you who it happened to. Segments group people by both. Campaigns talk to a segment once. Journeys keep talking based on how they respond.

### Campaigns vs Journeys

- **Campaign**: one message, one moment. Fast to build. Broadcast-style. E.g. "Health Checkup Week starts tomorrow."
- **Journey**: outcome needs more than one nudge. Next nudge depends on prior response. Combines channels in sequence (push → WhatsApp if unopened → email if still unopened). Building a habit over time.
- **Adoption growth (12% → 35%) is fundamentally Journey territory**, with Campaigns as supporting one-off moments (open enrolment, seasonal weeks).

### Segment Builder Mechanics

Three rule families in a Past Behaviour segment:

- **USER PROPERTY** family (User property, Demographics, Geography, Technographics, Reachability, App Fields, Segments, Subscription Groups) — static facts about who someone IS. Home of partner_type, org ID, plan status, DND flag.
- **USER BEHAVIOR** family (Event Did / Event Have Not Done / Event Combination Did Any Of) — actions taken. Home of booking events and app-install/launch events.
- **USER INTERESTS** family (Event property, Time of day, Day of week) — context of when/how people act; relevant for send-time optimisation.

Important distinctions:
- **"App Fields"** segments by app version/OS — does NOT tell you whether someone has the app. Whether someone has the app is an EVENT (`App Installed` / `App Launched`), not a property.
- **"Segments" as a rule type** lets a new segment include/exclude an already-saved segment — build one clean base "eligible" segment, then layer conditions on top.
- **Reachability panel**: ALWAYS check per-channel reachable counts on the REAL filtered segment before treating it as campaign-ready.

### Naming Convention

All segments, campaigns, and journeys: `[TeamCode]_[Objective]_[PartnerType]_[LifecycleStage]`

Example: `HW_Adoption_SMB_ViewedNoBook`

---

## 3. Confirmed Event Schema

> **Source**: Exported CleverTap CSVs (~950 events, ~330 properties), manually verified. These are the REAL event names. Use exactly as written — character-for-character.

### 3.1 Telehealth Funnel Events (in order)

**Entry / Awareness:**
```
nativeDisplay_telehealth_card
telehealth_entry_point_clicked
EmployeeMobileApp_Telehealth_Homepage_Viewed
```

**Consider / Browse:**
```
EmployeeMobileApp_Telehealth_Care_Clicked
ConsultNow_Selected
DoctorList_Viewed
Doctor_Selected
Doctor_Profile_Viewed
```

**Book:**
```
SlotScreen_Viewed
ConsultationInputDetails_Viewed
BookAppointment_Clicked
AppointmentCreated
AppointmentSuccessful_Viewed    ← CANONICAL "booked" event (CONFIRMED)
```

**Complete:**
```
telehealth_doctor_joined
EmployeeMobileApp_Telehealth_CallLog
```

**Doctor-matching sub-funnel:**
```
telehealth_findDoctor_entryInitiated
assessmentComplete
recommendationAccepted
```

> **RESOLVED**: `EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed` is the official, confirmed Telehealth "booked" event. Use this one everywhere. `AppointmentCreated` is NOT the canonical signal.

### 3.2 Health Checkup Funnel Events (in order)

**Entry / Browse:**
```
healthCheckuphomepage_viewed
healthCheckuplisting_viewed
serviceability_checked
skuList_viewed
```

**Cart:**
```
item_added
member_selected
slot_selected
savedAddress_selected
```

**Checkout / Payment:**
```
payment_initiated
paymentGateway_opened
payment_processing
paymentGateway_success
```

**Conversion:**
```
healthCheckupbooking_confirmed    ← CANONICAL "booked" event (CONFIRMED)
```

**Post-Booking:**
```
healthCheckupreport_viewed        ← strong completion signal
reportDownload_clicked
```

**Cross-Product Bridge:**
```
healthCheckuptelehealthBooking_done    ← HC-to-TH cross-sell signal (LIVE, not hypothetical)
```

### 3.3 App Status Events (System Events)

```
App Installed
App Launched                          ← best MAU/engagement proxy, heavily used
App Uninstalled                       ← showed zero volume — flag for sanity check
```

### 3.4 AARR Funnel Events

**Activation events (any of these = "activated"):**
```
cultfitoffer_explored
healthCheckuplisting_viewed
Telehealth_DoctorList_Viewed
perks_offer_unlocked
```

**Revenue events:**
```
superTopUp_purchased
topUp_purchased
oPD_purchased
mAternity_purchased
```

### 3.5 HRA (Health Risk Assessment) Events

```
hra_entry_viewed
hra_started
hra_question_answered
hra_completed
hra_score_viewed
hra_goals_saved
hra_recommendation_viewed
hra_recommendation_clicked
```

**Derived HRA states** (for targeting):
- Never started: no `hra_started`
- Started, dropped off: `hra_started` but no `hra_completed`
- Completed, no goal: `hra_completed` but no `hra_goals_saved`
- Completed + goal, no action: `hra_goals_saved` but no `hra_recommendation_clicked`
- High-risk, no action 30d: high risk score + no follow-up action in 30 days

---

## 4. Confirmed User Properties

### 4.1 Core Targeting Properties

| Property | Type | Use |
|----------|------|-----|
| `is_in_DND_CT` | Boolean | DND flag — full-org-level, set via dedicated CT journey |
| `warehouse_production_organisationId` | String | **Canonical** org ID (most-used variant) |
| `warehouse_production_organisationStatus` | String | Org active status — must be `ACTIVE` |
| `warehouse_production_isTestOrganisation` | Boolean | Test org exclusion — must be `!= true` |
| `warehouse_production_telehealthMembershipCreatedAtTimestamp` | Timestamp | TH eligibility — renews annually |
| `warehouse_production_plumHealthCheckupMembershipCreatedAtTimestamp` | Timestamp | HC eligibility — renews annually |
| `wallet_expiry_days_left` | Number | Countdown for urgency messaging |
| `is_dependent` / `has_dependents` | Boolean | Separates primary employee from family |
| `warehouse_production_admin` | Boolean | Flags HR/admin users (separately targetable) |
| `gmcMembershipCreatedAtTimestamp` | Timestamp | Used for M0 new-user identification |
| `inviteCreatedAt` | Timestamp | Used alongside GMC timestamp for new-user identification |

### 4.2 AM (Account Manager) Contact Properties

```
SMB_AMName
SMB_AMEmail
SMB_AMPhone
SMB_AMWA
SMB_RenewalDate
SMB_DaysToRenewal
SMB_ExpiringPolicy
```

### 4.3 Post-Checkup Health Risk Properties

```
dimension_score_cardiometabolic
dimension_score_mentalHealth
dimension_score_msk
dimension_score_nutrition
dimension_score_physicalActivity
dimension_score_sleep
dimension_score_substance
overall_score
hra_completed
```

> These enable a future cross-sell cohort ("high risk score, never booked a follow-up consult") — not immediate priority.

### 4.4 Properties Explicitly Ruled Out

| Property | Status | Reason |
|----------|--------|--------|
| `wallet_coverage_hc` | **RULED OUT** | Not a correct HC eligibility indicator — confirmed by direct instruction |

---

## 5. Eligibility & Targeting Definitions

### 5.1 Base Eligibility (applies to EVERY segment)

**An eligible user** = ALL of:
1. `organisationStatus = ACTIVE`
2. `isTestOrganisation != true`
3. The relevant membership-created timestamp **exists and falls within the last 365 days**:
   - TH: `warehouse_production_telehealthMembershipCreatedAtTimestamp`
   - HC: `warehouse_production_plumHealthCheckupMembershipCreatedAtTimestamp`

Two confirmed facts make this reliable:
- The timestamp **renews annually** — correctly captures anyone in an active benefit year
- TH and HC have **separate** membership properties — genuinely per-product check

### 5.2 The DND Mechanism

- Applied at **full-org level**, unconditionally, via a user-property flag
- Set via a dedicated CT journey: Past Behaviour entry segment matching one specific org ID → controller node sets `is_in_DND_CT = true` → force-exit
- The journey ONLY sets the flag — other campaigns must independently check `is_in_DND_CT != true`
- Each DND org appears to have its own journey (hardcoded org ID), not one master list
- **Workaround for DND orgs**: the AM/HR "utility messaging exception" route — HR-admin users ARE separately targetable via `warehouse_production_admin`

---

## 6. Segment Definitions & Confirmed Counts

> **Source**: All 8 segments built in CleverTap, confirmed, delivered as `Segment_Reference_TH_HC.xlsx`. Counts as of July 2026.

| # | Segment | Users | Push | Email | SMS | WhatsApp |
|---|---------|-------|------|-------|-----|----------|
| 1 | Base: Eligible & Real (org active + not test) | 956,050 | 23% | 80% | 90% | 80% |
| 2 | No App (no install signal, 365d) | 739,126 | 11% | 77% | 87% | 74% |
| 3 | HC Eligible, Never Booked | 75,272 | 40% | 85% | 98% | 98% |
| 4 | TH Eligible, Never Booked | 173,373 | 36% | 87% | 97% | 97% |
| 5 | P0 Dark on BOTH (AND, DND=false) | 57,336 | 38% | 85% | 98% | 98% |
| 6 | P0 Dark on EITHER (OR, DND=false) | 70,129 | 43% | 86% | 98% | 98% |
| 7 | P1 Dark on BOTH (AND, DND=true) | 13,221 | 35% | 97% | 98% | 98% |
| 8 | P1 Dark on EITHER (OR, DND=true) | 16,008 | 40% | 98% | 99% | 99% |

### Key Observations for Model Training

- **No App segment is 77% of eligible users** (739K of 956K) — this is the single largest barrier
- **WhatsApp/SMS reachability is 97-98%** across most segments — highest-reach channels
- **Push reachability is only 11-43%** — heavily dependent on app install
- The AND vs OR logic difference on Dark segments: AND = dark on both TH and HC; OR = dark on either

### Mistakes Made Building These (Bake Into Validation)

1. **Wrong exclusion event**: `healthCheckuptelehealthBooking_done` (narrow HC-to-TH bridge event) was accidentally used instead of `AppointmentSuccessful_Viewed` for TH exclusion — silently overcounts "never booked"
2. **Blank comparison value**: `is_in_DND_CT not equals [blank]` produced 3.8M+ (absurd, near-whole-database) — always validate comparison values are actually set
3. **Diagnostic rule**: if AND-logic returns MORE users than OR-logic on the same conditions, something is mathematically wrong — trace it before reporting

---

## 7. Funnel Definitions & Confirmed Numbers

> **Source**: All 10 funnels pulled in CleverTap, 120-day window, filtered to active + not-test orgs. Delivered as `Funnel_Reference_TH_HC.xlsx`.

### 7.1 Telehealth Funnels

**Master Funnel:**

| Stage | Event | Users | Conversion |
|-------|-------|-------|------------|
| Homepage | `Homepage_Viewed` | 126,680 | — |
| Doctor List | `DoctorList_Viewed` | 41,461 | 32.73% |
| Slot Screen | `SlotScreen_Viewed` | 22,789 | 17.99% |
| Book Click | `BookAppointment_Clicked` | 16,818 | 13.28% |
| Success | `AppointmentSuccessful_Viewed` | 16,167 | 12.76% |

**Awareness Funnel:** Card (227,836) → Click (98,301, 43.15%) → Homepage (96,917, 42.54%)

**Doctor-Matching Tool:** Entry (18,751) → Assessment (8,259, 44.05%) → Recommendation (4,324, 23.06%)

**Last-Mile Funnel:** SlotScreen (24,952) → SlotNext (21,485, 86.10%) → ConsultInput (14,652, 58.72%) → BookClick (13,005, 52.12%)

**Payment:** Opened (626) → Success (368, 58.79%)

### 7.2 Health Checkup Funnels

**Master Funnel:**

| Stage | Event | Users | Conversion |
|-------|-------|-------|------------|
| Homepage | `healthCheckuphomepage_viewed` | 82,838 | — |
| Listing | `healthCheckuplisting_viewed` | 46,974 | 56.71% |
| Item Added | `item_added` | 12,328 | 14.88% |
| Slot Selected | `slot_selected` | 6,787 | 8.19% |
| Confirmed | `healthCheckupbooking_confirmed` | 5,085 | 6.14% |

**Serviceability:** Listing (54,587) → Checked (25,961, 47.56%) → Failed (794, 1.45%)

**Payment Success:** Initiated (8,632) → Opened (1,731, 20.05%) → Success (1,431, 16.58%)

**Post-Booking:** Confirmed (13,845) → Report Viewed (9,035, 65.26%) → Downloaded (8,226, 59.41%)

**Cross-Sell Bridge:** Report Viewed (12,275) → TH Booking Done (1,758, 14.32%)

### 7.3 The Key Qualitative Insight

**TH problem is EARLY**: 67% never open the doctor list. Fix = early-funnel relevance/routing.

**HC problem is LATE**: friction persists at every stage after listing. Fix = friction removal at each subsequent step.

Different products need different model features and different intervention strategies.

---

## 8. Lifecycle & AARR Segment Framework

### 8.1 AARR Funnel Definitions

**M0 NEW APP users:**
- `gmcMembershipCreatedAtTimestamp` 30-60 days ago
- AND `inviteCreatedAt` 30-60 days ago
- AND `App Launched` in last 60 days

**Activations** (any of):
- `cultfitoffer_explored`
- `healthCheckuplisting_viewed`
- `Telehealth_DoctorList_Viewed`
- `perks_offer_unlocked`

**Revenue** (any of):
- `superTopUp_purchased`, `topUp_purchased`, `oPD_purchased`, `mAternity_purchased`

### 8.2 Lifecycle Segments

**Unacquired** (NOT done `App Launched` in last 180 days + membership exists in last 365 days):
- Fresh: 30-60 days since membership
- Lapsing: 60-90 days
- Dormant: 90-365 days

**Unactivated** (downloaded app, NOT done any activation event, hard cutoff 90 days):
- Fresh: last 7 days
- Lapsing: 7-14 days
- Dormant: 14-90 days

**Retained** (done at least 1 activation event):
- Fresh: last 30 days
- Lapsing: 30-60 days
- Dormant: 60-90 days

### 8.3 Cohort Dimension Checklist (Confirmed by Manager)

Every cohort must be defined across ALL FOUR axes:

1. **Benefit type**: Telehealth-only / Health-Checkup-only / Both
2. **App-downloaded status**: Yes / No ← its own axis, never conflated with usage
3. **Benefit-used status**: Yes / No
4. **Lifecycle month**: M3 / M6 / M9

---

## 9. The P0/P1 Prioritisation Framework

> Confirmed directly by manager (Prayat). Supersedes any informal prioritisation.

Let X = Eligible users. Y = DND-locked users. Z = Already-activated users.

| Priority | Formula | Who | Action |
|----------|---------|-----|--------|
| **P0** | X − Y − Z | Reachable AND not yet converted | Target immediately — default first priority |
| **P1** | DND-locked AND not yet activated | Harder to reach | Needs AM/HR "utility messaging exception" route first |
| **Out of scope** | Already-activated (Z) | Already converted | Exception: TH repeat-usage/habit-loop targeting only |

---

## 10. The Four Adoption Gaps

> **Diagnose BEFORE messaging.** The fix is different for each gap. A generic "use your benefit" push does not move a trust problem.

| Gap | Symptom | Fix | Dominant Segment |
|-----|---------|-----|-----------------|
| **Awareness** | Doesn't know benefit exists | Information + visibility | SMB, EOR |
| **Friction** | Knows, but booking feels like effort | Reduce steps, deep links | HC late-funnel |
| **Trust** | Unfamiliar with virtual care | Testimonials, profiles, security | ENT at scale |
| **Trigger** | Knows and trusts, nothing nudges action | Urgency, seasonal, wallet expiry | MM |

---

## 11. Copy Style Rules (Hard Enforcement)

> These are NOT guidelines. They are **hard rules** enforced in copy scoring. Violations are flagged and penalised.

| # | Rule | Bad Example | Good Example |
|---|------|-------------|--------------|
| 1 | **No "not X" negation contrasts.** State the positive and stop. | "Recommendations built around your results — not generic advice." | "Recommendations built specifically from your results." |
| 2 | **No ", so you know X" tails.** Land benefit in main clause. | "A score across 7 key health areas, so you know exactly what to focus on." | "Your health, scored across 7 key areas — with a clear place to start." |
| 3 | **No em dashes.** Rewrite as two sentences or restructure. | — | Use full stops or commas |
| 4 | **Colon definitions must define what the thing IS.** | Not where it lives or how long it takes | What it fundamentally is |
| 5 | **Never invent stats.** No fabricated percentages. | "87% of users saw improvement" (made up) | Phrase qualitatively if no real number exists |
| 6 | **Never surface scoring formulas/weights/percentiles** to end users. | — | Keep internal |
| 7 | **Skip acronyms** (HRA, GMC, GTL) in first-touch consumer copy unless defined. | "Complete your HRA today" | "Get your Health Score today" |
| 8 | **Lead with reader benefit**, not mechanism. | "Complete your Health Risk Assessment" | "Get your Health Score in 5 minutes" |
| 9 | **AM emails: shorter and more direct** than consumer copy. Professional tone. | — | — |
| 10 | **When editing human drafts: edit minimally.** Fix factual/compliance/banned constructions. Don't rewrite wholesale. | — | — |

---

## 12. Narrative Playbook — Lifecycle → Messaging Angle

| Segment State | Messaging Angle | Key Principle |
|---------------|----------------|---------------|
| Unacquired — Fresh | Urgency + first action ("get started in the next 30 days") | Time pressure on unused benefit |
| Unacquired — Lapsing/Dormant | Re-acquisition, remove friction, remind of what's theirs | Loss framing beats gain framing |
| Unactivated — Fresh | Remove-friction framing, one clear first step | Reduce steps, don't add motivation |
| Unactivated — Lapsing/Dormant | Re-surface single highest-converting hook | Don't overwhelm with options |
| Retained — Fresh/Lapsing | Habit/streak framing, build on existing engagement | Social proof scales with company size |
| Retained — Dormant | Re-engagement without guilt-tripping | Never shame the lapse |

### HRA-Specific Messaging Angles

| HRA State | Angle |
|-----------|-------|
| Never started | Lead with speed + personalisation ("5 minutes, tailored to you") |
| Dropped off | Low-friction reminder, emphasise how little is left |
| Completed, no goal | Nudge toward goal-selection screen |
| Completed + goal, no action | Recommendation-specific push matched to their goal |
| High-risk, no action 30d | Care-forward urgency — **NEVER fear-based** |

### Messaging Logic Principles (Bake Into Model)

- **Loss framing beats gain framing** for a benefit already owned — "don't lose this free consult" > "gain a free consult"
- **Social proof scales with company size** — "used by 2,400 of your colleagues" lands for ENT, means nothing to SMB
- **Reduce steps, don't just add motivation** for friction-gap cohorts — a one-tap deep link outperforms any amount of persuasive copy
- **First use and repeat use are different problems** — treat as two distinct journeys

---

## 13. Channel & Timing Constraints

### Channel Reachability (from confirmed segments)

| Channel | Reachability Range | Notes |
|---------|--------------------|-------|
| WhatsApp | 74-99% | Highest reach. Primary channel for most segments |
| SMS | 87-99% | Second highest. Use for DND workarounds |
| Email | 77-98% | Good reach but lower engagement |
| Push | 11-43% | Heavily app-dependent. Only 23% of base eligible |

### Channel Selection Logic

1. **No-app users** (739K): WhatsApp/SMS/Email ONLY — push is unreachable
2. **DND users**: AM/HR utility messaging route only — direct channels blocked
3. **P0 reachable users**: WhatsApp first, push second (if app installed), email third
4. **Sequence pattern for Journeys**: Push → WhatsApp (if unopened 48h) → Email (if still unopened)

### Timing Patterns

- **8-11 PM peak activity** for many segments
- **AM emails are shorter and more direct** — different from consumer copy
- **Seasonal relevance**: monsoon/dengue = natural TH push; year-end = HC wallet-expiry push
- **`wallet_expiry_days_left`** enables countdown urgency for HC

### Standing Constraints

- **5% control group** on every journey — flat, no exceptions (mentor-confirmed industry standard)
- **Frequency caps** on final reminder nodes — don't overwhelm
- **Coordinate with Oshin and Santu** before launching any new campaign — no uncoordinated messaging to the same users
- **Stop, don't delete** retired campaigns — preserve historical data for benchmarking
- **Never stack uncoordinated pushes** across TH and HC on the same user in a short window

---

## 14. Domain Rules & Product Knowledge

### Telehealth Specifics

- Video AND chat consultations; chat being pushed (faster, cheaper for Plum)
- 24x7, cashless, bookable via app or WhatsApp
- Repeat usage pattern: ~5 consults/year once someone starts
- Adoption metric: **unique users**, not total bookings
- Canonical booking event: `EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed`
- Main problem: early-funnel (67% never open doctor list)
- Doctor-matching sub-funnel exists and is live
- Payment is a very small funnel (626 users) — mostly cashless flow

### Health Checkup Specifics

- At-home biomarker screening, one free per year
- Priority: first-time activation of the free checkup, NOT repeat usage
- Canonical booking event: `healthCheckupbooking_confirmed`
- Main problem: late-funnel friction at every stage after listing
- `wallet_expiry_days_left` powers urgency/countdown messaging
- A paid, pay-per-use advanced tier exists — explicitly SECONDARY right now
- Never build "book your checkup again" messaging — right angle is "use the one in your plan"
- Post-booking engagement (report viewed → downloaded) is strong (65% → 59%)
- HC-to-TH cross-sell bridge event is LIVE and working (14.32% conversion)

### Adoption Compounds With Tenure

In every segment: M3 → M6 → M9 all trend upward. The product mechanism works. The gap to target is a **speed-to-maturity and penetration problem**, not a "does this work" problem.

---

## 15. The Four-Way Output Distinction (Non-Negotiable)

> Every output the system produces must be clearly labelled as one of:

| Label | Meaning | Example | Visual Treatment |
|-------|---------|---------|-----------------|
| **OBSERVED** | What actually happened historically | "Segment A had 8.2% conversion across 14 campaigns" | Solid badge, blue |
| **PREDICTED** | What the model expects to happen | "Estimated 7.5% conversion for Segment A" | Dashed badge, amber |
| **RECOMMENDED** | What the system suggests doing | "Prioritise Segment A over C" | Arrow badge, green |
| **GENERATED** | What the LLM created | "Here are three copy variants" | Sparkle badge, purple |

**Rules:**
- Never present a prediction as an observation
- Never present generated copy as a data-backed recommendation
- Never let the LLM invent conversion rates (that's the model's job)
- If the model can't make a reliable prediction, say so with low confidence — don't fabricate

---

## 16. The 15 Cohort Opportunities (Reference)

> Source: 21-page Cohort Opportunity Report. These are sized, sourced, and prioritised.

| # | Cohort | Size | Type | Priority |
|---|--------|------|------|----------|
| 1 | TH Eligible Never Booked | 173,373 | Activation | P0 |
| 2 | Enterprise Wide But Shallow | ~145,347 | Structural | Foundational |
| 3 | HC Eligible Never Booked | 75,272 | Activation | P0 |
| 4 | No App Installed | 739,126 | Acquisition gate | P0 |
| 5 | TH Drop Homepage-to-DoctorList | 85,219 | Funnel friction | P1 |
| 6 | HC Drop Listing-to-Cart | 34,646 | Funnel friction (steepest) | P1 |
| 7 | Mature Dark Orgs (SMB/MM only) | ~2,200 employees | Account-level urgent | P1 |
| 8 | DND and Dark (P1) | 13,221 (AND) / 16,008 (OR) | DND unlock | P1 |
| 9 | HC Report Viewed No TH Follow-up | 10,517 | Warm cross-sell | P2 |
| 10 | TH Doctor-Match Tool Abandoners | 14,427 | Funnel friction / high intent | P2 |
| 11 | HC Booked Report Never Viewed | 4,810 | Retention / value-realisation | P2 |
| 12 | HC Payment Friction | 7,163 | Product/engineering fix | P2 |
| 13 | TH Repeat-Use Lapsed | ~8,000 (estimate) | Segment not yet built | P2 |
| 14 | HC Serviceability Failed | 794 | Ops/expansion signal | P3 |
| 15 | TH Payment Abandoners | 258 | Tiny but highest-intent | P3 |

**Org-type composition model** (for generic "never booked" cohorts): ~58.5% ENT, ~23.5% MM, ~13.9% SMB, ~4.1% EOR. Label as MODELED, not measured. Exception: DND skews heavily Enterprise — describe directionally, don't use the generic formula.

**Recommended lead cohorts**: Start with 1 and 3 (largest, cleanest, zero-dependency). Pursue 8's DND unlock in parallel (compounds everything once resolved). Use 7 as fastest proof point.

---

## 17. Data Hygiene Flags & Known Issues

### Active Issues (Do Not Block On, But Track)

1. **Org-ID property variants**: `warehouse_production_organisationId`, `organisationId`, `organization_id`, `org_id`, `organization` — not confirmed whether they all resolve identically. Default to `warehouse_production_organisationId`.

2. **camelCase/snake_case duplication**: Every key event carries BOTH `organisationId` AND `organisation_id` — likely from two tracking implementations. Filtering on only one variant risks missing users tracked under the other.

3. **`App Uninstalled` zero volume**: showed zero events in export — either genuinely no uninstalls tracked, or event not firing. Don't assume either way.

4. **Enterprise M9 "target met" rate dropped to 0%**: in Jun-Jul dataset — could be genuine collapse or broken target calculation. High priority to verify before sizing ENT campaigns.

5. **Aggregate "Targets Met" jump**: ~8.75x jump in one month with no corresponding breakdown — suggests definition change or data-pull error. Don't use until confirmed.

### Segment-Building Mistakes to Validate Against

- A `Have Not Done` condition using a plausible-but-wrong event name (e.g. using the HC-to-TH bridge event instead of the actual TH booking event)
- A comparison value left blank on a property condition (produces absurdly inflated counts)
- AND-logic returning MORE users than OR-logic on the same conditions (mathematically impossible — means an error)

---

## 18. People & POCs

| Name | Role | Go to them for |
|------|------|----------------|
| **Nihit** | Team buddy | TH/HC product context, roadmap, partner doctors, pricing |
| **Vijender** | Data POC | Metabase data flow, table locations, access requests |
| **Sathvik** | Metabase definitions | Whether definitions match adoption sheets, recent changes |
| **Prayat** | Manager | Direction, priorities, target validation, deliverable review |
| **Oshin** | PMM on product team | Cross-team comms gatekeeper — MUST co-design campaigns |
| **Santu** | Personal campaigns team | Coordination to avoid overlapping outreach |
| **Aditya** | External mentor | PMM strategy, funnel/OKR approach (not a Plum employee) |

---

## 19. DATA REQUIREMENTS — What the Model Needs

> This section specifies every data export, sheet, screenshot, and raw feed the Crew M platform needs to train its models properly. Organised by what we HAVE vs what we NEED.

### 19.1 What We Already Have (Confirmed Available)

| Data | Source | Status | Used For |
|------|--------|--------|----------|
| CleverTap event schema (~950 events, ~330 properties) | CT CSV exports | ✅ Analysed | Feature engineering, funnel definitions |
| 8 confirmed segments with reachability | CT segment builder | ✅ Built & verified | Targeting, reachability constraints |
| 10 confirmed funnels (120-day window) | CT funnel pulls | ✅ Delivered | Funnel-stage conversion rates, drop-off sizing |
| Org-level TH + HC adoption CSVs | Adoption sheets | ✅ In sandbox | Segment-level adoption rates, M3/M6/M9 benchmarks |
| DND org list (~43 names) | Manual list | ✅ Cross-referenced | DND cohort sizing |
| Cohort Opportunity Report (15 cohorts) | Synthesised | ✅ Delivered | Cohort definitions, sizes, priorities |
| HRA event schema | CT exports | ✅ Mapped | HRA funnel definitions |
| Lifecycle segment definitions (AARR) | Operational playbook | ✅ Documented | Lifecycle stage targeting |

### 19.2 What We NEED — CleverTap Exports

> **Priority order**: items marked 🔴 are blocking for core model training. 🟡 are needed for full feature coverage. 🟢 are nice-to-have for enrichment.

#### 🔴 CRITICAL — Campaign History Export

**What**: Full campaign performance history from CleverTap — every campaign and journey that has been sent, with:
- Campaign/journey ID and name
- Send date/time
- Target segment (which segment was used)
- Channel used (push/email/WhatsApp/SMS/in-app)
- Total sent count
- Delivered count
- Opened/viewed count
- Clicked count
- Converted count (goal event triggered)
- Control group size and conversion
- Copy/message content (the actual text sent)
- A/B variant details if applicable

**How to get it**: CleverTap → Analytics → Campaigns → Export (CSV). Also: Journeys → each journey → Export Stats. We need BOTH campaign-level and journey-level exports.

**Why**: This is the training data for the prediction models. Without campaign-level performance data tied to segments, the XGBoost/LightGBM models have nothing to learn from. This is the single most critical missing dataset.

#### 🔴 CRITICAL — User-Level Event Export (Sample)

**What**: A user-level event log for a representative sample (~50K users) covering the last 120-180 days:
- User ID (anonymised is fine)
- Every event they triggered (with timestamp)
- Event properties for each event
- Key user properties (partner_type, org_id, DND status, membership timestamps)

**How to get it**: CleverTap → Analytics → Events → Export (CSV). Or via CleverTap API: `GET /1/profiles.json` + `GET /1/events.json`. Alternatively: Metabase SQL export if the events are mirrored there.

**Why**: This is how we build the feature engineering pipeline — recency, frequency, intensity scores, channel preference vectors, intent signals, temporal behaviour patterns. Without user-level event sequences, we can't cluster for persona discovery or train per-user prediction models.

#### 🔴 CRITICAL — User Profile Export (Full)

**What**: All user profiles with their properties:
- All properties listed in Section 4 of this document
- Partner type, org ID, org status, test-org flag
- Membership timestamps (TH and HC)
- DND status
- App install/launch recency
- Wallet expiry days
- Dependent status
- HRA completion status and scores

**How to get it**: CleverTap → Segments → select the Base Eligible segment → Download Users (CSV). Or via API: `GET /1/profiles.json` with segment filter.

**Why**: This is the denominator for everything — who exists, what properties they have, which segments they fall into. Combined with the event export, this gives us the full feature matrix for clustering and prediction.

#### 🟡 IMPORTANT — Existing Journey Configurations

**What**: Screenshots or exports of every currently live/paused/completed journey in CleverTap showing:
- Journey name and ID
- Entry criteria (which segment)
- Node structure (what messages, waits, conditions, splits)
- Goal event
- Control group percentage
- Channel used at each node
- Message content at each node
- Current state (running/paused/completed/stopped)

**How to get it**: CleverTap → Journeys → click each journey → screenshot the canvas + export stats. There are reportedly ~20 live campaigns/journeys.

**Why**: This teaches the model what has been tried, what combinations of segment × channel × message × timing have been deployed, and what the outcomes were. It's also needed for the "don't duplicate existing journeys" checklist.

#### 🟡 IMPORTANT — A/B Test Results

**What**: Any A/B test that has been run in CleverTap with:
- Test hypothesis
- Variant A and B content/channel/timing
- Sample sizes per variant
- Conversion rates per variant
- Statistical significance (if reported by CT)

**How to get it**: CleverTap → Campaigns → filter by A/B → export results.

**Why**: A/B results are the highest-quality training signal for the copy scoring model and the channel preference model. They tell us what actually beat what, not just what was tried.

#### 🟡 IMPORTANT — Segment-Level Engagement Metrics (Monthly)

**What**: For each of the 8 confirmed segments (and ideally any other active segments), monthly:
- Segment size
- Messages sent per channel
- Open rates per channel
- Click rates per channel
- Conversion rates
- Unsubscribe/opt-out rates

**How to get it**: CleverTap → Analytics → Engagement → filter by segment → export monthly.

**Why**: This is how we build the channel preference model per segment and detect fatigue patterns over time.

#### 🟡 IMPORTANT — Push/Email/WhatsApp Delivery Logs

**What**: Message-level delivery data showing:
- Message ID
- User ID
- Channel
- Timestamp sent
- Timestamp delivered
- Timestamp opened (if applicable)
- Timestamp clicked (if applicable)
- Bounce/failure reason (if applicable)

**How to get it**: CleverTap → Analytics → Messages → Export. Or via CT API webhooks if configured.

**Why**: This powers the P(Delivery) → P(Open) → P(Click) → P(Conversion) multi-stage prediction funnel. Without delivery-level data, we can only predict aggregate rates, not per-user probabilities.

#### 🟢 NICE-TO-HAVE — Historical Adoption Sheets (Monthly Snapshots)

**What**: The org-level TH and HC adoption sheets for each month going back 6-12 months (not just the current snapshot).

**How to get it**: Ask Vijender/Sathvik — these may exist as historical Metabase snapshots or archived Google Sheets.

**Why**: Shows adoption velocity curves over time, which lets us validate whether the M3→M6→M9 compounding pattern holds month-over-month, and calibrate the tenure-based prediction model.

#### 🟢 NICE-TO-HAVE — Metabase Dashboard Definitions

**What**: Screenshots or SQL queries behind key Metabase dashboards showing:
- Which tables/views are used
- How metrics are calculated
- Known discrepancies vs CT data

**How to get it**: Metabase → each dashboard → click each card → View SQL.

**Why**: Validates that our feature definitions match the operational definitions already in use. Catches any discrepancy between CT-side and Metabase-side metrics early.

#### 🟢 NICE-TO-HAVE — Communication Samples

**What**: Actual message content (WhatsApp messages, email bodies, push notification text, SMS text) from recent campaigns — at least 20-30 real examples spanning:
- Different channels
- Different partner types
- Different lifecycle stages
- Both TH and HC
- Both successful and underperforming campaigns

**How to get it**: CleverTap → Campaigns → click each → copy the message content. Or: ask Oshin/Santu for their campaign library.

**Why**: This is the training corpus for the copy scoring model. The style rules in Section 11 define what to penalise, but we need real examples to calibrate what "good" and "bad" actually look like in Plum's voice.

### 19.3 What We NEED — Screenshots & Visual References

| What | Where to Get It | Why |
|------|-----------------|-----|
| Screenshot of the CleverTap segment builder with one of our 8 segments open | CT → Segments → click a segment | Validates segment logic visually, catches rule-ordering issues |
| Screenshot of a live journey canvas (any currently running journey) | CT → Journeys → click a running journey | Documents node structure and branching patterns for the journey-configuration model |
| Screenshot of the Reachability panel for Base Eligible segment | CT → Segments → Base Eligible → Reachability tab | Confirms reachability numbers match our table, catches any recent changes |
| Screenshot of the RFM analysis view | CT → Analytics → RFM | Shows how CT's built-in RFM scoring works for Plum's user base |
| Screenshot of the CleverTap dashboard homepage (Engagement tab) | CT → Dashboard → Engagement | Shows overall engagement trends, active users, channel mix |
| Screenshot of any Metabase adoption dashboard currently in use | Metabase → relevant dashboard | Validates operational metrics vs our analysis |

### 19.4 What We NEED — From the Data Team

| Question | Ask | Priority |
|----------|-----|----------|
| Do all org-ID property variants resolve to the same value? | Vijender | 🟡 |
| Does `App Uninstalled` genuinely have zero volume or is it not firing? | Vijender | 🟢 |
| What caused the ENT M9 "target met" rate to drop to 0% in Jun-Jul? | Vijender/Sathvik | 🔴 |
| What caused the 8.75x jump in aggregate "Targets Met" metric? | Vijender/Sathvik | 🟡 |
| Are historical adoption sheet snapshots available month-by-month? | Vijender | 🟢 |
| Is there a master DND org list (beyond the 43 names we have)? | Prayat/Vijender | 🟡 |
| Which CleverTap API endpoints does our account have access to? | Vijender | 🔴 |

### 19.5 Synthetic Data Calibration Points

If we use the synthetic data generator as a fallback, these are the real distributions it must encode:

| Parameter | Real Value | Source |
|-----------|-----------|--------|
| Total eligible users | 956,050 | Base Eligible segment |
| No-app share | 77.3% (739,126 / 956,050) | No App segment |
| TH eligible never-booked | 173,373 | TH segment |
| HC eligible never-booked | 75,272 | HC segment |
| ENT employee share | ~57% | Adoption sheets |
| SMB account share | ~65% | Adoption sheets |
| TH homepage-to-conversion rate | 12.76% | TH master funnel |
| HC homepage-to-conversion rate | 6.14% | HC master funnel |
| WhatsApp reachability (P0 segments) | 97-98% | Segment reachability |
| Push reachability (base) | 23% | Base segment |
| Peak activity window | 8-11 PM | Behavioural data |
| TH repeat-use rate once started | ~5 consults/year | Product knowledge |
| HC repeat booking rate | ~1.0 bookings/user | Product knowledge |
| Org-level activation rate | ~74% | Adoption analysis |
| Employee-level activation rate | ~10% | Adoption analysis |
| M3/M6/M9 targets | 15% / 25% / 35% | Manager-confirmed |
| Control group standard | 5% flat | Mentor + manager confirmed |
| DND-locked TH employees | ~13,835 | DND matching exercise |
| DND-locked HC employees | ~5,621 | DND matching exercise |

### 19.6 Key Correlations the Synthetic Data Must Encode

1. **Tenure → adoption**: M3 < M6 < M9 monotonically in every segment
2. **ENT = most employees, worst per-employee adoption**: inverse relationship between headcount share and adoption rate
3. **EOR = smallest, best adoption**: ~2x the company average at M9
4. **No-app = largest barrier**: 77% of eligible users, unreachable via push
5. **WhatsApp/SMS ≫ Push for reachability**: 97-98% vs 11-43%
6. **TH early-funnel drop, HC late-funnel drop**: structurally different friction points
7. **HC cross-sell → TH**: 14.32% of report viewers book a TH consult
8. **DND skews Enterprise**: don't model as uniform across segments
9. **8-11 PM peak**: temporal pattern for engagement
10. **Org activation ≫ employee activation**: 74% vs ~10% — the structural gap

---

> **Last updated**: 21 August 2026
>
> **Status**: Living document. Update when new data arrives, when open questions are resolved, or when model training reveals gaps.
>
> **Usage**: Feed Sections 1-17 directly into the model's system prompt or knowledge base. Use Section 19 as the data collection checklist. The model should refuse to make predictions in areas where the data requirements marked 🔴 have not been satisfied.
