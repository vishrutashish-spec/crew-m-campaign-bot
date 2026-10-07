"use client";

/**
 * Client-side auth gate.
 *
 * Until a Plum Workspace session exists, this renders the sign-in screen and
 * nothing else: no sidebar, no assistant, no page content. The server gate in
 * proxy.ts is what actually protects the data; this is what the person
 * sees, and it keeps a single unauthenticated figure from ever painting.
 *
 * A session from outside the allowed domain is signed out on sight rather than
 * shown an error and left logged in.
 */

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import type { Session } from "@supabase/supabase-js";
import {
  browserClient, authConfigured, emailAllowed, HOSTED_DOMAIN, ALLOWED_DOMAIN,
} from "@/lib/supabase";
import { CrewMLogo } from "@/components/logos";
import { ShieldCheck, TriangleAlert, RotateCw } from "lucide-react";

interface AuthValue {
  session: Session | null;
  email: string | null;
  signOut: () => Promise<void>;
}

const Ctx = createContext<AuthValue>({
  session: null, email: null, signOut: async () => {},
});

export const useAuth = () => useContext(Ctx);

export function AuthGate({ children }: { children: React.ReactNode }) {
  const configured = authConfigured();
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Surface an OAuth failure that came back on the URL, then clean it off so
    // a refresh does not keep showing a stale error.
    const p = new URLSearchParams(window.location.search);
    const e = p.get("auth_error");
    if (e) {
      setError(e === "domain_not_allowed"
        ? `That account is not on ${ALLOWED_DOMAIN}. Sign in with your Plum Workspace account.`
        : e);
      p.delete("auth_error");
      const q = p.toString();
      window.history.replaceState({}, "",
        window.location.pathname + (q ? `?${q}` : ""));
    }
  }, []);

  useEffect(() => {
    if (!configured) { setReady(true); return; }
    const supabase = browserClient();
    let alive = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!alive) return;
      const s = data.session;
      if (s && !emailAllowed(s.user.email)) {
        supabase.auth.signOut();
        setSession(null);
        setError(`That account is not on ${ALLOWED_DOMAIN}.`);
      } else {
        setSession(s ?? null);
      }
      setReady(true);
    });

    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => {
      if (!alive) return;
      if (s && !emailAllowed(s.user.email)) {
        supabase.auth.signOut();
        setSession(null);
        return;
      }
      setSession(s ?? null);
    });
    return () => { alive = false; sub.subscription.unsubscribe(); };
  }, [configured]);

  const signIn = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const supabase = browserClient();
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          // hd limits Google's own account chooser to the Plum Workspace.
          queryParams: { hd: HOSTED_DOMAIN },
          redirectTo: `${window.location.origin}/auth/callback?next=${
            encodeURIComponent(window.location.pathname)}`,
        },
      });
      if (error) { setError(error.message); setBusy(false); }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sign-in failed to start.");
      setBusy(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    if (!configured) return;
    await browserClient().auth.signOut();
    setSession(null);
  }, [configured]);

  if (!configured) {
    return (
      <Shell>
        <div className="auth-note auth-note-bad">
          <TriangleAlert className="w-4 h-4 flex-shrink-0" />
          <span>
            Authentication is not configured on this deployment, so it will not
            serve data. <code>NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
            <code>NEXT_PUBLIC_SUPABASE_ANON_KEY</code> are missing.
          </span>
        </div>
      </Shell>
    );
  }

  if (!ready) {
    return (
      <Shell>
        <p className="auth-sub">Checking your session</p>
      </Shell>
    );
  }

  if (!session) {
    return (
      <Shell>
        <p className="auth-sub">
          Crew M reads confidential Plum campaign and clinical aggregates, so it
          is restricted to Plum Workspace accounts.
        </p>

        {error && (
          <div className="auth-note auth-note-bad">
            <TriangleAlert className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <button className="auth-btn" onClick={signIn} disabled={busy}>
          {busy ? <RotateCw className="w-4 h-4 animate-spin" />
                : <GoogleMark />}
          {busy ? "Opening Google" : "Continue with Plum Workspace"}
        </button>

        <div className="auth-note">
          <ShieldCheck className="w-4 h-4 flex-shrink-0" />
          <span>
            Only <strong>@{ALLOWED_DOMAIN}</strong> accounts can sign in. Access
            is read-only, every data route is logged, and nothing here can be
            exported.
          </span>
        </div>
      </Shell>
    );
  }

  return (
    <Ctx.Provider value={{ session, email: session.user.email ?? null, signOut }}>
      {children}
    </Ctx.Provider>
  );
}

/** The sign-in plate. Deliberately the only thing on screen. */
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="auth-screen">
      <div className="auth-card glass">
        <div className="auth-brand">
          <CrewMLogo />
        </div>
        <h1 className="auth-title">Campaign intelligence</h1>
        {children}
      </div>
      <p className="auth-foot">
        Plum product marketing. Crew M reconciles every figure to a verified
        anchor and labels what kind of claim it is.
      </p>
    </div>
  );
}

/** Google's mark, drawn rather than loaded, since no external image is allowed. */
function GoogleMark() {
  return (
    <svg viewBox="0 0 18 18" width="17" height="17" aria-hidden className="flex-shrink-0">
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.17-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.91c1.7-1.57 2.69-3.88 2.69-6.62z"/>
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.91-2.26c-.81.54-1.84.86-3.05.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A9 9 0 0 0 9 18z"/>
      <path fill="#FBBC05" d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.94H.96a9 9 0 0 0 0 8.12l3.01-2.34z"/>
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58z"/>
    </svg>
  );
}
