import { NextResponse } from "next/server";

/**
 * Slack approve/reject button handler.
 *
 * In the target architecture, approval marks the campaign request as approved
 * in Supabase and prompts the PMM to open the CleverTap draft and publish it
 * there. This service does not send email itself; CleverTap does, after a
 * human clicks Publish inside its dashboard.
 *
 * Rejection marks the row as rejected and posts a message so the requesting
 * AM knows.
 */

interface InteractionRequest {
  actionId: string;
  campaignId: string;
  approverUserId: string;
  channel: string;
  messageTs?: string;
}

async function slackApi(token: string, method: string, body: Record<string, unknown>) {
  const res = await fetch(`https://slack.com/api/${method}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify(body),
  });
  return res.json();
}

export async function POST(request: Request) {
  const { actionId, campaignId, approverUserId, channel, messageTs } =
    (await request.json()) as InteractionRequest;

  const token = process.env.SLACK_BOT_TOKEN;
  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!token || !supabaseUrl || !supabaseKey) {
    return NextResponse.json({ ok: false, error: "not_configured" }, { status: 500 });
  }

  const approved = actionId === "approve";
  const status = approved ? "approved" : "rejected";

  // Load the row so we can address the requester in the follow-up message.
  const rowRes = await fetch(
    `${supabaseUrl}/rest/v1/campaign_requests?id=eq.${encodeURIComponent(campaignId)}`,
    {
      headers: { apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}` },
    },
  );
  const rows = (await rowRes.json()) as Array<{
    id: string;
    account_name: string;
    campaign_type: string;
    campaign_name?: string;
    subject?: string;
    slack_channel?: string;
    slack_thread_ts?: string;
  }>;
  const row = rows[0];

  // Record the decision.
  await fetch(
    `${supabaseUrl}/rest/v1/campaign_requests?id=eq.${encodeURIComponent(campaignId)}`,
    {
      method: "PATCH",
      headers: {
        apikey: supabaseKey,
        Authorization: `Bearer ${supabaseKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        status,
        approved_by: approverUserId,
        approved_at: new Date().toISOString(),
      }),
    },
  );

  const name = row?.campaign_name ?? campaignId;
  const decisionText = approved
    ? `<@${approverUserId}> approved *${name}*. Open the draft in CleverTap and click Publish to send.`
    : `<@${approverUserId}> rejected *${name}*.`;

  await slackApi(token, "chat.postMessage", {
    channel,
    thread_ts: messageTs,
    text: decisionText,
  });

  if (row?.slack_channel) {
    await slackApi(token, "chat.postMessage", {
      channel: row.slack_channel,
      thread_ts: row.slack_thread_ts || undefined,
      text: approved
        ? `Your ${row.campaign_type} campaign for ${row.account_name} was approved. The PMM will publish it from CleverTap shortly.`
        : `Your ${row.campaign_type} campaign for ${row.account_name} was not approved this time. Ping the PMM channel if you want details.`,
    });
  }

  return NextResponse.json({ ok: true, status });
}
