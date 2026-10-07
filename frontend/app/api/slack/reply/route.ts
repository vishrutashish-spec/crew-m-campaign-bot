import { NextResponse } from "next/server";

interface ReplyRequest {
  channel: string;
  slackUser?: string;
  amName: string;
  accountName: string;
  reviewUrl: string;
  summary: string;
}

async function post(token: string, channel: string, text: string) {
  const res = await fetch("https://slack.com/api/chat.postMessage", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify({ channel, text, unfurl_links: false }),
  });
  return res.json();
}

export async function POST(request: Request) {
  const { channel, slackUser, amName, accountName, reviewUrl, summary } =
    (await request.json()) as ReplyRequest;

  const token = process.env.SLACK_BOT_TOKEN;
  if (!token) {
    console.error("SLACK_BOT_TOKEN is not set — cannot reply in Slack");
    return NextResponse.json({ ok: false, error: "slack_not_configured" }, { status: 500 });
  }

  if (!channel && !slackUser) {
    console.error("No Slack channel or user to reply to for", accountName, amName);
    return NextResponse.json({ ok: false, error: "missing_destination" }, { status: 400 });
  }

  const text = summary
    ? `${summary}\n\n<${reviewUrl}|Open CleverTap>`
    : `Campaign brief ready for ${accountName} (requested by ${amName}). <${reviewUrl}|Open CleverTap>`;

  // Try the originating conversation first so a request made in a team channel
  // is answered there. It can fail for reasons the bot can do nothing about:
  // a DM it is not a member of (chat:write.public only covers public channels),
  // or a private channel it was never invited to. In those cases fall back to
  // DMing the requester — chat.postMessage accepts a user id as `channel` and
  // opens the IM itself.
  let data = channel ? await post(token, channel, text) : { ok: false, error: "no_channel" };

  if (!data.ok && slackUser && ["channel_not_found", "not_in_channel", "no_channel"].includes(data.error)) {
    const first = data.error;
    data = await post(token, slackUser, text);
    if (data.ok) {
      console.warn(`channel ${channel} failed with ${first}; delivered via DM to ${slackUser}`);
      return NextResponse.json({ ok: true, deliveredVia: "dm", channelError: first });
    }
  }

  if (!data.ok) {
    console.error("chat.postMessage failed", data.error);
    return NextResponse.json({ ok: false, error: data.error }, { status: 502 });
  }

  return NextResponse.json({ ok: true, deliveredVia: "channel" });
}
