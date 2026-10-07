# Campaign Bot - Build Plan

**What this document is.** The build plan for a Slack-triggered, PMM-approved
bot that creates CleverTap campaign drafts for client email sends. Covers scope,
architecture choices with their trade-offs, security requirements, and build
sequence.

**Scope.** The Slack bot only. One goal: an HR admin or AM asks for a campaign
in Slack, and a correctly-targeted, co-branded draft lands in the CleverTap
dashboard waiting for a PMM to click Publish.

Date: October 2026.

---

## 1. What the bot does, in one sentence

A Slack-triggered pipeline that takes a short structured request (campaign
intent, organisation, product), resolves the audience against standard
suppression rules (DND, test organisations, removed members, quiet hours),
writes copy against the house style, assembles creative that is co-branded
where appropriate, saves the result as a draft in CleverTap, and notifies a
PMM for manual publish. Nothing ever sends automatically.

Three constraints that follow from this:

1. **Draft only, never publish.** The bot's CleverTap credentials permit
   creating a draft. They do not permit publishing or scheduling. The Publish
   button stays human, enforced by scope.
2. **Templates own the structure, the bot owns the content.** The bot does not
   design emails. It fills slots in approved templates.
3. **Audience resolution is the highest-risk code in the system.** A wrong
   recipient list is the one error that cannot be rolled back once a draft is
   published. See §5 on the targeting bug.

---

## 2. Repository structure (post-cleanup)

The following files are the current reference set for anyone building against
this project.

| File | Role |
|------|------|
| `CLAUDE.md` | Project-wide guardrails and data governance rules. Non-negotiable. |
| `Copy_SKILL.md` | The style guide the copy generation model reads as its system prompt. |
| `CLEVERTAP_CAMPAIGN_SETUP_SKILL.md` | The 12-grid template structure, deeplinks, CleverTap-specific composition rules. |
| `CLEVERTAP_PLATFORM_REFERENCE.md` | API endpoints, auth, rate limits, async polling. |
| `CREW_M_MASTER_CT_BIBLE.md` | Segment definitions, event schema, suppression rules, funnel anchors. |
| `PLUM_ADOPTION_PRODUCT_CONTEXT.md` | Product descriptions (TH, HC, Mental Health, GMC) for campaign angle selection. |
| `CREW-M-CAMPAIGN-PLAYBOOK.md` | The pipeline documentation. |
| `EMAIL-DESIGN-PLAYBOOK.md` | Figma file keys, template production procedure. |
| `KNOWN_ISSUES.md` | Load-bearing problems the next engineer must know about. |
| `CAMPAIGN-BOT-PLAN.md` | This document. |

Three files to create as the build proceeds:

- `BOT_SYSTEM_PROMPT.md` - the Slack bot's system prompt, lifted out of code.
- `AUDIENCE_RULES.md` - the canonical, machine-readable suppression rules.
- `BOT_RUNBOOK.md` - operational guide for the PMM reviewing drafts.

---

## 3. The pipeline

A single run, start to finish.

```
HR admin / AM in Slack
    |
    | 1. slash command or mention, e.g. "/campaign hc-reminder Acme"
    v
Slack webhook -> our Vercel endpoint
    - verify X-Slack-Signature using the signing secret
    - acknowledge within 3 seconds
    |
    | 2. parse the request into {campaignType, orgName, product, ...}
    |    unknown fields asked back in Slack, one at a time
    v
Audience resolution
    |
    | 3. construct the CleverTap segment:
    |      - base: event or org membership relevant to the campaign
    |      - AND warehouse_production_removed != true
    |      - AND warehouse_production_isTestOrganisation != true
    |      - AND is_in_DND_CT != true
    |      - AND campaign-specific filters
    |    reach via /1/counts/profiles.json with estimate_only
    |    check against the org's known headcount, refuse if more than 2x off
    v
Fetch client logo (if co-branding)
    |
    | 4. look up org -> logoUrl from the account facts store
    |    missing logo blocks the request pending HR upload
    v
Generate copy
    |
    | 5. one Claude call with Copy_SKILL.md as system prompt and
    |    verified policy facts for the organisation
    |    returns {subject, body} as JSON, passes the word-count floor
    v
Assemble HTML
    |
    | 6. load the template for this campaign type from email-templates/
    |    substitute the slots (subject, body, CTA, banner, logo)
    v
Create draft in CleverTap
    |
    | 7. POST /1/targets/create.json
    |      - target_mode: email
    |      - segment: saved segment ID (not an inline where clause, see §5)
    |      - content: full HTML body
    |      - when: omitted on purpose, this saves as draft
    v
Post to the PMM Slack channel
    |
    | 8. message with: requester, segment size, campaign ID, deep link to
    |    the CleverTap draft, campaign type
    v
PMM reviews in CleverTap, clicks Publish there
    |
    | CleverTap sends. We never call send ourselves.
    v
Delivery tracking in CleverTap's own campaign reports.
```

Three notes on this flow:

- Step 3's suppression filters are mandatory. Every campaign, no exceptions.
  New campaign types that want to opt out of any filter require a PMM override
  with a logged reason, not a configuration flag.
- Step 6's HTML must be verified as acceptable by CleverTap's campaign API
  before anything else is built. See §4 and §6.
- Step 8's "approve" affordance in Slack is a notification plus an audit chip.
  The real approval action is the human clicking Publish inside CleverTap.

---

## 4. Email composition: the real architecture choice

Three options, honestly compared.

### Option A: Reusable blocks defined in CleverTap, bot triggers

CleverTap exposes reusable content blocks in its editor. There is no API to
fetch or inject them from outside, so the bot could not compose - only trigger
pre-built campaigns with a small number of variable swaps (recipient first name,
one deeplink, one banner URL).

- Pros: no HTML to maintain in the codebase, CleverTap's editor renders
  everything correctly in test sends.
- Cons: the bot cannot vary structure per campaign type, co-branding is a
  URL swap per campaign, rules out dynamic campaign content.
- Verdict: adequate for 3-4 highly standardised campaign types, inadequate as
  a general tool.

### Option B: Figma as the composition source

A Figma file holds every template. A server-side process renders a specific
template with the client logo and body copy substituted, exports PNG, uploads,
sends.

- Pros: highest visual quality, matches brand exactly, co-branding is fully
  automated.
- Cons: Figma has no server-side execution path. Standing this up requires
  rebuilding the Figma pipeline against Puppeteer-rendered HTML templates and
  a server-side image compositing library, worth 2-3 weeks on its own.
- Verdict: the right end state, not a realistic first version.

### Option C (recommended): HTML templates in the repo, bot swaps slots

A small set of HTML templates in `email-templates/`, one per campaign type.
Each template has clearly-marked substitution slots. The bot does Mustache-style
substitution, uploads any new assets to the existing asset bucket, and POSTs the
finished HTML into CleverTap.

- Pros: server-friendly, no Figma dependency at send time, templates
  version-controlled and reviewed in pull requests, logos swap by changing one
  URL, new campaign types require a designer to produce the HTML (which is a
  feature, not a limitation - every new template gets design review).
- Cons: subtler design than Figma offers, new types require designer work.
- Verdict: this is what we ship.

Figma stays as the tool Oshin uses to produce new templates for the repo. It
does not run per send.

**Co-branding** uses one logo slot in the template header. Bot looks up
`accountFacts[orgId].logoUrl`. If present, substitute. If absent, Slack message
to HR: "No logo on file for Acme, please upload or confirm an un-cobranded send."

**Footers** are fixed in every template. The bot never touches them.

---

## 5. The CleverTap targeting issue

Documented in detail in `KNOWN_ISSUES.md`. Summary here, because every piece of
the build must respect it.

A narrow `equals` filter on a CleverTap profile property has been observed to
be silently ignored and return reach equal to the full user base, in both the
API and the dashboard UI. For an automated campaign bot this is a severity-one
issue: a 12-recipient campaign could land in 680,000 inboxes.

**Mandatory mitigations, enforced in code**:

1. Open a support ticket with the CleverTap CSM, attach the evidence from
   `KNOWN_ISSUES.md`, track to resolution.
2. Until the bug is fixed, segments are built by hand in the CleverTap dashboard,
   validated there, and referenced from the API by saved segment ID. The bot
   never constructs a one-shot inline segment definition.
3. Every campaign-create call runs `estimate_only` first against the same
   segment. The code refuses to proceed if the estimate exceeds 2x the org's
   known headcount.
4. Hard caps per campaign type, in code: HR nudges cap at 10,000; welcomes at
   50,000; anything beyond requires explicit PMM override with a logged reason.

These four together are the gate between the bot and a newsworthy incident.

---

## 6. Infrastructure

**App surface**: Next.js on Vercel. The project already runs here, so this is
chosen for continuity, not for any special fit. Vercel is well suited to short
request-and-response work (an incoming Slack call, a reach check, a CleverTap
draft creation). Any long-running job (bulk fan-out, scheduled sweeps) runs
through CleverTap's own infrastructure rather than ours.

**Data**: Supabase. Stores the campaign request record, approval state, PMM
decision log. The authoritative client-fact source for policy terms and logos
is a dedicated table loaded from the warehouse on a daily cadence via Vercel
Cron.

**Sending**: CleverTap. All sends happen through CleverTap drafts that a PMM
publishes manually. Delivery tracking, frequency caps and unsubscribe handling
are inherited from the platform; we do not implement any of them ourselves.

**Scheduling**: Vercel Cron for the daily warehouse sync. Nothing else.

**Secrets**: environment variables only, injected per environment. No secret
value ever appears in the repository.

---

## 7. Security

Three hard requirements, in severity order, each a precondition for live
traffic.

### 7.1 Authentication on every campaign route

Every route under `/api/campaign/*` requires either a valid Supabase session
cookie (for PMM dashboard access) or a verified Slack signature (for bot
triggers). An unauthenticated request receives 401 with no body. No campaign
route is callable anonymously.

### 7.2 Slack webhook signature verification

Every `POST` from Slack carries an `X-Slack-Signature` header. The bot computes
HMAC-SHA256 over the raw request body using the signing secret and compares
against the header in constant time. Mismatch returns 401. Timestamp older than
five minutes also returns 401, to prevent replay. Standard pattern, ten lines
of code.

### 7.3 No sensitive data in the repository

Member data, client contract terms, staff email lists and policy records come
from Supabase or the warehouse at runtime. The repository holds code, templates,
and documentation. It does not hold data.

---

## 8. Build sequence

Phased in order of what must come first, not calendar days.

**Phase 0 - security floor (half day, non-negotiable):**
Authentication on every campaign route. Slack signature verification. No further
work on this project ships without these in place.

**Phase 1 - the architecture test (half day):**
Build one minimum CleverTap draft via API. Post a complete HTML body to
`/1/targets/create.json`, confirm the draft appears in the dashboard, confirm
it renders correctly in a test send. If this passes, Option C in §4 is viable
and the rest of the plan proceeds. If it fails, we rescope around what the API
accepts.

**Phase 2 - the audience resolver (1-2 days):**
The function that takes a campaign brief and returns a validated segment ID.
Standard suppression filters, `estimate_only` sanity check, hard caps per
campaign type. This is the most important code in the system. Written with
tests.

**Phase 3 - template substitution (1-2 days):**
Three starter templates in `email-templates/`: HC reminder, HRA, dependant
reminder. Mustache-style substitution. Logo compositing via `sharp` on a
serverless function. HTML output verified pixel-for-pixel against a reference.

**Phase 4 - integration (2 days):**
Wire the pipeline end to end. Slack signature verification. Copy generation
against the real system prompt. Draft creation in CleverTap. PMM notification
with the deep link.

**Phase 5 - one real campaign, one real client, test audience (1 day):**
Pick a campaign type and a client. Run the pipeline end to end. Audience of 1:
the requester's own email. PMM publishes from CleverTap. Delivery confirmed.
This is the "done" moment.

Total: around 7 working days of focused build, contingent on Phase 1.

---

## 9. What this doesn't try to be

- Not AI-generated creative. Templates are hand-designed. Claude writes body
  copy that fills them.
- Not real-time dashboard analytics. Delivery stats live in CleverTap's own
  reporting.
- Not multi-channel. Email in v1. Push and WhatsApp are the same pattern,
  separate scope.
- Not autonomous. Every draft is reviewed by a PMM before publish.
- Not self-service for every org. Rolling out beyond the pilot clients is a
  conversation about trust and permissions.

---

## Appendix - the three new MD files

### A1. `BOT_SYSTEM_PROMPT.md`

The Slack bot's system prompt lives as a reviewable markdown file, loaded at
build time by the Slack chat handler. Easier to iterate on, easier for the copy
team to edit without touching code.

### A2. `AUDIENCE_RULES.md`

The canonical list of standard filters, machine-readable. Imported by the
audience resolver as data. A change to the rules is a one-line edit to this
file, reviewable in isolation.

Shape:

```yaml
standard_filters:
  - name: Removed members
    property: warehouse_production_removed
    operator: not_equals
    value: true
    applies_to: all
  - name: Test organisations
    property: warehouse_production_isTestOrganisation
    operator: not_equals
    value: true
    applies_to: all
  - name: Do Not Disturb
    property: is_in_DND_CT
    operator: not_equals
    value: true
    applies_to: all
  - name: Quiet hours
    kind: scheduling
    forbid_sends_between: ["21:00", "09:00"]
    tz: Asia/Kolkata
caps_by_type:
  hr_nudge: 10000
  welcome: 50000
  renewal: 50000
```

### A3. `BOT_RUNBOOK.md`

What a PMM does when they see a draft notification in Slack. What to check in
the CleverTap preview before publishing. How to reject a draft. What to do if
the audience estimate looks wrong. The humans in the loop need a playbook.

---

End of plan.
