/**
 * Route gate for Crew M.
 *
 * Named proxy, not middleware: the middleware file convention is deprecated in
 * this Next version and renamed to proxy, per
 * node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md
 *
 * A login that leaves the data API open is decoration. This runs on every page
 * and on the engine proxy, so an unauthenticated request cannot read a single
 * Plum figure, whether it comes from a browser or from curl.
 *
 * Three behaviours, by request shape:
 *   engine proxy   401 JSON, because a fetch should not be handed a login page
 *   pages          rendered, and the client-side gate shows the sign-in screen
 *   auth routes    always allowed, or sign-in could never complete
 *
 * It also refreshes the session on every request. Supabase access tokens are
 * short-lived; without a refresh here a working session reads as signed out
 * after an hour and the app would appear to log people out at random.
 */

import { NextResponse, type NextRequest } from "next/server";
import { serverClient, emailAllowed, authConfigured } from "@/lib/supabase";

/** Paths that must work before a session exists. */
const PUBLIC = ["/auth/callback", "/auth/signout"];

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const res = NextResponse.next({ request: req });

  if (PUBLIC.some((p) => pathname.startsWith(p))) return res;

  // With auth unconfigured, refuse rather than silently serving Plum data to
  // anyone. A misconfigured deploy should look broken, not open.
  if (!authConfigured()) {
    if (pathname.startsWith("/api/engine")) {
      return NextResponse.json(
        { error: "Authentication is not configured on this deployment." },
        { status: 503 },
      );
    }
    return res;
  }

  const supabase = serverClient(req, res);
  const { data: { user } } = await supabase.auth.getUser();
  const ok = user && emailAllowed(user.email);

  if (!ok && pathname.startsWith("/api/engine")) {
    return NextResponse.json(
      {
        error: "Sign in with your Plum Workspace account to read this data.",
        signed_in: Boolean(user),
        reason: user ? "domain_not_allowed" : "no_session",
      },
      { status: 401 },
    );
  }

  return res;
}

export const config = {
  // Everything except Next internals and static files. The engine proxy is
  // matched on purpose; static assets are not, so the sign-in screen can
  // still load its own fonts and logo.
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|icon.svg|fonts/|creative/|.*\\.(?:png|jpg|jpeg|svg|webp|woff|woff2|ttf)$).*)",
  ],
};
