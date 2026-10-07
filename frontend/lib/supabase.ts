/**
 * Supabase clients for Crew M authentication.
 *
 * Auth is Plum Workspace Google sign-in, and the participant's own Supabase
 * project is the authority. Two clients, because the App Router needs both:
 *
 *   browser  runs in the page, starts the OAuth redirect, reads the session
 *   server   runs in the proxy and route handlers, reads and refreshes the
 *            session from cookies so a request can be gated before any data
 *            is served
 *
 * Only the ANON key is ever used here. The service_role key must never reach
 * browser code, and is not read by this module at all.
 *
 * Domain restriction is enforced in three independent places, deliberately:
 *   1. the Google app itself is Internal to the Plum Workspace
 *   2. a before_user_created hook in the database rejects other domains
 *   3. ALLOWED_DOMAIN below, so a session that somehow arrives from another
 *      domain is signed out client-side rather than trusted
 */

import { createBrowserClient, createServerClient } from "@supabase/ssr";
import type { NextRequest, NextResponse } from "next/server";

export const ALLOWED_DOMAIN = "plumhq.com";

/** Google's hosted-domain hint, so the account chooser only offers Plum. */
export const HOSTED_DOMAIN = "plumhq.com";

function env() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !key) {
    throw new Error(
      "Supabase is not configured. NEXT_PUBLIC_SUPABASE_URL and " +
      "NEXT_PUBLIC_SUPABASE_ANON_KEY must be set."
    );
  }
  return { url, key };
}

/** True when auth is configured at all, so the app can fail loudly not blankly. */
export function authConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL
    && process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY);
}

export function browserClient() {
  const { url, key } = env();
  return createBrowserClient(url, key);
}

/**
 * Server client bound to one request's cookies.
 *
 * The caller passes the response so refreshed tokens are written back. Without
 * that, a session that needed refreshing would silently read as signed out.
 */
export function serverClient(req: NextRequest, res: NextResponse) {
  const { url, key } = env();
  return createServerClient(url, key, {
    cookies: {
      getAll() {
        return req.cookies.getAll();
      },
      setAll(cookies) {
        cookies.forEach(({ name, value, options }) => {
          res.cookies.set(name, value, options);
        });
      },
    },
  });
}

/** Is this email allowed in at all? */
export function emailAllowed(email: string | null | undefined): boolean {
  return Boolean(email && email.toLowerCase().endsWith(`@${ALLOWED_DOMAIN}`));
}
