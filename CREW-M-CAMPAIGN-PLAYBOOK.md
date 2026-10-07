# Crew M - Campaign Email Playbook

The campaign pipeline, as it is being built. Every step runs through CleverTap
as the system of record. Nothing in this document describes "what we do today
and will replace" - this is the target design and the one being built against.

## 1. The pipeline

```
HR admin / AM in Slack
    |
    | 1. structured request (campaign type, org, product)
    v
Slack webhook (signature verified) -> /api/slack/chat
    |
    | 2. parse intent, resolve any missing fields in a conversation
    v
Audience resolution
    |
    | 3. construct CleverTap segment with standard suppression filters
    |    (see AUDIENCE_RULES.md). Call estimate_only, verify count is within
    |    sanity bounds for the org before proceeding.
    v
Copy generation
    |
    | 4. Claude writes body copy using Copy_SKILL.md as system prompt and
    |    verified policy facts for the organisation.
    v
Template assembly
    |
    | 5. HTML template for the campaign type, with substitution slots for
    |    org name, body, CTA, banner, logo. Server-side composition.
    v
CleverTap draft creation
    |
    | 6. POST /1/targets/create.json with the full HTML body, saved as draft
    |    (not scheduled, not sent).
    v
PMM notification in Slack
    |
    | 7. Message to the PMM channel: who requested, segment count, deep link
    |    to the CleverTap draft.
    v
PMM reviews and publishes inside CleverTap
    |
    | Publish happens in CleverTap's own UI. The bot never calls send.
    v
CleverTap sends, tracks delivery, respects frequency caps and unsubscribes.
```

## 2. The approval boundary

Only CleverTap sends. The bot creates drafts. The Publish button stays human.
This is not a convention - it is enforced by what credentials the bot holds.
The CleverTap token used by the bot has permission to create and update a draft
campaign; it does not have permission to publish or schedule one.

## 3. Email structure

Every campaign uses an approved HTML template from `email-templates/`. A template
is a complete, mobile-responsive email with named substitution slots. The bot
never generates HTML from scratch and never modifies the template structure. It
only fills slots.

Slots a template exposes:

- `{{org_name}}` - the client organisation
- `{{recipient_first_name}}` - resolved per recipient by CleverTap, not us
- `{{body_html}}` - the Claude-written body, converted from markdown
- `{{cta_url}}` - deeplink picked from CLEVERTAP_CAMPAIGN_SETUP_SKILL.md
- `{{banner_url}}` - the campaign-type banner, possibly with the client logo
  composited in
- `{{logo_url}}` - the client logo for co-branding, or empty for no co-brand

Footer, unsubscribe link, and legal text are fixed in every template. The bot
does not touch them.

## 4. Co-branding

Co-branding uses one logo slot in the template header. The bot looks up the
client logo from the account facts table. If present, it drops into the slot.
If absent, the bot messages HR to upload the logo or confirm an un-cobranded
send. The bot does not infer or scrape a logo.

Logos must be a transparent PNG with the correct colour variant for a cream
background. Scraping brand websites for a logo is unreliable: many sites block
automated requests, favicon services return icons too small for email, and
public logos are often the wrong colour variant for the context. All logos are
sourced from a reviewed asset store.

## 5. Campaign types

Each campaign type is a separate template plus a separate audience rule set.
Adding a new type requires:

1. A new template HTML file in `email-templates/`
2. A new audience rule entry in `AUDIENCE_RULES.md`
3. A new product-angle entry in the copy route
4. A test send to a dry-run recipient

New types are added by a PMM request, reviewed as a pull request.
