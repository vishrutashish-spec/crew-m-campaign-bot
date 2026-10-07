import { NextResponse } from "next/server";

/**
 * Campaign send is intentionally not implemented in this service.
 *
 * In the target architecture, campaigns are created as drafts in CleverTap
 * (see /api/campaign/draft) and published by a PMM from CleverTap's own
 * dashboard. This application never calls a sending API directly; delivery,
 * frequency caps, suppression and unsubscribe handling are all inherited from
 * CleverTap by publishing through it.
 *
 * This route exists only so any caller that still references it gets a clear
 * 501 with a pointer to the real path, rather than a 404 or a silent failure.
 */
export const dynamic = "force-dynamic";

export async function POST() {
  return NextResponse.json(
    {
      ok: false,
      error: "not_implemented",
      message:
        "Campaign sending runs through CleverTap. Create a draft via " +
        "/api/campaign/draft and publish it from the CleverTap dashboard.",
    },
    { status: 501 },
  );
}

export async function GET() {
  return NextResponse.json(
    {
      ok: false,
      error: "not_implemented",
      message:
        "Campaign sending runs through CleverTap. Create a draft via " +
        "/api/campaign/draft and publish it from the CleverTap dashboard.",
    },
    { status: 501 },
  );
}
