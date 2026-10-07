import { NextResponse } from "next/server";

/**
 * Renders the saved draft's subject + body as a simple, readable HTML page,
 * so a PMM approver can open a link and read the exact copy before clicking
 * Approve in Slack.
 *
 * This is a plain readable view of the stored copy, not a final-template
 * render. The real final rendering (template, co-branding, substitution)
 * happens when the draft is published through CleverTap.
 */
function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  const supabaseUrl = process.env.SUPABASE_URL;
  const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!supabaseUrl || !supabaseKey) {
    return new NextResponse("Preview unavailable - Supabase is not configured.", { status: 500 });
  }

  const rowRes = await fetch(
    `${supabaseUrl}/rest/v1/campaign_requests?id=eq.${encodeURIComponent(id)}`,
    { headers: { apikey: supabaseKey, Authorization: `Bearer ${supabaseKey}` } }
  );
  const [row] = rowRes.ok ? await rowRes.json() : [null];
  if (!row) {
    return new NextResponse("Campaign draft not found.", { status: 404 });
  }

  const subject = String(row.subject ?? "(no subject)");
  const body = String(row.body ?? "");
  const paragraphs = body
    .split(/\n\s*\n/)
    .map((p) => `<p>${escapeHtml(p).replace(/\n/g, "<br>")}</p>`)
    .join("\n");

  const html = `<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Draft preview</title>
<style>
  body { font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif;
         color: #2B0B21; background: #FDFAFB; margin: 0; padding: 32px 20px; }
  .wrap { max-width: 640px; margin: 0 auto; background: #fff; border: 1px solid #EADFE4;
          border-radius: 10px; padding: 28px 30px; }
  .label { font-size: 11px; color: #6E5866; text-transform: uppercase; letter-spacing: .1em; }
  h1 { font-size: 21px; margin: 6px 0 24px; line-height: 1.25; }
  .note { margin-top: 32px; padding-top: 20px; border-top: 1px solid #EADFE4;
          color: #6E5866; font-size: 12.5px; }
</style></head>
<body><div class="wrap">
  <div class="label">Subject</div>
  <h1>${escapeHtml(subject)}</h1>
  ${paragraphs}
  <p class="note">This is the raw copy stored in the draft. Template, co-branding
  and footer are applied when the draft is published from CleverTap.</p>
</div></body></html>`;

  return new NextResponse(html, {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
