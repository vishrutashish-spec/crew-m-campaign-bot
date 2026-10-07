# Crew M: Project Brief

## What This Is

An AI-powered campaign intelligence platform for Plum's product marketing team.
It learns from real CleverTap user data: behavioral events, campaign history,
engagement patterns: and turns it into actionable campaign decisions backed by
evidence, not guesswork.

The system answers: **who** should receive a campaign, through **which channel**,
at **what time**, with **what message**, and **how well** it will perform: with
explainable reasoning behind every recommendation.

## Who It's For

Product marketing managers at Plum who plan and execute campaigns across
WhatsApp, email, push notifications, in-app, and SMS through CleverTap. They
have behavioral data, campaign history, and cohort information but no automated
way to turn that data into targeting decisions or performance predictions.

## The Problem

Campaigns are planned using intuition and tribal knowledge. There is no
systematic way to:

- Discover behavioral personas from actual usage data
- Predict how a campaign will perform before sending it
- Know which audience segment is the best fit for a given campaign
- Compare what-if scenarios (different channel, timing, copy) with evidence
- Score copy against what has historically worked

The data exists in CleverTap. The intelligence layer does not.

## The Demo Story (Full Loop)

This is the end-to-end flow that the product must demonstrate:

1. Marketer types: "I want more health checkup bookings"
2. System parses intent: HC activation, first-time booking
3. System surfaces data-driven personas discovered from real user clustering
4. System recommends the best-fit audience with scores and reasoning
5. System predicts conversion through the full funnel: delivery → open → click → convert
6. System recommends channel and timing based on real behavioral patterns
7. System explains every prediction with feature-level drivers (SHAP)
8. Marketer tweaks copy, channel, timing, or audience
9. System re-simulates live and shows the delta
10. Copy is scored against the baked-in style guide

Every number shown must trace back to data. Every recommendation must have a
reason. Every prediction must have a confidence level.

---

## Architecture Decisions (Locked)

### Screens

| Screen | Role |
|--------|------|
| **Overview** | Landing page. Eligible base, app/no-app split, the push-reachability gap, age cohort composition, both product funnels, and deterministic cross-metric insights. |
| **Age cohorts** | Six cohorts across the eligible base, selected from full-width tiles (no left rail). Per-cohort reachability, device and gender split, org-type drill-down table, both funnels, and cohort-specific insights. |
| **Simulator** | Cohort selection first, then filters narrow it: objective, org type, channel (picked via real WhatsApp / Gmail / Plum logos), send hour, DND and stale-token exclusions. Output is an exact audience size plus a clearly-labelled PREDICTED funnel. Step 4 is the copy studio: variants assembled from Plum's approved copy library (Master Journey doc + shipped WATI/PN messages), disciplined per channel (WhatsApp Utility vs Marketing classification, per-band emoji ranges, push title/body limits, soft CTAs, no fear framing under 26, no TH friction device in HC copy), each variant carrying a GENERATED label, itemised discipline checks, and a PREDICTED performance versus the channel prior, sized against the simulated send. A paste-your-own analyzer scores custom copy against the same rules. |
| **Methodology** | Field-level provenance, the reachability decomposition, literal CT event names, and the full list of invariants the model asserts at startup. |

### Naming

Plain naming throughout. No fantasy/game naming. Campaign Simulator, Persona
Explorer, Dashboard, Audience Recommender: not The Forge, Persona Guild, The
Watchtower, The Compass.

### Design language

Three colours carry every chart and nothing else: `#2B0B21` plum violet,
`#FF3F52` plum red, `#F8DBC9` cream. Metallic cyan is reserved for interaction
only: focus, active, selection: so data and controls are never confused.
Backgrounds are pure white and every panel carries a visible outline.

Vollkorn (serif) sets all headings, large figures and chart labels in plum
violet; Inter sets body copy in near-black. Panels use layered grounds
(engineered grid, dot field, warm aurora) and blueprint corner ticks.

Every chart exports to PNG with the font embedded, so an exported image is
self-describing rather than a fallback-serif mess.

### Data Strategy

1. **Anchors** are real: documented CT segment exports plus live CleverTap
   aggregate counts, each tagged with its provenance and pull date.
2. **Composition** is modeled where no measurement exists: age, gender, device,
   org type: and calibrated so every aggregate reconciles exactly to the anchors.
3. **Conflicts are recorded, never averaged.** `backend/anchors.py` carries the
   scope warning that split the two populations apart: the eligible base is
   956,050 in active non-test orgs, while CleverTap's `/counts` endpoints accept
   no org filter and so report account-wide. Dividing one by the other is the
   single easiest way to produce a wrong number here.

### Cohort model (replaces K-Means clustering)

Age cohorts are the primary organising dimension. K-Means personas are gone ,
they produced unstable, unexplainable groups whose subtotals did not reconcile.

| Aspect | Approach |
|--------|----------|
| Cohorts | Under 20, 21-25, 26-35, 36-40, 41-50, 51+ |
| Structure | 6 cohorts × 4 org types = 24 cells, every quantity an exact integer |
| Method | Largest-remainder (Hamilton) apportionment: not sampling |
| Guarantee | Deterministic: identical inputs always give byte-identical output |
| Verification | 25 invariants asserted at startup; the API refuses to boot if any anchor disagrees |
| Rates | Always derived from the counts shown beside them, so a percentage cannot contradict its own bar |

### Corrections this rebuild landed

| Was wrong | Now |
|-----------|-----|
| DAU 11,703: queried today, a partial day | 16,503: last complete day |
| Org activation 100%, gap 92 points: computed as "does any user in this org type have a booking", always true | 74% org vs 10% employee, the documented 64-point gap |
| Push reach ~27% from two unrelated random draws | 23% of base observed, decomposed into 138,588 real and 81,304 stale tokens |
| Total base 10,000 synthetic users | 956,050 eligible base |
| Segment rules emitted `DoctorList_Viewed`, `AppointmentSuccessful_Viewed`: both rejected by the API as invalid events, so those segments matched nobody | Literal names with the `EmployeeMobileApp_Telehealth_` and `healthCheckup` prefixes |
| Simulator intersected an app-install audience with app-installed push reach: two disjoint groups | Reach is measured against the same population the objective's pool is drawn from |

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js + React + TypeScript + Tailwind |
| Type | Vollkorn (local, `public/fonts/`) for headings and figures; Inter for body |
| Charts | Recharts, with PNG export via embedded-font SVG rasterisation |
| Backend | Python + FastAPI |
| Cohort model | Pure-Python integer apportionment: no sklearn, no sampling |
| Data | Documented CT segment exports + live CleverTap aggregate counts (read-only, ≤1yr windows, counts only) |
| Insights | Deterministic rule engine (`backend/insights.py`): no LLM in the number path |

### Backend layout

| File | Role |
|------|------|
| `anchors.py` | Every ground-truth number, each tagged OBSERVED / REFERENCE / DERIVED / MODELED, with the scope warning and recorded conflicts |
| `population.py` | Exact integer cohort model + `verify()`, which asserts all 25 invariants |
| `insights.py` | Deterministic cross-metric insight rules, each carrying its own arithmetic |
| `server.py` | Cohort-first API; will not serve a request unless `verify()` passes |

---

## Baked-In Domain Intelligence

These are not reference documents. They are hardcoded system rules that Crew M
enforces automatically. They come from the Crew M operational playbooks.

### Segment Definitions (Exact CT Event Names)

**AARR funnel:**
- M0 NEW APP users: gmcMembershipCreatedAtTimestamp 30-60 days ago + inviteCreatedAt 30-60 days ago + App Launched in last 60 days
- Activations: any of: cultfitoffer_explored, healthCheckuplisting_viewed, Telehealth_DoctorList_Viewed, perks_offer_unlocked
- Revenue: any of: superTopUp_purchased, topUp_purchased, oPD_purchased, mAternity_purchased

**Lifecycle segments:**
- Unacquired: NOT done App Launched in last 180 days + membership exists in last 365 days
  - Fresh (30-60d), Lapsing (60-90d), Dormant (90-365d)
- Unactivated: downloaded app, NOT done any activation event, hard cutoff 90 days
  - Fresh (last 7d), Lapsing (7-14d), Dormant (14-90d)
- Retained: done at least 1 activation event
  - Fresh (last 30d), Lapsing (30-60d), Dormant (60-90d)

**HRA behavioral events:**
- hra_entry_viewed, hra_started, hra_question_answered, hra_completed, hra_score_viewed, hra_goals_saved, hra_recommendation_viewed, hra_recommendation_clicked
- Derived states: never started, started-dropped-off, completed-no-goal, completed+goal-no-action, high-risk-no-action-30d

### Narrative Playbook (Lifecycle → Messaging Angle)

| Segment State | Messaging Angle |
|---------------|----------------|
| Unacquired: Fresh | Urgency + first action ("get started in the next 30 days") |
| Unacquired: Lapsing/Dormant | Re-acquisition, remove friction, remind of what's theirs |
| Unactivated: Fresh | Remove-friction framing, one clear first step |
| Unactivated: Lapsing/Dormant | Re-surface single highest-converting hook |
| Retained: Fresh/Lapsing | Habit/streak framing, build on existing engagement |
| Retained: Dormant | Re-engagement without guilt-tripping |

**HRA-specific angles:**
- Never started → lead with speed + personalization
- Dropped off → low-friction reminder, emphasize how little is left
- Completed, no goal → nudge toward goal-selection screen
- Completed + goal, no action → recommendation-specific push matched to goal
- High-risk, no action 30d → care-forward urgency, never fear-based

### Copy Style Guide (Hard Rules)

These are enforced in copy scoring. Violations are flagged.

1. **No "not X" negation contrasts.** State the positive claim and stop.
   - Bad: "Recommendations built around your results: not generic advice."
   - Good: "Recommendations built specifically from your results."

2. **No ", so you know X" tails.** Land the benefit in the main clause.
   - Bad: "A score across 7 key health areas, so you know exactly what to focus on."
   - Good: "Your health, scored across 7 key areas: with a clear place to start."

3. **No em dashes.** Rewrite as two sentences or restructure.

4. **Colon definitions must define what the thing IS**: not where it lives or how long it takes.

5. **Never invent stats.** No fabricated percentages or outcome figures. If no real number exists, phrase qualitatively.

6. **Never surface scoring formulas, weights, or percentile math** to end users.

7. **Skip acronyms** (HRA, GMC, GTL) in first-touch consumer copy unless defined.

8. **Lead with reader benefit**, not mechanism ("Get your Health Score in 5 minutes" beats "Complete your Health Risk Assessment").

9. **AM emails are shorter and more direct** than consumer copy. Professional counterpart, not end consumer.

10. **When editing a human draft, edit minimally.** Fix factual/compliance issues, typos, banned constructions. Do not rewrite wholesale.

### Plum Domain Rules

**Telehealth:**
- Video and chat consultations, chat being pushed (faster, cheaper)
- 24x7, cashless, bookable via app or WhatsApp
- Repeat usage is real (~5 consults/year once started)
- Adoption metric is unique users, not total bookings
- Canonical event: EmployeeMobileApp_Telehealth_AppointmentSuccessful_Viewed
- Problem is early-funnel: 67% never open the doctor list

**Health Checkups:**
- At-home biomarker screening, one free per year
- Priority is first-time activation, NOT repeat usage
- Right angle: "you still haven't used the one in your plan"
- wallet_expiry_days_left powers urgency messaging
- Canonical event: healthCheckupbooking_confirmed
- Problem is late-funnel: friction through every stage after listing

**Four Adoption Gaps (diagnose before messaging):**
| Gap | Symptom | Fix |
|-----|---------|-----|
| Awareness | Doesn't know benefit exists | Information + visibility |
| Friction | Knows, but booking feels like effort | Reduce steps, deep links |
| Trust | Unfamiliar with virtual care | Testimonials, profiles, security |
| Trigger | Knows and trusts, nothing nudges action | Urgency, seasonal, wallet expiry |

**Confirmed funnel numbers:**
- TH: 126K Homepage → 41K DoctorList (33%) → 23K SlotScreen (18%) → 17K BookClick (13%) → 16K Success (12.8%)
- HC: 83K Homepage → 47K Listing (57%) → 12K ItemAdded (15%) → 7K SlotSelected (8%) → 5K Confirmed (6.1%)

**Partner segments:**
- ENT: 57% of employees, worst adoption (biggest lever)
- SMB: 65% of accounts, 14% of employees
- MM: consistent improver
- EOR: smallest, best per-employee performer (2x avg)

**Key correlations:**
- Adoption compounds with tenure (M3 < M6 < M9)
- 74% org-level activation vs ~10% employee-level (the gap)
- 8-11 PM peak activity for many segments
- WhatsApp/SMS highest reachability (97-98%)
- No-app segment is 77% of eligible users (739K of 956K)

### Adoption Targets

| Milestone | Target |
|-----------|--------|
| M3 | 15% unique users / eligible employees |
| M6 | 25% |
| M9 | 35% |

---

## The Four-Way Distinction (Non-Negotiable)

Every output the system produces must be clearly labeled as one of:

| Label | Meaning | Example |
|-------|---------|---------|
| **OBSERVED** | What actually happened historically | "Segment A had 8.2% conversion across 14 campaigns" |
| **PREDICTED** | What the model expects to happen | "Estimated 7.5% conversion for Segment A" |
| **RECOMMENDED** | What the system suggests doing | "Prioritize Segment A over Segment C" |
| **GENERATED** | What the LLM created | "Here are three copy variants for Segment A" |

Never blur these. Never present a prediction as an observation. Never present
generated copy as a data-backed recommendation.

---

## What's In Scope

- Real CleverTap data pipeline (synthetic fallback)
- Real clustering for persona discovery
- Real prediction models (XGBoost/LightGBM) for campaign simulation
- SHAP explainability for every prediction
- Audience recommendation with scoring and reasoning
- What-if simulation (change any variable, see the delta)
- Copy scoring against style guide rules
- Pixel avatar personas
- 3 polished screens (Dashboard, Persona Explorer, Campaign Simulator)
- Baked-in domain rules from Crew M playbooks
- Confidence levels and evidence volume on every prediction

## What's Out of Scope

For the Dashboard / Persona Explorer / Campaign Simulator platform described
above:

- Campaign drafting/activation in CleverTap
- Uplift modeling (needs control group data we don't have)
- Auto model retraining and drift detection
- Copy generation (analysis and scoring only, not generation)
- Figma template filling
- Backtesting dashboard (can show static validation results)
- Send-time optimization as a separate model (show timing data in persona cards)
- Real-time CT webhook integration

Campaign drafting, copy generation, and Figma creative rendering ARE in scope
for the separate AM Campaign Request Bot workstream below: that exclusion
list is specific to the analytics platform, not the whole project.

---

## Workstream: AM Campaign Request Bot (Krtin)

A second, separate slice of Crew M, running alongside the analytics platform
above. Origin problem: AMs hit the same friction every time they set up a
CleverTap campaign for a client: copy, creative, segment, and the fear of
getting it wrong. This workstream automates the mechanical setup so the AM
only supplies intent, and a human (PMM) still approves before anything goes
out.

**Flow**: AM runs `/new-campaign` in Slack → a modal collects AM name, account
name, campaign type (Welcome/Renewal), and an optional logo → n8n
(`iw-crew-m-c4b9 · AM campaign request → CleverTap draft`) parses the
submission, stores the raw input for audit, and calls this app's own API
routes in sequence: generate copy → render creative → build a CleverTap
campaign **draft only** → reply in Slack with a link to the draft. A PMM
reviews and publishes the draft directly in CleverTap: this tool never
publishes/sends anything itself.

**In scope for this workstream**: campaign drafting in CleverTap (draft
state only, never published by this tool), copy generation grounded in
account context, creative rendering, Slack modal intake.

**Out of scope for this workstream**: publishing/sending campaigns (PMM does
that manually in CleverTap), any UI beyond the Slack modal: this workstream
has no screens of its own in the three above.

**Reference docs**: `CLEVERTAP_CAMPAIGN_SETUP_SKILL.md`,
`CLEVERTAP_PLATFORM_REFERENCE.md`, `Copy_SKILL.md`.

**Where it lives**: API routes under `frontend/app/api/` (this is what's
actually deployed at the Vercel domain the n8n workflow calls): separate
from `backend/server.py`, which is the Python/FastAPI service for the
analytics platform's ML pipeline and is not part of this workstream.

**Environment variables needed** (set in `frontend/.env.local` for dev, and
in the Vercel project settings for the deployed app: never commit values):
`SLACK_BOT_TOKEN` (requires creating a Slack app: not done yet),
`ANTHROPIC_API_KEY`, `CT_ACCOUNT_ID`, `CT_PASSCODE`, `CT_REGION`.

**Known gaps**: creative rendering is currently a stub (no real Figma call);
CleverTap has no API to create campaigns, so `/api/campaign/draft` produces
a structured brief for a human to paste into CleverTap's dashboard rather
than a real CT draft; there's no Slack app yet, so nothing in this workstream
runs end-to-end until one is created and `SLACK_BOT_TOKEN` is set.

---

## Build Principles

1. **Do not fake intelligence.** Every number must come from data or a trained
   model. Never hardcode outputs. Never use the LLM to invent conversion rates.
   If the model can't make a reliable prediction, say so with low confidence.

2. **Data-driven personas, not invented ones.** Personas emerge from clustering
   real behavioral data. The LLM writes the narrative description, but every
   claim in that narrative must trace to cluster statistics.

3. **The LLM is for language, not math.** Use it for: parsing natural language
   campaign briefs, writing persona narratives, explaining predictions in plain
   English, analyzing copy against the style guide. Do NOT use it for: predicting
   conversion rates, scoring audiences, ranking channels.

4. **Build incrementally.** Get data pipeline + models working (even ugly) before
   touching the frontend. Show working software early. React to what's real.

5. **Graceful degradation.** Insufficient data → say so. Unknown campaign type →
   say so. Weak confidence → show it. Missing channel history → exclude it.
   Never fabricate an answer because the UI expects one.

6. **Secrets in env vars, never in code.** CleverTap credentials, API keys, any
   credentials go in `.env` / `.env.local`, never committed to git.

### Design addenda (locked this session)

- No em dashes anywhere: UI, copy output, captions.
- Channels carry their real brand logos (WhatsApp glyph, Gmail M, Plum p) on
  charts, legends, pickers and rows. Bar colours stay in the three-colour
  palette; logos carry identity.
- macOS chrome (traffic lights, curved tops, hairline bars) on the main page
  banners and message previews. White surfaces only.
- Crew M brand mark: geometric M in the plum gradient with a metallic cyan
  signal node, in components/logos.tsx.
- backend/copy_engine.py is the deterministic copy engine; /api/copy/options,
  /api/copy/generate, /api/copy/analyze serve it.
- Dark mode: token-driven (.dark on <html>), plum-black surfaces, cream-led
  chart series, cream metallic primary button, OS-preference default with
  localStorage persistence and a no-flash inline init script. Theme toggle
  pill lives in the sidebar. PNG exports follow the active theme.
- All headings carry the brand gradient (light: plum to red; dark: cream to
  red) via background-clip: text.
- Accuracy iterations (locked): click-to-convert is computed from observed
  funnel counts for th_activation (12.76%), hc_activation (6.14%) and
  hc_crosssell (14.32%); the old modeled priors ran +36.8% / -28.1% off.
  Channel recommendation is a published 6-parameter weighted rubric
  (decisions.py, v1.0), not argmax reach; a 20-simulation sweep runs at every
  boot and the server refuses to start if any check fails.
- Decision transparency: every simulation ships its rubric breakdown; the UI
  renders the weights as a spectrum pie (deliberately non-plum colours) in a
  collapsed "How this recommendation was calculated" panel.
- Ask Crew M (simulator step 5): deterministic grounded Q&A over the verified
  model + approved copy library. Every reply carries the facts it used with
  provenance and scores itself against a published 9-parameter rubric
  (mean 9.8/10 across ten question families in testing). No free generation.
- Brand v5 (locked): "Crew M" in Vollkorn Bold as SVG text with a static
  cyan-spectrum gradient. No animation, nothing pointy, never boxed. One
  static seafoam node after the M. Favicon: broad rounded wave with node,
  on transparency.
- Liquid glass: a restrained .glass utility (backdrop blur + saturate,
  hairline top light, diagonal specular) on surfaces that float over colour:
  banner stats strips, tooltips, popovers, the org control, the theme pill,
  mac title bars. Scarce by rule.
- Charts carry gradient series fills + soft dashed grids via shared SeriesDefs.

### Clinical intelligence layer (new)

`backend/aggregates/real_aggregates.json` holds aggregate-only extractions from
Plum's own telehealth consultation file (34,528 valid members, 133,218 consults,
24 specialties) and health checkup file (36,526 bookings, 11 scored biomarkers).
No member rows, no free text, doctor_notes never read.

Three data defects handled openly, not hidden:
- patient_age ranges from -517 to 2026; filtered to 15-80, dropping 2.87%
- appointment timestamps are UTC; converted to IST or the curve peaks at 05:00
- checkup bookings carry no age; joined via member id, matching 42.6%

Findings that drive the product: Vitamin D abnormal in 80.2% of bookings
(median 17 against a 30 threshold) and worst in the young at 88.1%; HbA1c
nearly triples from 12.1% at 21-25 to 34.1% at 41-50; LDL peaks at 36-40
(66.8%), which is hard evidence for the Bible's "36-40 is the pivot band"
copy strategy; Dermatology peaks at 21-25 (18.2%); Psychology collapses after
36; Orthopedics climbs with age.

### Send timing, rebuilt

`backend/timing.py` replaces the modeled peak-hour table. Real booking intent
is twin-peaked at 11:00 and 18:00-19:00 IST across 133,218 consults; the
often-quoted 20:00-23:00 window carries only 18.9% and sits past the peak.
Sends lead intent by channel: email 90 min ahead into an inbox sweep (09:30),
WhatsApp 30 min ahead (10:30), push at the peak itself (11:00). Quiet hours
01:00-06:00 are never used. Every recommendation ships its clock, its weights
and the corrections it applied.

### SIGNAL

`backend/signal_engine.py`, surfaced on the cohorts page in a glass phone
frame with a pixel avatar. Deterministic grounded retrieval over the cohort
model, the clinical aggregates and the approved copy library. Answers
specialty patterns, biomarker gradients, segment filter rules, timing,
channels, reach and provenance. Has a voice with deterministically varied
openers. Scores every reply against a published 10-parameter rubric
(grounding, numbers, provenance, depth, specificity, action, honesty, voice,
brevity, hygiene): mean 9.98/10 across 23 question families, nothing below
9.7.

### Decision transparency, extended

Both the channel recommendation and the funnel projection now ship a "how this
was calculated" panel: weights as a spectrum pie, per-stage arithmetic with
rates and provenance, and the observed/derived/modeled composition. Timing
carries the same treatment plus the corrections it applied.

### Session additions

- Cursor glow: a two-layer plum-red bloom eased toward the pointer in a rAF
  loop, written straight to transform so React never re-renders on mouse move.
  Hidden on touch and under reduced motion.
- Chart tooltips: filled swatches via `.tip-dot`, with gradient series paints
  mapped back to their solid token by `solidPaint`. The dot is inline-block, or
  width and height are ignored outside a flex context.
- SIGNAL is now a floating launcher opening a phone-shaped dock: escape to
  close, click-outside to close, composer autofocus, aria-expanded and
  aria-controls, conversation state preserved across open and close, near
  full-width under 720px. Screen is 9:16 by aspect-ratio. Avatar animates.
- Segment answers are grouped by property type (base user properties, product
  eligibility, event conditions, suppression) and rendered as non-wrapping
  scrollable rule rows, so 78-character CleverTap names never break per
  character or spill past the glass.
- Intent matching is anchored at word starts. Naive substring matching had the
  ENT Surgeon keyword firing inside "segment for" and "event properties".
- Email copy is now distinct from WhatsApp for every objective and band:
  verified 0 collisions across 30 combinations.
- push.with_app moved into population.cohort_summary so every endpoint carries
  it, with a 26th invariant asserting it is present and non-zero per cohort.
  Previously the cohort list omitted it and the chart plotted zero.
- Settings page restored: data sources and their scope, guardrails in force,
  published rubrics with weights, startup invariants, appearance, and the
  Brigold licensing caveat.
- Wordmark uses Brigold DEMO. Personal-use licence only; commercial licence
  needed before this ships.

### SIGNAL surfaces

Three placements, one component, so answer quality cannot drift:
- Cohorts page: inline, framed with window chrome and aurora, phone centred.
- Simulator step 5: the same framed treatment, replacing the old flat AskPanel
  that was still rendering there.
- Global floating launcher on every page, opening a phone-shaped dock.

Query understanding hardened: intents are ranked by matched-keyword weight
rather than declaration order, so multi-part questions lead with the intent
that carries more of the sentence. A normalisation pass fixes common
misspellings before detection. Unmatched questions get an honest answer that
says so and lists what SIGNAL can actually answer, rather than a generic
brochure. Verified across 24 queries including typos, multi-intent and
nonsense: mean 9.90, min 9.4, none below 9.

## Deployment topology

Two Vercel projects, deliberately, because the two halves want different build
shapes and forcing one project to serve both produced a deploy that reported
success and then 404ed every route.

| Project | Contains | Config | Root |
|---|---|---|---|
| `iw-crew-m-c4b9` | The Next.js app | zero-config | Root Directory `frontend/` |
| `iw-crew-m-engine` | The Python engine | `vercel.engine.json` | repo root |

The engine project needs the repo root, because `api/index.py` bundles
`backend/**` and files outside a project's Root Directory are not available to
it. The app project needs Root Directory `frontend/`, because that is where its
`package.json` lives and Next.js version detection reads it there.

Deploy commands, from the repo root:

    iw-deploy                                    # the app
    vercel deploy --prod -A vercel.engine.json   # the engine

The engine deploy needs `VERCEL_PROJECT_ID=prj_dkR8WNgRzq5acKc4xSp85PiTbvul`
exported, since `.vercel/project.json` is linked to the app project.

The browser never learns the engine origin. `frontend/next.config.ts` rewrites
`/api/engine/:path*` to it server-side, so every request the client makes is
same-origin: no CORS surface, and no cross-origin fetch of Plum aggregates from
a page. `ENGINE_ORIGIN` overrides the target for a preview engine or a local
uvicorn.

Two things worth knowing before the demo.

**Demo on the `.vercel.app` host, not the `.insurwreck.com` one.** Plum's Sophos
web filter blocks `insurwreck.com` as an uncategorised site from inside the
corporate network: it intercepts TLS with its own CA and redirects to an
internal block page. The deployment is fine; the network is not letting that
hostname through. `iw-crew-m-c4b9.vercel.app` passes the filter.

**Both projects are public.** The app displays aggregate cohort figures and the
engine serves them unauthenticated, so anyone with either URL can read them.
That is the same posture the desk provisioned for the app, and the engine
exposes nothing the app does not already show, but it is a real property of the
deploy rather than an accident to discover later. There are no member rows in
either path.

### Deploying a shared project: verify the alias, not the deployment

`iw-crew-m-c4b9` is one Vercel project shared by three people deploying from
three local trees, and **production is whoever deployed last**. That has already
broken the live site once: two deploys landed from a tree that predated a push,
and the campaign creative in `public/creative` vanished from
`iw-crew-m-c4b9.vercel.app` while still being present and reachable on the
individual deployment URLs.

Two habits avoid it.

**Pull before you deploy.** `git pull --rebase origin main` first, then build,
then deploy. Deploying a stale tree does not just miss your teammates' work, it
actively removes it from production.

**Verify on the alias.** `https://iw-crew-m-c4b9.vercel.app` is the only host
that proves anything. A `…-insurwreck.vercel.app` deployment URL returning 200
tells you your build is fine and says nothing about what the demo will serve,
because the alias may be pointing somewhere else entirely.

A quick check that catches the specific failure:

    curl -sL -o /dev/null -w '%{http_code}\n' \
      https://iw-crew-m-c4b9.vercel.app/creative/evening-call.png

404 there means production is running someone's older tree, and the fix is to
pull, build and deploy again.
