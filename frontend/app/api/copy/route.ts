import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

interface GenerateCopyRequest {
  requestId: string;
  amName: string;
  accountName: string;
  campaignType: "welcome" | "renewal" | string;
  /** Free-text description of intent for anything that isn't welcome/renewal, e.g.
   *  "nudge employees who haven't used their free annual health checkup yet". */
  campaignBrief?: string;
  logoFileId?: string;
  logoUrl?: string;
  slackUser?: string;
  /** Pick a specific HRA narrative by key; omitted rotates deterministically. */
  narrative?: string;
}

const COPY_SKILL_PATH = path.join(process.cwd(), "lib", "prompts", "copy-skill.md");

/**
 * Messaging angles for known Plum products, distilled from
 * PLUM_ADOPTION_PRODUCT_CONTEXT.md and CREW_M_MASTER_CT_BIBLE.md so a
 * non-welcome/renewal request (e.g. "health checkup campaign") still gets
 * product-accurate framing instead of a generic guess. Matched by substring
 * against the AM's own words, since the bot doesn't force them into an enum.
 */
const PRODUCT_ANGLES: Array<{ match: RegExp; angle: string; deeplink: string }> = [
  {
    match: /health\s*-?\s*check\s*-?up|\bhc\b/i,
    angle: `This is a Health Checkup activation nudge, NOT a renewal or welcome email.
Most plans give one free checkup per year; once used, there's no urgency to
rebook, so the right angle is FIRST-TIME activation of the free checkup
already sitting in their plan — never "book your checkup again" framing.
Lead with something like "you still haven't used the one already in your
plan," not a generic wellness pitch. Mention it's free (already included,
not something to buy), quick, and covers biomarker screening. Do not invent
package names or turnaround times.`,
    deeplink: "https://deeplink.plumhq.com/home?screen=hc",
  },
  {
    match: /tele\s*-?\s*health|\bth\b|doctor\s*consult|teleconsult/i,
    angle: `This is a Telehealth activation nudge. The angle is "help is one call
away" — unlimited doctor consultations are already part of their plan.
Emphasise speed and availability (no appointment needed, general physicians
and specialists), not urgency or scarcity.`,
    deeplink: "https://deeplink.plumhq.com/care",
  },
];

function lookupProductAngle(text: string) {
  return PRODUCT_ANGLES.find((p) => p.match.test(text)) ?? null;
}

export async function POST(request: Request) {
  const { requestId, amName, accountName, campaignType, campaignBrief, logoUrl, narrative } =
    (await request.json()) as GenerateCopyRequest;

  const normalizedType = String(campaignType).toLowerCase();
  const isStandard = normalizedType === "welcome" || normalizedType === "renewal";

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    console.error("ANTHROPIC_API_KEY is not set — cannot generate copy");
    return NextResponse.json({ error: "anthropic_not_configured" }, { status: 500 });
  }

  const copySkill = fs.readFileSync(COPY_SKILL_PATH, "utf-8");

  // Account facts come from a verified source at runtime (a database lookup
  // backed by the warehouse). This endpoint does not read any such lookup
  // today; until it does, the "no verified facts" branch below always runs,
  // which writes a correct email without inventing specifics. Wire a real
  // lookup here when the facts table is ready.
  const facts = null as { coverStart?: string } | null;
  const isRenewal = normalizedType === "renewal";

  // Policy year label for the subject, e.g. "2026-27", derived from the
  // cover start rather than today, so a future-dated policy reads correctly.
  const startYear = facts?.coverStart
    ? Number((facts.coverStart.match(/\b(20\d{2})\b/) ?? [])[1])
    : new Date().getFullYear();
  const yearLabel = `${startYear}-${String((startYear + 1) % 100).padStart(2, "0")}`;

  const knownFacts = `No verified policy data is on file for this account. Write
every section below, but state NO insurer name, date, sum insured, maternity
limit, copay or any other specific. Where a specific belongs, write that the
detail will follow shortly. Never invent a figure and never write a placeholder
like "[insurer]".`;

  const userPrompt = isStandard ? `Write the body copy for a ${isRenewal ? "RENEWAL" : "WELCOME"} benefits email to employees of "${accountName}".
Requested by account manager ${amName}.

${knownFacts}

This is a real member-facing benefits email and must match Plum's production
format. Those emails are long and specific: an employee should be able to act
on it without asking anyone a question. Aim for 400-550 words. A short email is
a failure.

Use EXACTLY these sections, in this order, each heading on its own line:

1. Opening, two sentences. ${isRenewal
    ? `Say ${accountName} has RENEWED its partnership with Plum to continue bringing a best-in-class healthcare experience.`
    : `Say ${accountName} has partnered with Plum to bring a best-in-class healthcare experience.`}
   Describe it as comprehensive, simple, inclusive and easy to access for them
   and their loved ones.
2. One or two sentences naming the insurer as the trusted insurance partner and
   what that means for service and support. Only if the insurer is known.
3. "Here's when it starts:" then the ${isRenewal ? "renewed " : ""}coverage start date on the next line.
4. "Here's what you need to know:" with bullets starting "- ":
   - Coverage for the employee and their family begins on the start date, and
     health cards will be available in the Plum app shortly
   - Emergency assistance or a cashless claim without a health ID yet: call
     Plum's 24/7 helpline at 1800 30 911 911. Missed calls returned within 15 minutes
   - For cashless treatments, visit a network hospital. The network hospital
     list is in the Plum app
   - For non-network treatments, file a reimbursement claim in the Plum app once
     health IDs arrive
5. "Note:" then a line about reimbursement claims incurred BEFORE the coverage
   start date: submit documents through the Plum app under the previous policy,
   and the Claims Support team will review and guide them. ${isRenewal ? "" : "Include this only if a start date is known."}
6. "Next steps:" a Plum enrollment invite is coming, to sign up, review details
   and dependents, and enroll in the group insurance program.
7. "More updates to follow, stay tuned!" on its own line.
8. "Here's what you're covered for:" then these as separate lines, only the ones
   known: plan name, "Sum Insured: Graded", "Family definition: ...",
   "Insurer: ... | TPA: ...", "Start Date of Coverage: ...".
9. "Health Insurance Benefits for ${yearLabel}:" with bullets for maternity limit,
   pre and post natal expenses, baby day-one coverage, ambulance charges, LASIK
   and Ayush. Include ONLY limits given in the verified facts. If none are
   given, omit this whole section rather than inventing any.
10. A line saying complete coverage details are on the Plum app, where they can
    view detailed benefits, coverage limits and applicable policy terms.
11. "Reaching out to Plum:" with bullets for in-app support (Plum app or web
    dashboard, 24x7), email support (care@plumhq.com, 9am to 9pm, seven days a
    week), and emergencies without health cards (1800 30 911 911, 24x7, cashless
    only at network hospitals).
12. A short closing, two or three sentences, on its own after the support
    section. ${isRenewal
      ? `Thank ${accountName} employees for continuing with Plum and say the team is glad to keep looking after them.`
      : `Welcome them to Plum once more and say the team is glad to have them on board.`}
    Warm and plain. No heading above it, no bullets, no call to action, and do
    not repeat the helpline or email address again here.

Hard rules:
- SUM INSURED IS WRITTEN AS "Graded" AND NOTHING ELSE. Never list the per-grade
  amounts. A whole organisation reads this email and the grades differ per person.
- No em dashes anywhere.
- No "not X, but Y" negation contrasts.
- No ", so you know X" tails.
- Never invent a statistic, limit, date or hospital count.
- Spell out acronyms on first use. Never write GMC, GTL, GPA or HRA bare.
- No jokes, no personification, no wit.

Respond with ONLY a raw JSON object (no markdown fences, no commentary):
{"subject": "...", "body": "..."}

The subject must be EXACTLY this, with nothing added or removed:
Welcome to Your ${yearLabel} Health Benefits 🎉${accountName}<> Plum`
    : (() => {
        const brief = (campaignBrief ?? "").trim();
        const angle = lookupProductAngle(`${campaignType} ${brief}`);
        return `Write the body copy for a targeted benefits-engagement email to
employees of "${accountName}" who already have a Plum plan. This is NOT a
welcome or renewal email — do not use either of those framings.
Requested by account manager ${amName}.

What the AM asked for, in their own words: "${brief || campaignType}"

${angle ? angle.angle : `No specific Plum product angle is recognised from that
description. Infer the single clearest benefit or action being promoted from
the AM's own words above, and write toward that one thing only — do not pad
with unrelated benefits.`}

${knownFacts}

Aim for 200-280 words — this is a short, single-purpose nudge, not a full
onboarding email, but it must clear 150 words with real margin (a send-time
gate rejects anything shorter). It should read as one clear ask, not a
benefits directory — pad with specific, relevant detail, never filler.

Structure:
1. A one-line hook naming the specific action or benefit (not a generic
   greeting).
2. Two to three sentences of body copy making the case for taking the action,
   in Plum's voice — concrete, no filler.
3. "Here's how:" with 2-4 short bullet steps to do it in the Plum app.
4. One closing line reinforcing why now (only if there's a genuine reason —
   never invent urgency or a deadline that wasn't supplied).

Hard rules:
- No em dashes anywhere.
- No "not X, but Y" negation contrasts.
- No ", so you know X" tails.
- Never invent a statistic, limit, date, price or deadline.
- Spell out acronyms on first use. Never write GMC, GTL, GPA or HRA bare.
- No jokes, no personification, no wit.

Respond with ONLY a raw JSON object (no markdown fences, no commentary):
{"subject": "...", "body": "..."}

The subject line should be short (under 60 characters), specific to the one
action being promoted, and end with "${accountName}<> Plum".`;
      })();

  const apiBase =
    process.env.ANTHROPIC_BASE_URL ??
    process.env.ANTHROPIC_API_BASE ??
    "https://api.anthropic.com";

  // The model thinks before answering — a low budget can burn the whole
  // response on the (discarded) thinking block and return no text block at
  // all, which then parses as "{}" and silently ships an empty campaign
  // rather than erroring. Confirmed live for a health-checkup request even
  // at 8192. Retry once before giving up, since it doesn't reproduce every
  // time for the same prompt.
  let text = "{}";
  for (let attempt = 0; attempt < 2; attempt++) {
    const res = await fetch(`${apiBase}/v1/messages`, {
      method: "POST",
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        model: "claude-sonnet-5",
        max_tokens: 8192,
        system: copySkill,
        messages: [{ role: "user", content: userPrompt }],
      }),
    });

    if (!res.ok) {
      const errText = await res.text();
      console.error("Anthropic request failed", res.status, errText);
      if (attempt === 1) return NextResponse.json({ error: "copy_generation_failed" }, { status: 502 });
      continue;
    }

    const data = await res.json();
    const blocks: Array<{ type: string; text?: string }> = data?.content ?? [];
    const found = blocks.find((b) => b.type === "text")?.text;
    if (found) {
      text = found;
      break;
    }
    console.error("Anthropic response had no text block on attempt", attempt, JSON.stringify(data).slice(0, 500));
  }

  let parsed: { subject?: string; body?: string };
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = { subject: `${campaignType} — ${accountName}`, body: text };
  }

  // A short or malformed generation must never reach a member's inbox. The
  // model occasionally returns an empty or truncated text block (it thinks
  // before answering, and a bad run can spend the budget on that), which
  // previously shipped as a 6-word email. Fail loudly instead.
  const finalBody = (parsed.body ?? "").trim();
  const wordCount = finalBody ? finalBody.split(/\s+/).length : 0;
  const MIN_WORDS = 150;
  if (wordCount < MIN_WORDS) {
    console.error(
      `copy generation too short for ${accountName}: ${wordCount} words (min ${MIN_WORDS})`,
      JSON.stringify({ rawPreview: text.slice(0, 300) })
    );
    return NextResponse.json(
      { error: "copy_too_short", words: wordCount, minimum: MIN_WORDS },
      { status: 502 }
    );
  }

  return NextResponse.json({
    requestId,
    accountName,
    campaignType,
    subject: parsed.subject ?? `${campaignType} — ${accountName}`,
    body: finalBody,
  });
}
