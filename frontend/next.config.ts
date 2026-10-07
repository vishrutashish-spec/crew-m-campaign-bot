import type { NextConfig } from "next";

/**
 * The engine is reached through an authenticated route handler at
 * app/api/engine/[...path], NOT through a rewrite.
 *
 * A rewrite cannot attach the shared secret the engine now requires, and it
 * also could not be gated: the engine is a separate Vercel project with its
 * own public URL, so a rewrite left the data readable by anyone who called
 * that host directly. The route handler sits behind the auth gate and is the
 * only holder of the secret.
 *
 * ENGINE_ORIGIN overrides the target for a preview engine or a local uvicorn.
 */
const nextConfig: NextConfig = {};

export default nextConfig;
