/**
 * OAuth callback. Google sends the browser back here with a code, which is
 * exchanged for a session and written into cookies.
 *
 * The domain is checked again at this point, before the session is allowed to
 * persist. The database hook already refuses non-Plum accounts at signup, so
 * reaching here with a foreign domain should be impossible; if it ever happens
 * the session is torn down rather than trusted.
 */

import { NextResponse, type NextRequest } from "next/server";
import { serverClient, emailAllowed } from "@/lib/supabase";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const next = url.searchParams.get("next") || "/";
  const oauthError = url.searchParams.get("error_description")
    || url.searchParams.get("error");

  if (oauthError) {
    return NextResponse.redirect(
      new URL(`/?auth_error=${encodeURIComponent(oauthError)}`, url.origin));
  }
  if (!code) {
    return NextResponse.redirect(new URL("/?auth_error=missing_code", url.origin));
  }

  const res = NextResponse.redirect(new URL(next, url.origin));
  const supabase = serverClient(req, res);
  const { data, error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(
      new URL(`/?auth_error=${encodeURIComponent(error.message)}`, url.origin));
  }

  const email = data.session?.user?.email;
  if (!emailAllowed(email)) {
    await supabase.auth.signOut();
    return NextResponse.redirect(
      new URL("/?auth_error=domain_not_allowed", url.origin));
  }

  // Audit line: who signed in and when. Required for a data-access feature,
  // and it records the identity only, never a token.
  console.log(`AUTH: sign-in email=${email} at=${new Date().toISOString()}`);
  return res;
}
