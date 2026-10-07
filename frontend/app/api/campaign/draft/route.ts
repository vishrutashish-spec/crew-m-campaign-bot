import { NextResponse } from "next/server";

interface SendTo {
  /**
   * The CleverTap segment this campaign targets. Must be a saved segment ID
   * from the CleverTap dashboard whose reach has been verified. Inline
   * where-clauses are not accepted here, by design, until the known
   * CleverTap targeting issue is resolved (see KNOWN_ISSUES.md).
   */
  segmentId?: string;
  segmentName?: string;
  estimatedReach?: number;
}

interface BuildDraftRequest {
  requestId: string;
  amName: string;
  accountName: string;
  campaignType: "welcome" | "renewal" | string;
  /** Free-text description of intent, for anything beyond welcome/renewal. */
  campaignBrief?: string;
  copy: { subject?: string; body?: string };
  creative: { creativeUrl?: string; stub?: boolean };
  /** Who this should actually go to once approved. Omit for the safe default. */
  sendTo?: SendTo;
  /** A literal, unbranded test send — copy generation was skipped entirely. */
  plain?: boolean;
}

/**
 * Human-facing label for the PMM approval message — shown so a reviewer sees
 * exactly who a send reaches BEFORE clicking Approve, since the recipient
 * field is now caller-specified rather than hard-locked. Mirrors
 * campaign/send's own resolution but doesn't need to be exact (send does the
 * real validation) — this just has to make the blast radius obvious.
 */
function describeSendTo(sendTo: SendTo | undefined): string {
  if (!sendTo?.segmentId) {
    return "No segment specified. The PMM must verify audience in CleverTap before publishing.";
  }
  const reach = sendTo.estimatedReach;
  const name = sendTo.segmentName ?? sendTo.segmentId;
  if (typeof reach === "number") {
    return `Segment \`${name}\` — ~${reach.toLocaleString()} profiles (verified in CleverTap).`;
  }
  return `Segment \`${name}\`. Verify the current reach in CleverTap before publishing.`;
}

/**
 * Builds a campaign brief and stores it in Supabase. Posts the brief to the
 * PMM Slack channel for review. When the full build is in place, a successful
 * draft here will also create the corresponding draft in CleverTap via the
 * campaign creation API; today it records the request for the PMM to action.
 */
export async function POST(request: Request) {
  const { requestId, amName, accountName, campaignType, campaignBrief, copy, creative, sendTo, plain } =
    (await request.json()) as BuildDraftRequest;

  const channel = "Email";
  const date = new Date().toISOString().slice(0, 10);
  const campaignName = `[${channel}] [${campaignType}] [${accountName}] [${date}] [v1]`;

  const segmentSuggestion =
    campaignType === "welcome"
      ? `New employees at ${accountName} who haven't installed the app or completed an activation event yet`
      : campaignType === "renewal"
      ? `Active employees at ${accountName} whose plan is due for renewal`
      : `Active employees at ${accountName} who haven't yet taken the action this campaign is nudging toward`;

  const summary = [
    `*${campaignName}*`,
    `Requested by: ${amName}`,
    `Channel: ${channel} (default for now — no channel picker yet)`,
    ...(campaignBrief ? [`Brief: ${campaignBrief}`] : []),
    "",
    `*Subject:* ${copy?.subject ?? "(none generated)"}`,
    "*Body:*",
    copy?.body ?? "(none generated)",
    "",
    `*Creative:* ${creative?.creativeUrl ?? "(none)"}${
      creative?.stub ? " — placeholder, Figma rendering isn't wired up yet" : ""
    }`,
    "",
    `*Suggested audience:* ${segmentSuggestion}`,
    "",
    "This is a brief, not a CleverTap draft — CleverTap doesn't expose an API to create campaigns. Paste this into the CleverTap dashboard to create the real draft.",
  ].join("\n");

  const region = process.env.CT_REGION ?? "in1";
  const reviewUrl = `https://${region}.clevertap.com/`;

  const record = {
    am_name: amName,
    account_name: accountName,
    campaign_type: campaignType,
    campaign_brief: campaignBrief ?? null,
    send_to: sendTo ?? null,
    plain: Boolean(plain),
    subject: copy?.subject ?? "",
    body: copy?.body ?? "",
    creative_url: creative?.creativeUrl ?? "",
    creative_is_stub: Boolean(creative?.stub),
    segment_suggestion: segmentSuggestion,
    campaign_name: campaignName,
    review_url: reviewUrl,
  };

  let id: string | null = null;
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (supabaseUrl && supabaseKey) {
    try {
      const insertRes = await fetch(`${supabaseUrl}/rest/v1/campaign_requests`, {
        method: "POST",
        headers: {
          apikey: supabaseKey,
          Authorization: `Bearer ${supabaseKey}`,
          "Content-Type": "application/json",
          Prefer: "return=representation",
        },
        body: JSON.stringify(record),
      });
      if (insertRes.ok) {
        const [row] = await insertRes.json();
        id = row?.id ?? null;
      } else {
        console.error("Supabase insert failed", insertRes.status, await insertRes.text());
      }
    } catch (err) {
      console.error("Supabase insert threw", err);
    }
  }

  // Ask a human before anything real goes out. This is the one place both
  // the chat bot and the /crew-m modal funnel through, so the approval gate
  // applies no matter which path produced the draft.
  const slackToken = process.env.SLACK_BOT_TOKEN;
  const pmmChannel = process.env.SLACK_PMM_CHANNEL_ID;
  if (slackToken && pmmChannel && id) {
    const previewUrl = `https://iw-crew-m-c4b9.insurwreck.com/api/campaign/${id}/preview`;
    await fetch("https://slack.com/api/chat.postMessage", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${slackToken}`,
        "Content-Type": "application/json; charset=utf-8",
      },
      body: JSON.stringify({
        channel: pmmChannel,
        text: `New campaign draft ready for review: ${campaignName}`,
        blocks: [
          {
            type: "section",
            text: {
              type: "mrkdwn",
              text: `*${campaignName}*${plain ? " _(plain/unbranded test send)_" : ""}\nRequested by ${amName}${
                campaignBrief ? `\n*Brief:* ${campaignBrief}` : ""
              }\n\n*Subject:* ${copy?.subject ?? ""}\n\n*Suggested audience:* ${segmentSuggestion}\n\n*Recipients:* ${describeSendTo(sendTo)}\n\n*Preview:* <${previewUrl}|Open the actual email>`,
            },
          },
          {
            type: "actions",
            block_id: "campaign_approval",
            elements: [
              {
                type: "button",
                text: { type: "plain_text", text: "Approve" },
                style: "primary",
                action_id: "approve_campaign",
                value: id,
              },
              {
                type: "button",
                text: { type: "plain_text", text: "Reject" },
                style: "danger",
                action_id: "reject_campaign",
                value: id,
              },
            ],
          },
        ],
      }),
    }).catch((err) => console.error("approval post failed", err));
  }

  return NextResponse.json({
    id,
    requestId,
    campaignName,
    channel,
    amName,
    subject: copy?.subject ?? "",
    body: copy?.body ?? "",
    creativeUrl: creative?.creativeUrl ?? "",
    creativeIsStub: Boolean(creative?.stub),
    segmentSuggestion,
    reviewUrl,
    // Kept for the Slack-reply path, which still expects a flat string.
    summary,
  });
}
