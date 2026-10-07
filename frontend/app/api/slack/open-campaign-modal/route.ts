import { NextResponse } from "next/server";

interface OpenModalRequest {
  requestId: string;
  triggerId: string;
  slackUser: string;
  slackChannel: string;
}

/**
 * Opens the /crew-m campaign request modal.
 *
 * Block and action ids here are a contract with the n8n workflow
 * ("iw-crew-m-c4b9 · AM campaign request → CleverTap draft", node
 * "Extract Campaign Fields"), which reads:
 *   am_name_block.am_name_input.value
 *   account_block.account_input.value
 *   campaign_type_block.campaign_type_select.selected_option.value
 *   logo_block.logo_upload.files[0].id / .url_private
 * Renaming any of them silently breaks the submission handler.
 *
 * radio_buttons rather than static_select: static_select was rejected by
 * views.open with invalid_arguments, and radio_buttons yields the same
 * selected_option.value shape.
 *
 * file_input IS supported in modals (it needs the files:read scope, which
 * this app has) — verified against Slack by structure-checking this exact
 * payload, which returns invalid_trigger_id rather than invalid_arguments.
 */
export async function POST(request: Request) {
  const { requestId, triggerId, slackChannel } = (await request.json()) as OpenModalRequest;

  const token = process.env.SLACK_BOT_TOKEN;
  if (!token) {
    console.error("SLACK_BOT_TOKEN is not set — cannot open the campaign modal");
    return NextResponse.json({ ok: false, error: "slack_not_configured" }, { status: 500 });
  }

  const view = {
    type: "modal",
    callback_id: "am_campaign_request",
    private_metadata: JSON.stringify({ channelId: slackChannel, requestId }),
    title: { type: "plain_text", text: "New campaign" },
    submit: { type: "plain_text", text: "Submit" },
    close: { type: "plain_text", text: "Cancel" },
    blocks: [
      {
        type: "input",
        block_id: "am_name_block",
        label: { type: "plain_text", text: "Your name" },
        element: {
          type: "plain_text_input",
          action_id: "am_name_input",
          placeholder: { type: "plain_text", text: "Jordan Lee" },
        },
      },
      {
        type: "input",
        block_id: "account_block",
        label: { type: "plain_text", text: "Account name" },
        element: {
          type: "plain_text_input",
          action_id: "account_input",
          placeholder: { type: "plain_text", text: "Client company name" },
        },
      },
      {
        type: "input",
        block_id: "campaign_type_block",
        label: { type: "plain_text", text: "Campaign type" },
        element: {
          type: "radio_buttons",
          action_id: "campaign_type_select",
          options: [
            { text: { type: "plain_text", text: "Welcome" }, value: "welcome" },
            { text: { type: "plain_text", text: "Renewal" }, value: "renewal" },
            { text: { type: "plain_text", text: "HRA (Health Risk Assessment)" }, value: "hra" },
          ],
        },
      },
      {
        type: "input",
        block_id: "logo_block",
        optional: true,
        label: { type: "plain_text", text: "Account logo (optional)" },
        hint: {
          type: "plain_text",
          text: "PNG only. A transparent, dark-on-light wordmark works best — the header is cream.",
        },
        element: {
          type: "file_input",
          action_id: "logo_upload",
          filetypes: ["png"],
          max_files: 1,
        },
      },
    ],
  };

  const res = await fetch("https://slack.com/api/views.open", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json; charset=utf-8",
    },
    body: JSON.stringify({ trigger_id: triggerId, view }),
  });

  const data = await res.json();
  if (!data.ok) {
    console.error("views.open failed", data.error, JSON.stringify(data.response_metadata ?? {}));
    return NextResponse.json({ ok: false, error: data.error }, { status: 502 });
  }

  return NextResponse.json({ ok: true });
}
