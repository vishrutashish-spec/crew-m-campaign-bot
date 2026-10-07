import { NextResponse } from "next/server";

interface RenderCreativeRequest {
  requestId: string;
  copy: { subject?: string; body?: string; campaignType?: string; accountName?: string };
  logoUrl?: string;
}

const CREATIVE_QUEUE_URL =
  process.env.CREATIVE_QUEUE_WEBHOOK_URL ??
  "https://workflow-stg.plumhq.com/webhook/iw-crew-m-c4b9-creative-queue";

async function queuePendingCreative(params: {
  requestId: string;
  accountName?: string;
  campaignType?: string;
  logoUrl?: string;
}) {
  try {
    await fetch(CREATIVE_QUEUE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        requestId: params.requestId,
        accountName: params.accountName ?? "",
        campaignType: params.campaignType ?? "",
        brandMode: params.logoUrl ? "cobranded" : "single",
        logoUrl: params.logoUrl ?? "",
      }),
    });
  } catch (err) {
    console.error("Failed to queue pending creative request (non-fatal)", err);
  }
}

/**
 * In the target architecture, campaign creative is a slot in the HTML
 * template, filled by composing the campaign-type banner with the client
 * logo via a server-side image library. This route does not perform that
 * composition today; it accepts the request and queues it for the
 * creative-production pipeline. See CREW-M-CAMPAIGN-PLAYBOOK.md.
 */
const REAL_CREATIVES: Record<string, Record<string, { desktop: string; mobile: string }>> = {};

export async function POST(request: Request) {
  const { requestId, copy, logoUrl } = (await request.json()) as RenderCreativeRequest;

  const accountKey = copy?.accountName?.trim().toLowerCase();
  const typeKey = copy?.campaignType?.trim().toLowerCase();
  const real = accountKey && typeKey ? REAL_CREATIVES[accountKey]?.[typeKey] : undefined;

  if (real) {
    return NextResponse.json({
      requestId,
      creativeUrl: real.desktop,
      mobileCreativeUrl: real.mobile,
      stub: false,
    });
  }

  await queuePendingCreative({
    requestId,
    accountName: copy?.accountName,
    campaignType: copy?.campaignType,
    logoUrl,
  });

  const label = encodeURIComponent(copy?.campaignType ?? "campaign");
  return NextResponse.json({
    requestId,
    creativeUrl: `https://placehold.co/1200x630?text=${label}+creative`,
    stub: true,
    note: "No real creative exists yet — this request has been queued for the Figma-processing agent to build for real.",
  });
}
