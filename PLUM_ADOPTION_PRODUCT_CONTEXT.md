# Plum Adoption & Product Context

> **Purpose**: Reference document for the Crew M campaign system. Explains what each Plum benefit product IS, how adoption data works, how user behaviour is analysed, the confirmed cohort framework, and exactly how to read/interpret raw Telehealth and Health Checkup data dumps — including age, behaviour, lifecycle, and engagement dimensions.
>
> **Audience**: The Claude Code session building the Crew M platform. Feed this alongside the Master CT Bible.

---

## 1. What Plum Actually Is

Plum is a **B2B corporate health benefits platform**. Its customers are **companies** (called "orgs" in the data). Those companies buy benefits plans for their **employees**. The employee is the end user — the person who actually opens the app, books a consultation, or schedules a health checkup.

The adoption problem Plum solves: companies have already purchased these benefits for their employees, but a large share of employees never use them. The PMM team's job is to move that number — get more employees to actually activate and use the benefits they already have access to.

**Key mental model**: This is NOT a consumer acquisition problem. The "customer" (the company) is already paying. The employee already has the benefit. The problem is **activation of an existing entitled base**, not convincing someone to buy something new.

---

## 2. The Benefit Products

### 2.1 Telehealth (TH)

**What it is**: On-demand doctor consultations via the Plum app — both **video calls** and **chat-based consultations**. Available 24×7, cashless (covered by the employer's plan), bookable through the app or WhatsApp.

**How it works for the employee**:
1. Open the Plum app → navigate to the Telehealth section
2. Browse available doctors or use the doctor-matching tool (symptom assessment → specialist recommendation)
3. Select a doctor → pick a time slot → enter consultation details → book
4. Attend the video or chat consultation
5. Receive prescription/follow-up if needed

**Key behavioural characteristics**:
- **Reactive trigger**: People use Telehealth when something is wrong — a symptom, a question, a concern. It's driven by a health need in the moment, not by scheduled prevention.
- **Real repeat-usage pattern**: Once someone uses TH for the first time, they average ~5 consultations/year. The product genuinely works — the problem is first-time activation, not retention.
- **Chat is being pushed deliberately**: Faster for the user, lower cost for Plum. Many queries are simple enough that a chat with a real doctor replaces what someone might otherwise Google.
- **Adoption is measured by unique users, not total bookings** — confirmed directly by the manager. Even though repeat usage exists, the official M3/M6/M9 targets (15%/25%/35%) count unique users who have booked at least once.

**Canonical CleverTap event**: `EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed` — this is the confirmed "booked" signal. Use this everywhere. `AppointmentCreated` is NOT the canonical event.

### 2.2 Health Checkups (HC)

**What it is**: At-home biomarker screening — comprehensive preventive health testing (100s of markers), with AI-assisted reporting. A newer, strategically prioritised product line for Plum.

**How it works for the employee**:
1. Open the Plum app → navigate to Health Checkups
2. Browse available checkup packages (listing page)
3. Check serviceability (whether home-visit testing is available in their area)
4. Select a package → add to cart → select family member → pick a slot → confirm address
5. Complete payment (free first checkup in most plans; paid advanced tier exists but is secondary priority)
6. Receive home visit for sample collection
7. View report in-app once results are processed → optionally download → optionally book a Telehealth follow-up to discuss results

**Key behavioural characteristics**:
- **Proactive trigger**: Unlike TH, nothing is "wrong" yet. The employee has to be motivated to take a preventive action. This requires fundamentally different messaging psychology — "stay ahead of it", seasonal health angles, countdown urgency ("your free checkup expires in X days").
- **One free checkup per year**: In most plans, employees get ONE free health checkup annually. Once used, there's no urgency to rebook. This means HC's low repeat-booking rate (~1.0 bookings/user) is **structurally expected, not a problem to fix**.
- **Current priority is FIRST-TIME activation**: Getting employees to use the free checkup already sitting in their plan, not repeat usage. "You still haven't used the one already in your plan" is the right messaging angle.
- **A paid advanced tier exists** (employee pays, Plum earns revenue) but is explicitly secondary — only worth focus after first-time free-checkup activation improves.
- **Adoption is measured by unique users**, same as TH.

**Canonical CleverTap event**: `healthCheckupbooking_confirmed` — no ambiguity, already the team's operational standard.

### 2.3 Mental Health / Wellness

**What it is**: Mental health and wellness support offered through the Plum platform, typically including therapy sessions, counselling access, and wellness content. Available as part of the broader benefits package.

**What we know from data**:
- Post-checkup health risk dimension properties exist in CleverTap: `dimension_score_mentalHealth`, alongside `cardiometabolic`, `msk`, `nutrition`, `physicalActivity`, `sleep`, `substance`, and `overall_score`.
- An `hra_completed` flag tracks whether someone has completed a Health Risk Assessment.
- These properties enable cross-sell cohorts like "high mental health risk score from checkup → recommended for a consultation" — noted as a future opportunity, not an immediate priority.

**For campaign targeting**: Mental health appears primarily as a **dimension within checkup results** and as a potential cross-sell trigger (checkup → consultation), rather than a standalone product with its own separate funnel. Model it as a property/signal, not a separate product vertical.

### 2.4 GMC (Group Medical Cover) / Insurance

**What it is**: The core group health insurance product — hospitalisation cover, OPD, maternity, etc. This is the foundational product that most Plum corporate clients purchase; TH and HC are add-on benefits layered on top.

**Relevance to adoption work**:
- GMC is the **baseline relationship** — the org is a Plum customer because of GMC. TH and HC adoption campaigns target employees who already have GMC.
- GMC data (policy details, renewal dates, coverage specifics) exists in the system and influences targeting: `SMB_RenewalDate`, `SMB_DaysToRenewal`, `SMB_ExpiringPolicy` properties are confirmed in CleverTap.
- Renewal-timed campaigns are a legitimate adoption lever: an approaching GMC renewal is a natural moment to push TH/HC activation ("while your plan is active, have you used your free checkup?").

**For campaign targeting**: GMC is context, not a product you're building campaigns for directly. It defines the eligible population and the commercial relationship. Treat GMC status/renewal as a **segmentation dimension**, not a conversion goal.

### 2.5 How the Products Relate

- TH and HC events are tracked **mostly separately** in CleverTap, but it's frequently the **same employee** who could receive messaging for both.
- A confirmed **cross-sell bridge event** exists: `healthCheckuptelehealthBooking_done` — an employee booking a TH consultation from within the HC results flow. This is a live, working signal already in use.
- Targeting must stay **coordinated across products** — avoid stacking uncoordinated pushes on the same user in a short window.
- A broader goal sits above both: driving **general Plum app engagement**, not just bookings. "Opened the app" or "explored benefits" can be legitimate intermediate goals.
- **Seasonal relevance** matters: monsoon/dengue season is a natural moment for both "get checked" (HC) and "consult quickly" (TH).

---

## 3. How Adoption Data Works

### 3.1 The Measurement Framework

**The target**: Move employee-level adoption from ~10-12% (baseline at project start) toward 35% by M9 (month 9 of an org's tenure on Plum).

**Tenure-staged targets**: M3 = 15%, M6 = 25%, M9 = 35%. These are **cumulative unique-user adoption rates** — the percentage of eligible employees who have used the benefit at least once by that milestone.

**What "eligible" means** (confirmed definition):
- `organisationStatus = ACTIVE`
- `isTestOrganisation != true`
- Relevant membership timestamp exists and falls within the last 365 days
  - TH: `warehouse_production_telehealthMembershipCreatedAtTimestamp`
  - HC: `warehouse_production_plumHealthCheckupMembershipCreatedAtTimestamp`
- The timestamp **renews annually** — so it correctly captures anyone in an active benefit year regardless of total tenure.
- TH and HC have **separate** membership properties — eligibility is per-product.

**What "adopted" means**: At least one confirmed booking event for the relevant product, by a unique user. Not total bookings, not page views, not app installs.

### 3.2 Two Ways of Computing Adoption (Know the Difference)

| Method | How it works | Who it favours | Use it for |
|---|---|---|---|
| **Pooled** | Total bookings ÷ total eligible employees, company-wide | Naturally weighted toward segments with the most employees (Enterprise dominates) | Official target-tracking — reflects real employee-level impact |
| **Median-of-org** | Each org's own rate, then find the middle value | Every org counts equally regardless of size | Understanding "typical org experience" — but risks overstating true adoption if large orgs are underperforming |

These can disagree by several percentage points. **Default to pooled** for anything official. Call out the gap if it's large.

### 3.3 The Org-Level vs. Employee-Level Gap

The **single biggest finding** from the data analysis: ~74% of orgs have at least one booking (org-level activation), but only ~10% of employees have ever booked (employee-level adoption). That's a ~64-point gap.

**What this means**: The "get the company to say yes" problem is largely solved. The bottleneck is reaching individual employees inside already-activated companies. This is the primary lever — more than acquiring new orgs.

### 3.4 Partner-Type Segments

| Segment | % of orgs | % of employees | Adoption behaviour |
|---|---|---|---|
| **SMB** (Small Business) | ~65% | ~14% | Many accounts, few employees each. Judge on accounts-activated. |
| **MM** (Mid-Market) | Middle | Middle | Most consistent month-over-month improvement in the data. Worth investigating what's working. |
| **ENT** (Enterprise) | Fewest | ~57% | Largest employee pool, historically worst per-employee conversion. **The single largest lever** — 1 point in ENT outweighs a much larger gain in a smaller segment. |
| **EOR** (Employer of Record) | Single-digit % | Single-digit % | Best per-employee performer (~2× company average at M9). Proof point to learn from, but too small to move the company number alone. |

**For a generic "never booked" cohort, the modeled partner-type composition is**: ~58.5% Enterprise, ~23.5% Mid-Market, ~13.9% SMB, ~4.1% EOR. Label this as modeled (weight = employee share × (1 − adoption rate), normalized), not measured. Exception: DND cohorts skew heavily Enterprise per direct manager confirmation — don't apply this formula there.

---

## 4. How We Look at User Behaviour

### 4.1 The Four Adoption Gaps

Before proposing any campaign, diagnose WHICH gap a cohort has. The fix is different for each:

| Gap | What's happening | The right fix | The wrong fix |
|---|---|---|---|
| **Awareness** | Genuinely doesn't know the benefit exists | Announcement, onboarding touchpoint, HR comms | Persuasive messaging (can't persuade someone who doesn't know) |
| **Friction** | Knows, but booking feels like effort or is unclear | Deep links, step reduction, one-tap booking, FAQ | More motivation copy (motivation doesn't fix UX friction) |
| **Trust** | Unfamiliar with virtual doctors, doubts data privacy | Testimonials, doctor credentials, privacy assurance | Loss framing / urgency (pressure doesn't fix distrust) |
| **Trigger** | Knows and trusts it, but nothing nudges action NOW | Seasonal timing, expiry countdown, "your colleagues use it" | Generic "use your benefit" push (no urgency = no action) |

### 4.2 The P0/P1 Prioritisation Framework

Given X = eligible users, Y = DND-locked users, Z = already-activated users:

- **P0 = X − Y − Z** → Reachable AND not yet converted. Target immediately. Default first-priority group.
- **P1 = Y ∩ ¬Z** → DND-locked AND not yet activated. Needs the AM/HR "utility messaging exception" route before any campaign can touch them.
- **Already-activated (Z)** → Out of scope for acquisition campaigns. For TH: may still target for repeat-usage/habit. For HC: NOT a repeat target (one free checkup/year is the norm).

### 4.3 The 4-Axis Cohort Checklist (Confirmed by Manager)

Every cohort must be defined across these four dimensions:

1. **Benefit type**: Telehealth-only / Health Checkup-only / Both
2. **App-downloaded status**: Yes / No (this is its own axis — "never installed" ≠ "installed but never booked")
3. **Benefit-used status**: Yes / No (has at least one confirmed booking)
4. **Lifecycle month**: M3 / M6 / M9

### 4.4 Lifecycle & AARR Framework

Adoption compounds with tenure in every segment — M3 → M6 → M9 all trend upward. The product mechanism works. The gap is speed-to-maturity and penetration depth.

| Stage | What it means | Key metric | Campaign type |
|---|---|---|---|
| **Acquisition** | Employee gains access to the benefit (org activates) | Eligible employee count | HR onboarding, welcome series |
| **Activation** | First meaningful use (first booking) | Unique users with ≥1 booking | Awareness, friction-removal, trigger campaigns |
| **Retention** | Repeat use (TH only — HC is one-and-done) | Bookings per activated user, MAU | Habit loops, seasonal re-engagement |
| **Revenue** | Paid tier adoption (HC advanced checkups) | Paid bookings / revenue per user | Upgrade campaigns (secondary priority) |

### 4.5 Behavioural Signals in the Data

**Engagement proxies** (confirmed in CleverTap):
- `App Launched` — the best existing MAU/engagement proxy, heavily used
- `App Installed` — confirms app presence (separate from App Launched)
- `App Uninstalled` — showed zero volume in the export; may not be firing correctly
- Benefit page views (TH homepage, HC homepage) — awareness/intent signals
- Funnel progression depth — how far someone gets before dropping off

**Cross-sell signals**:
- `healthCheckuptelehealthBooking_done` — HC-to-TH bridge (booked TH from within HC results)
- `healthCheckupreport_viewed` → no TH follow-up = warm cross-sell cohort (Cohort 9, ~10,517 users)

**Health risk dimensions** (post-checkup properties):
- `dimension_score_cardiometabolic`, `mentalHealth`, `msk`, `nutrition`, `physicalActivity`, `sleep`, `substance`, `overall_score`
- Future opportunity: route high-risk-score users to relevant TH consultations

---

## 5. The 15 Confirmed Cohorts

These are ranked, sized, and sourced from real data. The full details (definition, logic, recommended campaign, expected outcome) are in the Cohort Opportunity Report and the Master CT Bible. Summary for quick reference:

| # | Cohort | Size | Type | Product |
|---|---|---|---|---|
| 1 | TH Eligible Never Booked | 173,373 | Activation/P0 | TH |
| 2 | Enterprise Wide But Shallow | ~145,347 | Structural | Both |
| 3 | HC Eligible Never Booked | 75,272 | Activation/P0 | HC |
| 4 | No App Installed | 739,126 | Acquisition gate | Both |
| 5 | TH Drop Homepage→DoctorList | 85,219 | Funnel friction | TH |
| 6 | HC Drop Listing→Cart | 34,646 | Funnel friction | HC |
| 7 | Mature Dark Orgs (SMB/MM) | ~2,200 | Account-level urgent | Both |
| 8 | DND and Dark (P1) | 13,221 (AND) / 16,008 (OR) | P1 unlock | Both |
| 9 | HC Report Viewed, No TH Follow-up | 10,517 | Cross-sell | Both |
| 10 | TH Doctor-Match Abandoners | 14,427 | Funnel friction | TH |
| 11 | HC Booked, Report Never Viewed | 4,810 | Retention/value | HC |
| 12 | HC Payment Friction | 7,163 | Product/engineering | HC |
| 13 | TH Repeat-Use Lapsed | ~8,000 est. | Re-engagement | TH |
| 14 | HC Serviceability Failed | 794 | Ops signal | HC |
| 15 | TH Payment Abandoners | 258 | Highest intent, tiny | TH |

**Recommended starting point**: Lead with Cohorts 1 and 3 (largest, cleanest, zero-dependency). Pursue Cohort 8 in parallel (DND unlock compounds every other cohort). Use Cohort 7 as the fastest, smallest, most attributable proof point.

---

## 6. How to Read a Telehealth Data Dump

### 6.1 The TH Funnel (Real Events, In Order)

```
AWARENESS LAYER
  nativeDisplay_telehealth_card         → Entry point on home screen
  telehealth_entry_point_clicked        → Tapped the TH card
  TH_Homepage_Viewed                    → Landed on TH homepage

CONSIDERATION LAYER
  Care_Clicked / ConsultNow_Selected    → Chose to consult
  DoctorList_Viewed                     → Browsing doctors
  Doctor_Selected                       → Picked one
  Doctor_Profile_Viewed                 → Reading doctor profile

BOOKING LAYER
  SlotScreen_Viewed                     → Picking a time
  ConsultationInputDetails_Viewed       → Entering details
  BookAppointment_Clicked               → Hit the book button
  AppointmentSuccessful_Viewed          → ✓ CONFIRMED BOOKING (canonical event)

COMPLETION LAYER
  telehealth_doctor_joined              → Doctor joined the call
  TH_CallLog                            → Raw call-log stream

DOCTOR-MATCHING SUB-FUNNEL
  findDoctor_entryInitiated             → Started symptom assessment
  assessmentComplete                    → Finished assessment
  recommendationAccepted                → Accepted doctor recommendation
```

### 6.2 Key TH Drop-Off Points (From Real 120-Day Funnel Pulls)

| Stage transition | Conversion | What it means |
|---|---|---|
| Homepage → DoctorList | 32.7% | **67% drop at the first real step** — biggest leak in the whole TH funnel. Most people who visit TH never even browse doctors. |
| DoctorList → SlotScreen | 55.0% | Moderate — about half who browse proceed to pick a slot |
| SlotScreen → BookClicked | 73.8% | Good — once they're picking a slot, most continue |
| BookClicked → AppointmentSuccessful | 96.1% | Excellent — almost no payment/confirmation drop |
| Card display → Card click | 43.2% | Awareness layer — less than half of people shown the TH card click it |
| Doctor-match entry → Assessment complete | 44.1% | Half who start the symptom tool finish it |
| Assessment → Recommendation accepted | 23.1% | Steep drop — the recommendation step loses most users |

**The headline insight**: TH's problem is **early-funnel** — 67% never get past the homepage. Fix relevance and routing at the top, not payment friction at the bottom.

### 6.3 What to Look for in a Raw TH Data Dump

**User-level fields to analyse**:
- **Age/demographics**: Not directly available as a standard CleverTap user property in the confirmed schema. If present in a raw dump, segment by age bands (18-25, 26-35, 36-45, 46-55, 55+) and compare booking rates — hypothesis: younger users may prefer chat, older may prefer video.
- **Partner type** (`partner_type` or from org-level data): Enterprise employees are the largest underperforming group.
- **Org tenure** (derived from membership timestamp): Plot adoption rate vs. months-since-activation. Expect a curve that compounds — the question is how steeply.
- **Consultation type**: If the dump distinguishes video vs. chat, compare completion rates. Chat is being pushed deliberately.
- **Doctor speciality**: Which specialities get the most bookings? Which have the highest no-show/cancellation rates? This informs doctor-matching recommendations.
- **Time-of-day patterns**: When are consultations booked? When are they attended? Gaps between booking time and slot time indicate urgency vs. planned use.
- **Repeat usage**: Of users who booked once, what % booked again? What's the time gap between first and second booking? ~5 consultations/year is the known repeat-usage rate.
- **Channel source**: Did the booking originate from app, WhatsApp, or another channel? Informs channel prioritisation.
- **Geography**: City/region distribution — are there areas with low doctor coverage affecting completion?
- **Funnel depth reached**: For non-converters, how far did they get? Homepage-only vs. doctor-list-viewed vs. slot-selected-but-abandoned tells very different stories.

### 6.4 TH Engagement Patterns to Model

For the Crew M platform, these are the behavioural patterns worth encoding:

1. **First-visit-to-first-booking lag**: How many app sessions before someone books for the first time? Long lag = awareness/trust gap. Short lag (but low overall conversion) = friction gap.
2. **Repeat booking cadence**: Time between bookings for activated users. A sudden stop after consistent use = lapsed user signal.
3. **Doctor-match tool as a conversion accelerator**: Users who go through the symptom assessment → recommendation flow — do they convert at a higher rate than those who browse doctors manually?
4. **Cross-sell from HC**: Users who viewed their HC report and then booked TH — what's different about them vs. HC-report-viewers who didn't?
5. **DND impact**: Among otherwise-identical users, what's the adoption difference between DND-locked and non-DND orgs? This sizes the DND unlock opportunity.

---

## 7. How to Read a Health Checkup Data Dump

### 7.1 The HC Funnel (Real Events, In Order)

```
AWARENESS / BROWSE
  healthCheckuphomepage_viewed          → Landed on HC section
  healthCheckuplisting_viewed           → Browsing packages
  serviceability_checked                → Checked if home visit available
  skuList_viewed                        → Viewing specific test packages

CART / SELECTION
  item_added                            → Added a package to cart
  member_selected                       → Chose which family member
  slot_selected                         → Picked a date/time slot
  savedAddress_selected                 → Confirmed address for home visit

PAYMENT
  payment_initiated                     → Started payment
  paymentGateway_opened                 → Payment gateway loaded
  payment_processing                    → Processing payment
  paymentGateway_success                → ✓ Payment succeeded

CONFIRMATION
  healthCheckupbooking_confirmed        → ✓ CONFIRMED BOOKING (canonical event)

POST-BOOKING
  healthCheckupreport_viewed            → Viewed results in-app
  reportDownload_clicked                → Downloaded report PDF
  healthCheckuptelehealthBooking_done   → Booked TH follow-up from HC flow
```

### 7.2 Key HC Drop-Off Points (From Real 120-Day Funnel Pulls)

| Stage transition | Conversion | What it means |
|---|---|---|
| Homepage → Listing | 56.7% | Moderate — about half proceed to browse packages |
| Listing → Item Added | 26.3% | **Big drop** — three-quarters of browsers don't add anything to cart. Package selection/value proposition is unclear? |
| Item Added → Slot Selected | 55.0% | Moderate — half who add to cart proceed |
| Slot Selected → Booking Confirmed | 74.9% | Good — most who pick a slot complete |
| Listing → Serviceability Check | 47.6% | Nearly half check if service is available in their area |
| Serviceability → Failed | 1.5% | Very few fail serviceability (794 users) — small but an ops signal |
| Payment Initiated → Gateway Success | 16.6% | **Concerning** — but small absolute numbers (8,632 → 1,431). Many may be using the free checkup path that bypasses payment. |
| Booking Confirmed → Report Viewed | 65.3% | Good — two-thirds view their results |
| Report Viewed → Report Downloaded | 91.0% | Excellent — almost all viewers download |
| Report Viewed → TH Follow-up Booked | 14.3% | Cross-sell conversion — ~1 in 7 book a doctor consultation after seeing their results |

**The headline insight**: HC's problem is **persistent friction throughout the mid-funnel** — the leak continues from browsing through cart through payment. Unlike TH (where the top of the funnel is the whole problem), HC needs friction removal at multiple sequential stages.

### 7.3 What to Look for in a Raw HC Data Dump

**User-level fields to analyse**:
- **Age**: Critical for HC — hypothesis: older employees are more likely to value preventive screening. Segment by age band and compare booking rates, package selection, and report engagement.
- **Package/SKU selected**: Which checkup packages are most popular? Which are abandoned most? Price sensitivity vs. comprehensiveness trade-off.
- **Family member selection**: Are employees booking for themselves, spouse, parents, children? Dependent booking patterns tell a different story from primary-employee patterns.
- **Serviceability**: Geographic distribution — where does serviceability fail? This is an ops expansion signal.
- **Time from booking to sample collection**: How long between confirming and the actual home visit? Long gaps may indicate scheduling friction.
- **Time from collection to report availability**: Lab processing time — does it vary? Long waits may reduce report-viewing rates.
- **Report engagement depth**: Did they just glance at the report or download it? Did they share it? Did they act on it (booked a TH follow-up)?
- **Health risk scores**: Post-checkup dimension scores (cardiometabolic, mental health, MSK, nutrition, physical activity, sleep, substance). High-risk users who don't follow up = intervention opportunity.
- **Wallet expiry**: `wallet_expiry_days_left` — how close to expiry are non-bookers? Urgency messaging calibration.
- **Repeat booking** (rare but exists): For the paid advanced tier, who books again and when?
- **Payment path**: Free (wallet-covered) vs. paid — do completion rates differ? The free path should have near-zero payment friction.

### 7.4 HC Engagement Patterns to Model

1. **Wallet-expiry-to-booking urgency curve**: At what `wallet_expiry_days_left` value does booking probability spike? This calibrates countdown messaging timing.
2. **Report-to-follow-up conversion**: The 14.3% cross-sell rate is a strong baseline. What differentiates converters? Hypothesis: users with concerning scores are more likely to book TH.
3. **Package selection drivers**: Do users who view more packages (higher `skuList_viewed` count) convert at higher or lower rates? Over-choice paralysis vs. informed selection.
4. **Serviceability as a hard gate vs. soft gate**: Of users who fail serviceability, how many come back later? (Plum may have expanded coverage.)
5. **Dependent vs. primary booking patterns**: Different messaging needed — "book for your family" vs. "book for yourself."

---

## 8. Demographic & Behavioural Dimensions for Analysis

### 8.1 Age-Based Analysis

Age is not a standard CleverTap user property in the confirmed schema, but may be present in raw data dumps or derivable from date-of-birth fields. When available:

| Age band | TH hypothesis | HC hypothesis | Messaging angle |
|---|---|---|---|
| 18-25 | May prefer chat over video; lower health anxiety; "convenience" framing works | Low perceived need for preventive screening; "baseline your health early" angle | Digital-native, quick, casual tone |
| 26-35 | Peak working-age stress; dependents entering the picture; "save time" framing | Starting to think about prevention; family health concerns (children/parents) | Efficiency, family responsibility |
| 36-45 | Higher health awareness; may have chronic condition management needs | Strong preventive motivation; "catch things early" resonates | Health investment, proactive management |
| 46-55 | Most health-conscious; highest TH repeat-use potential | Highest perceived value; worried about lifestyle diseases | "Know your numbers", peace of mind |
| 55+ | May need more trust-building around virtual consultation | Strongest urgency for preventive screening | Doctor credentials, comprehensive coverage |

### 8.2 Behavioural Segmentation Dimensions

Beyond demographics, these behavioural dimensions create meaningful segments:

**By engagement depth**:
- **Ghost**: Eligible, app not installed, no digital footprint at all
- **Installed, dormant**: App installed but no launches in 90+ days
- **Browser**: Launches app, views benefits, never converts
- **Abandoned**: Reached mid-funnel (doctor list or cart) but didn't complete
- **One-and-done**: Single booking, no repeat (expected for HC; a retention signal for TH)
- **Active**: Multiple bookings or regular app engagement

**By channel responsiveness**:
- Push-responsive vs. email-responsive vs. WhatsApp-responsive vs. SMS-responsive
- Reachability data is available per segment (see confirmed segment set in Master CT Bible)
- Known reachability pattern: Push is weakest (~23-43%), Email/SMS/WhatsApp are strong (~80-98%)

**By lifecycle timing**:
- New employee (first 30 days of membership) — onboarding window
- Mid-tenure (30-180 days) — activation window
- Mature (180+ days) — if not activated yet, needs a different approach (they've already ignored multiple touchpoints)
- Approaching renewal — urgency window

**By org characteristics**:
- Partner type (SMB/MM/ENT/EOR) — different scale, different channels, different trust dynamics
- DND status — locked out of standard campaigns entirely
- Org-level adoption rate — "dark" orgs (zero or near-zero adoption) vs. partially-activated orgs
- Org size — affects social proof messaging ("2,400 of your colleagues use this" only works at scale)

---

## 9. The DND Dimension

DND (Do Not Disturb) is a **full-org-level flag** applied unconditionally via a CleverTap journey. When an org is DND:
- Every employee in that org has `is_in_DND_CT = true` set
- They are excluded from all standard marketing campaigns (every campaign checks `is_in_DND_CT != true`)
- The only path to reach them is through the AM/HR "utility messaging exception" — embedding activation content into operational/HR communications that the org has already approved

**Scale**: ~13,835 TH / ~5,621 HC employees are DND-locked (from the DND name-matching exercise). The P1 Dark cohort (DND + never used either product) is 13,221 (AND-logic) to 16,008 (OR-logic).

**Why it matters for modelling**: DND users must be treated as a separate population in any prediction model. Their conversion probability through standard campaigns is literally zero. The model should flag DND status prominently and route those users to the AM/HR pathway, not score them for campaign responsiveness.

---

## 10. Data Dump Interpretation Guide — Practical Checklist

When you receive a raw TH or HC data export, run through this before any analysis:

### 10.1 Data Quality Checks

- [ ] **Row count vs. expected population**: Does the dump size roughly match known segment sizes (e.g., ~173K TH-eligible-never-booked, ~75K HC)?
- [ ] **Date range**: What period does the dump cover? Our funnel pulls used a 120-day window.
- [ ] **Duplicate users**: Check for duplicate user IDs — especially if both camelCase and snake_case org-ID variants exist
- [ ] **Test org exclusion**: Confirm `isTestOrganisation = true` rows are excluded (or flag them for exclusion)
- [ ] **Inactive org exclusion**: Confirm `organisationStatus != ACTIVE` rows are excluded
- [ ] **DND flag present**: Is `is_in_DND_CT` in the export? Essential for P0/P1 splits.
- [ ] **Dependent flag present**: Is `is_dependent` in the export? Dependents skew counts if not handled.
- [ ] **Null/blank checks**: Watch for blank comparison values — a blank DND field once inflated counts to 3.8M+ in this project.

### 10.2 First-Pass Analysis

1. **Compute total eligible**: Active org + not test + membership within 365 days
2. **Split by partner type**: ENT / MM / SMB / EOR — compute adoption rates within each
3. **Split by DND**: P0 (reachable) vs. P1 (DND-locked)
4. **Split by app status**: App installed vs. not
5. **Split by booking status**: Never booked vs. booked-at-least-once
6. **Funnel analysis**: For each product, compute stage-to-stage conversion rates using the canonical events listed above
7. **Cross-product analysis**: How many users are dark on both products vs. one vs. neither?

### 10.3 Second-Pass — Behavioural Depth

1. **Recency**: When was the last meaningful event? Segment by recency bands (0-7d, 8-30d, 31-90d, 90d+)
2. **Frequency**: How many times has the user engaged? (App launches, page views, bookings)
3. **Funnel depth**: For non-converters, what was the deepest funnel stage reached?
4. **Channel engagement**: Which channels have they responded to? (Push opens, email clicks, WhatsApp reads)
5. **Time patterns**: Day-of-week and time-of-day patterns for bookings and engagement
6. **Cohort assignment**: Based on the above, which of the 15 defined cohorts does each user fall into?

---


## 12. What This Document Does NOT Cover

- **Campaign copy and messaging** — see the Copy Style Guide and the Master CT Bible's copy rules
- **CleverTap journey building mechanics** — see the Master CT Bible
- **Exact segment builder steps** — see the Master CT Bible
- **People and POCs** — see the Master CT Bible
- **Data export requirements** — see the Master CT Bible's Section 19 (Data Requirements appendix)

This document is the **"what and why"** companion to the Master CT Bible's **"how"**.
