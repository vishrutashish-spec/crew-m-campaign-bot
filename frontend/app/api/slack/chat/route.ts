import { NextResponse } from "next/server";

const BASE_URL = "https://iw-crew-m-c4b9.insurwreck.com";

interface ChatRequest {
  slackUser: string;
  slackChannel: string;
  threadTs?: string;
  text: string;
}

interface AgentReply {
  action: "reply" | "draft";
  text?: string;
  amName?: string;
  accountName?: string;
  campaignType?: string;
  /** One-sentence free-text description of intent, for anything beyond a
   *  plain welcome/renewal request — carried through to copy generation. */
  campaignBrief?: string;
  logoUrl?: string;
  /** Only set for campaignType "hra", and only if the AM named a specific
   *  angle by name. Omitted -> rotates deterministically. */
  narrative?: string;
  /** True for a literal pipeline/deliverability test — skips copy generation
   *  entirely and sends campaignBrief verbatim, unbranded, as the body. */
  plain?: boolean;
  /** Only set if the AM explicitly named a recipient. Omitted -> safe default. */
  sendTo?: { segmentId?: string; segmentName?: string };
}

const SYSTEM_PROMPT = `You are Crew M's campaign assistant. Someone just tagged you in a Slack channel — your job is to gather what's needed to draft a client email campaign, then hand it off for drafting.

Gather these, ONE question at a time, in this order:

1. The AM's name. You are usually told this already (see the identity note
   appended below this prompt) — if so, do NOT ask for it, just use it.
   Only ask if you genuinely don't know it.
2. Which client account/company the campaign is for.
3. What campaign they want to run, in their own words.

For step 3, figure out what this actually is:
- "Welcome" (a brand-new client's first benefits email) and "Renewal" (an
  existing client renewing their plan) are the two standard types —
  use campaignType "welcome" or "renewal" for these, campaignBrief "".
- "HRA" (Health Risk Assessment — also called "health assessment" or "health
  score") is its OWN exact campaignType: use campaignType "hra" — lowercase,
  exactly those three letters, nothing appended (not "health-risk-assessment"
  or any other slug) — this exact string is what routes it to the real,
  hand-written HRA copy instead of a generated one. Recognise it whenever the
  AM mentions HRA, "health risk assessment," or "health assessment" as the
  campaign itself. The copy for this is pre-written, not generated, so
  campaignBrief can just be a short note of who it's for. If the AM names a
  specific angle for it (one of: curiosity, early-detection, personalization,
  social-proof, free, self-id, myth-busting, anecdote, minimalist), set
  "narrative" to that exact key; otherwise omit "narrative" entirely and it
  rotates automatically.
- Plum also runs targeted activation nudges, e.g. Health Checkup (getting
  employees to use the free annual checkup already in their plan — the
  right angle is always first-time activation of the one they already have,
  never "book it again") or Telehealth (reminding employees that doctor
  consultations are already covered). If the AM describes something like
  this, recognise it, use a short kebab-case campaignType (e.g.
  "health-checkup", "telehealth"), and write a one-sentence campaignBrief
  summarising exactly what they asked for — who it's for and what action
  it's driving. This gets used downstream to write the actual copy, so make
  it specific, not generic.
- If the AM is asking for a literal pipeline or deliverability test — NOT a
  real campaign — recognise that explicitly. Signs of this: "send a test
  email," "just send one that says X," "check the pipeline/send flow
  works," or similar. Do NOT try to write marketing copy for this: there is
  no real benefit or action to build a case around, and inventing one to
  fit the usual structure produces a fake campaign, which is worse than a
  short email. Instead use campaignType "test", set "plain" to true, and
  put the exact wording they asked for as campaignBrief verbatim (if they
  didn't give exact wording, use "This is a test email from Crew M. Please
  ignore." as campaignBrief). This skips copy generation and sends
  campaignBrief as-is, unbranded — appropriate for a test, wrong for a real
  campaign, so only use it when it's genuinely a test.
- For anything else, don't block them: use a short kebab-case slug for
  campaignType and write the clearest one-sentence campaignBrief you can
  from what they told you. Ask ONE clarifying question first only if their
  description is genuinely too vague to act on (just "a campaign", nothing
  else) — otherwise proceed with your best understanding of what they said.

Ask short, direct questions — one at a time, not a list. Don't explain your
reasoning. Don't use markdown headers.

Audience is resolved by the PMM in CleverTap after the draft is created. You
do not pick recipients. If the AM explicitly names a CleverTap segment (e.g.
"the HC-eligible-never-booked segment"), capture it:
  "sendTo": {"segmentName": "<the segment name they said>"}
Otherwise omit sendTo entirely and the PMM will attach the correct segment
during review.

Once you have the AM's name, the account name, and the campaign type/intent,
respond with ONLY this JSON (no other text):
{"action":"draft","amName":"...","accountName":"...","campaignType":"welcome|renewal|hra|test|<slug>","campaignBrief":"...","logoUrl":"...","narrative":"...","sendTo":{"segmentName":"..."}}
("narrative", "plain" and "sendTo" are all optional — include each only per the rules above.)

Until then, respond with ONLY this JSON (no other text):
{"action":"reply","text":"your next message to the AM"}

Never output anything other than one of those two JSON shapes.`;

async function slackApi(token: string, method: string, body: Record<string, unknown>) {
  // Slack's "read" methods (conversations.replies, conversations.history,
  // users.info) reject a JSON body outright on this workspace/token —
  // confirmed live: identical params sent as JSON get "invalid_arguments:
  // missing required field: channel/ts", while form-encoding the exact same
  // params succeeds. chat.postMessage tolerates JSON fine, but form-encoding
  // works for every method (Slack requires nested values like `blocks` to be
  // JSON-stringified into a single form field), so use it everywhere rather
  // than special-case by method.
  const form = new URLSearchParams();
  for (const [key, value] of Object.entries(body)) {
    if (value === undefined || value === null) continue;
    form.set(key, typeof value === "string" ? value : JSON.stringify(value));
  }
  const res = await fetch(`https://slack.com/api/${method}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    },
    body: form,
  });
  return res.json();
}

// Our own fallback text from a previous bad turn — if this got posted to
// Slack, exclude it from history so it doesn't compound confusion.
const FALLBACK_MARKER = "lost my train of thought";

/** Who tagged the bot, read straight from their Slack profile — so the AM is
 *  never asked for their own name when Slack already knows it. */
async function resolveSlackName(token: string, userId: string): Promise<string | null> {
  const data = await slackApi(token, "users.info", { user: userId });
  if (!data.ok) return null;
  const profile = data.user?.profile ?? {};
  return profile.real_name || data.user?.real_name || profile.display_name || null;
}

async function getRecentHistory(
  token: string,
  channel: string,
  threadTs: string | undefined
): Promise<Array<{ role: "user" | "assistant"; content: string }>> {
  const data = threadTs
    ? await slackApi(token, "conversations.replies", { channel, ts: threadTs, limit: 20 })
    : await slackApi(token, "conversations.history", { channel, limit: 20 });

  if (!data.ok) return [];

  const messages: Array<{ role: "user" | "assistant"; text: string; ts: string }> = (
    data.messages ?? []
  )
    // Drop join/leave/rename/etc system messages — they have a `subtype`
    // and aren't real conversation turns.
    .filter((m: { subtype?: string }) => !m.subtype)
    .map((m: { bot_id?: string; text?: string; ts: string }) => ({
      role: m.bot_id ? ("assistant" as const) : ("user" as const),
      text: m.text ?? "",
      ts: m.ts,
    }))
    .filter((m: { text: string }) => m.text && !m.text.includes(FALLBACK_MARKER));

  // History comes back newest-last for threads, newest-first for channel history.
  const ordered = threadTs ? messages : [...messages].reverse();
  return ordered.map((m) => ({ role: m.role, content: m.text }));
}

async function askClaude(
  history: Array<{ role: string; content: string }>,
  system: string
): Promise<string> {
  const apiKey = process.env.ANTHROPIC_API_KEY;
  const apiBase = process.env.ANTHROPIC_API_BASE ?? "https://api.anthropic.com";
  if (!apiKey) throw new Error("anthropic_not_configured");

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
      system,
      messages: history.map((m) => ({ role: m.role, content: m.content })),
    }),
  });

  if (!res.ok) throw new Error(`anthropic_error_${res.status}`);
  const data = await res.json();
  const blocks: Array<{ type: string; text?: string }> = data?.content ?? [];
  return blocks.find((b) => b.type === "text")?.text ?? "{}";
}

async function callClaude(
  history: Array<{ role: string; content: string }>,
  system: string
): Promise<AgentReply | null> {
  for (let attempt = 0; attempt < 2; attempt++) {
    const prompt =
      attempt === 0
        ? history
        : [
            ...history,
            {
              role: "user",
              content: "(Reminder: reply with ONLY the JSON object, nothing else.)",
            },
          ];
    const text = await askClaude(prompt, system);
    try {
      return JSON.parse(text) as AgentReply;
    } catch {
      // retry once
    }
  }
  // Both attempts failed to produce valid JSON. Don't post a confusing
  // "I forgot everything" message — that just pollutes history further.
  // Stay silent this turn; the user's next message tries again with full context.
  return null;
}

export async function POST(request: Request) {
  const { slackUser, slackChannel, threadTs, text } = (await request.json()) as ChatRequest;

  const token = process.env.SLACK_BOT_TOKEN;
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!token) {
    return NextResponse.json({ ok: false, error: "slack_not_configured" }, { status: 500 });
  }

  const [history, knownName] = await Promise.all([
    getRecentHistory(token, slackChannel, threadTs),
    resolveSlackName(token, slackUser),
  ]);
  history.push({ role: "user", content: text });

  const identityNote = knownName
    ? `\n\nIdentity note: the person you're talking to (Slack ID <@${slackUser}>) is named "${knownName}" per their Slack profile — use this as their name, do not ask them what their name is.`
    : `\n\nIdentity note: this person's Slack profile name could not be resolved. If this is the start of the conversation, your first message must ask for their name before anything else.`;

  const reply = await callClaude(history, SYSTEM_PROMPT + identityNote);

  if (!reply) {
    return NextResponse.json({ ok: false, error: "no_valid_reply" });
  }

  if (reply.action === "reply") {
    await slackApi(token, "chat.postMessage", {
      channel: slackChannel,
      thread_ts: threadTs,
      text: reply.text ?? "Sorry, could you rephrase that?",
    });
    return NextResponse.json({ ok: true, action: "reply" });
  }

  // action === "draft": run the existing pipeline against our own API.
  const requestId = `chat-${Date.now()}`;
  const { amName, accountName, campaignType, campaignBrief, logoUrl, narrative, plain } = reply;

  const sendTo = reply.sendTo;

  // A literal test send has no real benefit to write a campaign about —
  // skip the copy model entirely rather than asking it to invent one.
  // (Asking it to anyway is exactly what produced a multi-paragraph refusal
  // that then got sent verbatim as the "campaign" body.)
  const copy = plain
    ? { subject: `Test — ${accountName}`, body: campaignBrief || "This is a test email from Crew M. Please ignore." }
    : await fetch(`${BASE_URL}/api/copy`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requestId, amName, accountName, campaignType, campaignBrief, logoUrl, narrative }),
      }).then((r) => r.json());

  const creative = plain
    ? { creativeUrl: "", stub: true }
    : await fetch(`${BASE_URL}/api/creative`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requestId, copy }),
      }).then((r) => r.json());

  const draft = await fetch(`${BASE_URL}/api/campaign/draft`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requestId, amName, accountName, campaignType, campaignBrief, copy, creative, plain, sendTo }),
  }).then((r) => r.json());

  // Tag the saved record with where it came from, so the PMM's approve/reject
  // decision (posted by /api/campaign/draft, which is the one place both this
  // chat bot and the modal flow funnel through) can notify the right person.
  if (draft.id && supabaseUrl && supabaseKey) {
    await fetch(`${supabaseUrl}/rest/v1/campaign_requests?id=eq.${draft.id}`, {
      method: "PATCH",
      headers: {
        apikey: supabaseKey,
        Authorization: `Bearer ${supabaseKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        slack_channel: slackChannel,
        slack_thread_ts: threadTs ?? null,
      }),
    }).catch(() => {});
  }

  const sendToNote = sendTo?.segmentName
    ? ` It'll target the \`${sendTo.segmentName}\` segment once the PMM publishes it in CleverTap.`
    : "";

  await slackApi(token, "chat.postMessage", {
    channel: slackChannel,
    thread_ts: threadTs,
    text: `Got it — drafting the ${campaignType} campaign for ${accountName} now.${sendToNote} I'll ping the PMM channel for approval and let you know what happens.`,
  });

  return NextResponse.json({ ok: true, action: "draft", id: draft.id });
}
