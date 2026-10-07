import { NextResponse } from "next/server";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.json({ error: "storage_not_configured" }, { status: 500 });
  }

  const res = await fetch(
    `${supabaseUrl}/rest/v1/campaign_requests?id=eq.${encodeURIComponent(id)}&select=*`,
    {
      headers: {
        apikey: supabaseKey,
        Authorization: `Bearer ${supabaseKey}`,
      },
    }
  );

  if (!res.ok) {
    return NextResponse.json({ error: "lookup_failed" }, { status: 502 });
  }

  const [row] = await res.json();
  if (!row) {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }

  return NextResponse.json({
    id: row.id,
    campaignName: row.campaign_name,
    channel: "Email",
    amName: row.am_name,
    accountName: row.account_name,
    campaignType: row.campaign_type,
    subject: row.subject,
    body: row.body,
    creativeUrl: row.creative_url,
    creativeIsStub: row.creative_is_stub,
    segmentSuggestion: row.segment_suggestion,
    reviewUrl: row.review_url,
    createdAt: row.created_at,
  });
}
