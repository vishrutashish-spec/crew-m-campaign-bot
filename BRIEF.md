# Crew M Campaign Bot - Brief

## What this is

A Slack-triggered pipeline that lets an authorised requester at Plum (an HR
admin at a client, or an internal AM) ask for a campaign in Slack, and get a
reviewed CleverTap draft ready for a PMM to publish.

The complete scope, architecture choices and build sequence live in
`CAMPAIGN-BOT-PLAN.md`. This file is the one-page framing.

## Problem

Setting up a client email campaign today takes a round of DMs, a copy
request, an audience request, a Figma asset request, a CleverTap setup, and a
reach check. The work is slow, repetitive, and error-prone at every handoff.
Nothing links a request to the final send, and there is no record of who
asked, who approved, and what was sent.

## Who it is for

- HR admins at Plum client organisations who need to nudge their own
  employees (dependant reminder, HC checkup, HRA, etc).
- Plum AMs setting up welcomes and renewals.
- Plum PMMs who approve and publish.

## What success looks like

An HR admin asks in Slack for a dependant reminder for their org, and ten
seconds later a correctly-targeted, correctly-branded draft is sitting in the
CleverTap dashboard waiting for a PMM to click Publish. The entire request
is logged with who asked, what segment was resolved, who approved.

## The one hard constraint

Nothing in this pipeline sends email. CleverTap sends, after a human clicks
Publish inside the CleverTap dashboard. The bot's credentials permit creating
and updating drafts, not publishing them.

## Build phases (summary - full detail in CAMPAIGN-BOT-PLAN.md)

0. Security floor: auth every route, verify Slack signatures. Non-negotiable.
1. The architecture test: can CleverTap's campaign-creation API accept our
   full HTML body? Half-day test that decides the rest.
2. Audience resolver: standard suppression filters, estimate-only sanity
   check, hard caps per campaign type. Mitigates the known CleverTap targeting
   issue documented in `KNOWN_ISSUES.md`.
3. Template substitution: HTML templates in the repo, bot fills slots.
4. Pipeline integration: wire Slack trigger -> copy -> template -> CleverTap
   draft -> PMM notification.
5. One real campaign for one real client, test audience of one.

## Out of scope for this build

- Any sending outside CleverTap.
- Auto-approval. Every draft is reviewed by a PMM before publish.
- Self-service for every org. First rollout is to pilot clients.
- Automated creative composition from scratch - templates are hand-designed,
  the bot fills slots.
- Multi-channel. Email first. Push and WhatsApp follow the same pattern in
  later phases.

## Governance

- All secrets in environment variables, never in code.
- All CleverTap queries bounded to a date range, maximum one year.
- No export or download of records anywhere in the interface.
- Every data-access route logs who asked and what for.
- No campaign ever sends without a PMM clicking Publish in CleverTap.
