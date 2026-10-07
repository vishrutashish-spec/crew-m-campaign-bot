/**
 * Authenticated proxy to the Crew M engine.
 *
 * This replaced a plain next.config rewrite, which had a hole: the engine is a
 * separate Vercel project with its own public URL, so anyone could skip the
 * sign-in entirely by calling the engine host directly. A login that only
 * guards the front door is theatre.
 *
 * Now the engine refuses any request that does not carry a shared secret, and
 * the only thing holding that secret is this handler, which sits behind the
 * auth gate in proxy.ts. The secret is server-side only and never has a
 * NEXT_PUBLIC prefix, so it cannot reach browser code.
 *
 * Requests arriving here have already been authenticated by the proxy, so the
 * job is purely to forward faithfully: method, query, body and content type
 * out, status and body back.
 */

import { NextResponse, type NextRequest } from "next/server";

const ENGINE = process.env.ENGINE_ORIGIN
  ?? "https://iw-crew-m-engine.vercel.app";

async function forward(req: NextRequest, path: string[]) {
  const secret = process.env.CREWM_ENGINE_TOKEN;
  if (!secret) {
    return NextResponse.json(
      { error: "Engine access is not configured on this deployment." },
      { status: 503 },
    );
  }

  const target = `${ENGINE}/${path.join("/")}${req.nextUrl.search}`;
  const headers: Record<string, string> = { "x-crewm-engine": secret };
  const ct = req.headers.get("content-type");
  if (ct) headers["content-type"] = ct;

  const init: RequestInit = { method: req.method, headers, cache: "no-store" };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  try {
    const res = await fetch(target, init);
    const body = await res.text();
    return new NextResponse(body, {
      status: res.status,
      headers: {
        "content-type": res.headers.get("content-type") ?? "application/json",
        "cache-control": "no-store",
      },
    });
  } catch (e) {
    return NextResponse.json(
      { error: `Engine unreachable: ${e instanceof Error ? e.message : "unknown"}` },
      { status: 502 },
    );
  }
}

export async function GET(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(req, (await ctx.params).path);
}
