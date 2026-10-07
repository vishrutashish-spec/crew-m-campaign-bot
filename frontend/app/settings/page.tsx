"use client";

/**
 * Settings: what this instance is connected to, what it is allowed to do, and
 * what it has verified. Read-only by design. Nothing here mutates Plum data,
 * and no credential value is ever displayed, only whether it resolved.
 */

import { useEffect, useState } from "react";
import {
  getMethodology, getVerification, getRules, resyncCleverTap, API_BASE, n,
  type Methodology, type DecisionParam, type ResyncResult,
} from "@/lib/api";
import {
  Panel, PanelHead, Chip, Stat, ErrorState, Skeleton, PageBanner, ProvenanceNote,
} from "@/components/kit";
import { ThemeToggle } from "@/components/theme-toggle";
import {
  CheckCircle2, Database, ShieldCheck, Gauge, Palette, RefreshCw, TriangleAlert,
} from "lucide-react";

interface Health {
  status: string; version: string; invariants_verified: number; built_at: string;
}


export default function SettingsPage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [checks, setChecks] = useState<{ checks: string[]; sim_checks: string[] } | null>(null);
  const [meth, setMeth] = useState<Methodology | null>(null);
  const [rules, setRules] = useState<{ id: string; label: string; version: string; parameters: DecisionParam[] }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/health`).then((r) => r.json()).then(setHealth)
      .catch((e) => setError(e.message));
    getVerification().then(setChecks).catch(() => {});
    getMethodology().then(setMeth).catch(() => {});
    getRules().then((r) => setRules(r.rules)).catch(() => {});
  }, []);

  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-7">
      <PageBanner
        kicker="Settings"
        title="Connections and guardrails"
        sub="What this instance reads, what it is permitted to do, and what it verifies before it will serve a number."
        window="crewm / settings"
        right={
          <div className="flex items-center gap-3">
            <span className="label-mono">Theme</span>
            <ThemeToggle />
          </div>
        }
      />

      {!health ? <Skeleton rows={2} /> : (
        <>
          {/* ---------------- status ---------------- */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            <Panel className="p-5">
              <Stat label="API" value={health.status === "ok" ? "Healthy" : health.status}
                sub={`version ${health.version}`} chip="OBSERVED" size="sm" />
            </Panel>
            <Panel className="p-5">
              <Stat label="Model invariants" value={String(health.invariants_verified)}
                sub="asserted at every boot" chip="DERIVED" size="sm" />
            </Panel>
            <Panel className="p-5">
              <Stat label="Simulation checks" value={String(checks?.sim_checks?.length ?? 0)}
                sub="objective x channel sweep" chip="DERIVED" size="sm" />
            </Panel>
            <Panel className="p-5">
              <Stat label="Decision rubrics" value={String(rules.length)}
                sub="published with their weights" chip="RECOMMENDED" size="sm" />
            </Panel>
          </div>

          {/* ---------------- data sources ---------------- */}
          <Panel className="p-5" ground="grid">
            <PanelHead
              title="Data sources"
              sub="Everything the product reads, and the scope of each"
              chip="OBSERVED"
            />
            <div className="relative grid grid-cols-1 lg:grid-cols-3 gap-4">
              <SourceCard
                icon={<Database className="w-4 h-4" />}
                name="CleverTap counts API"
                detail={meth ? `Pulled ${meth.provenance.observed.pulled_at}, ${meth.provenance.observed.window_days} day window` : "Aggregate counts only"}
                note="Read-only. Counts endpoints only, never profiles. Account-wide, since /counts accepts no organisation filter."
              />
              <SourceCard
                icon={<Database className="w-4 h-4" />}
                name="CT Bible segment exports"
                detail="956,050 eligible base, 8 reachability segments, both product funnels"
                note="Scoped to active, non-test organisations. The documented source of record for segment sizes."
              />
              <SourceCard
                icon={<Database className="w-4 h-4" />}
                name="Consultation and checkup files"
                detail="133,218 consults across 24 specialties, 36,526 checkup bookings, 11 scored markers"
                note="Aggregated in place. Distributions and rates only, no member rows, and doctor notes are never read."
              />
            </div>
          </Panel>

          <ResyncPanel />

          {/* ---------------- guardrails ---------------- */}
          <Panel className="p-5">
            <PanelHead
              title="Guardrails in force"
              sub="These are properties of the build, not settings to toggle"
              chip="OBSERVED"
              right={<ShieldCheck className="w-5 h-5 text-[color:var(--success)]" />}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-3">
              {[
                "All CleverTap queries are read-only and bounded to a one year window",
                "Counts only. No individual profile is ever fetched or stored",
                "Clinical files are aggregated in place; no member row leaves the process",
                "No export or download of records anywhere in the interface",
                "Every data-access route logs what was requested",
                "The API refuses to start if any model invariant fails",
                "Push and email rates are learned from 458 real campaigns; WhatsApp stays a labelled prior",
                "Provenance labels are mandatory: observed, derived, modeled, predicted",
              ].map((g) => (
                <div key={g} className="flex items-start gap-2.5 text-[12.5px]">
                  <CheckCircle2 className="w-4 h-4 text-[color:var(--success)] flex-shrink-0 mt-0.5" />
                  <span className="text-muted-foreground">{g}</span>
                </div>
              ))}
            </div>
          </Panel>

          {/* ---------------- rubrics ---------------- */}
          <Panel className="p-5">
            <PanelHead
              title="Published decision rubrics"
              sub="Every recommendation in the product scores against one of these, and the weights are visible in the interface"
              chip="RECOMMENDED"
              right={<Gauge className="w-5 h-5 text-muted-foreground" />}
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {rules.map((r) => (
                <div key={r.id} className="panel-flush p-4">
                  <div className="meta-row">
                    <span className="label-mono">{r.id}</span>
                    <Chip kind="RECOMMENDED" />
                    <span className="text-[10.5px] text-muted-foreground ml-auto">v{r.version}</span>
                  </div>
                  <p className="text-[13px] font-medium mb-2">{r.label}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {r.parameters.map((p) => (
                      <span key={p.key} title={p.desc}
                        className="text-[10px] px-2 py-1 rounded border border-border bg-[color:var(--muted)]">
                        {p.label} <span className="tnum font-semibold">{p.weight}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          {/* ---------------- invariants ---------------- */}
          {checks && (
            <Panel className="p-5">
              <PanelHead
                title="Verified at startup"
                sub="If any of these fails the API refuses to serve rather than return a wrong number"
                chip="OBSERVED"
                right={<span className="label-mono">{checks.checks.length + (checks.sim_checks?.length ?? 0)} checks</span>}
              />
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-x-6 gap-y-2">
                {[...checks.checks, ...(checks.sim_checks ?? [])].map((c) => (
                  <div key={c} className="flex items-start gap-2 text-[11.5px]">
                    <CheckCircle2 className="w-3.5 h-3.5 text-[color:var(--success)] flex-shrink-0 mt-0.5" />
                    <span className="text-muted-foreground font-mono">{c}</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}

          {/* ---------------- appearance ---------------- */}
          <Panel className="p-5">
            <PanelHead
              title="Appearance"
              sub="Theme follows your system setting until you choose one"
              right={<Palette className="w-5 h-5 text-muted-foreground" />}
            />
            <div className="flex items-center justify-between gap-6 flex-wrap">
              <p className="text-[12.5px] text-muted-foreground max-w-xl">
                Charts re-light per theme: plum violet leads in light, cream leads in dark,
                and exported PNGs follow whichever theme is active so a dark export never
                lands light text on a white plate.
              </p>
              <ThemeToggle />
            </div>
            <ProvenanceNote label="Font licensing" kind="MODELED">
              The wordmark uses Brigold DEMO, which is licensed for personal use only.
              A commercial licence is required before this ships beyond a prototype.
            </ProvenanceNote>
          </Panel>
        </>
      )}
    </div>
  );
}

/**
 * Resync the live usage block against CleverTap.
 *
 * The panel reports drift against the anchored figure rather than silently
 * swapping numbers, and states what a resync cannot refresh, so pressing it
 * never reads as "the whole dashboard was just re-verified".
 */
function ResyncPanel() {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<ResyncResult | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function go() {
    setBusy(true); setErr(null);
    try {
      setRes(await resyncCleverTap("settings"));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Resync failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel className="p-5">
      <PanelHead
        title="Live usage from CleverTap"
        sub="Re-pulls the usage block from the counts API. Read-only, aggregate counts only, every window bounded and none wider than a year."
        chip="OBSERVED"
        right={
          <button onClick={go} disabled={busy} className="btn !px-3.5 !py-2 !text-[12px]">
            <RefreshCw className={`w-3.5 h-3.5 ${busy ? "animate-spin" : ""}`} />
            {busy ? "Pulling from CleverTap" : "Resync with CleverTap"}
          </button>
        }
      />

      {err && (
        <p className="text-[12px] text-[color:var(--red)]">{err}</p>
      )}
      {res?.error && (
        <p className="text-[12px] text-[color:var(--warning)]">{res.error}</p>
      )}
      {res?.partial && (
        <p className="text-[12px] text-[color:var(--warning)] mb-1">{res.partial}</p>
      )}

      {res && res.fields.length > 0 && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="text-left">
                  <th className="label-mono !text-[9px] pb-2">Figure</th>
                  <th className="label-mono !text-[9px] pb-2 text-right">Anchored</th>
                  <th className="label-mono !text-[9px] pb-2 text-right">Live now</th>
                  <th className="label-mono !text-[9px] pb-2 text-right">Drift</th>
                  <th className="label-mono !text-[9px] pb-2 pl-4">Window queried</th>
                </tr>
              </thead>
              <tbody>
                {res.fields.map((f) => (
                  <tr key={f.key} className="border-t border-border">
                    <td className="py-2 pr-3">
                      <span className="font-medium">{f.label}</span>
                      <span className="block text-[10.5px] text-muted-foreground">{f.basis}</span>
                    </td>
                    <td className="py-2 text-right tnum">{f.anchored ? n(f.anchored) : "-"}</td>
                    <td className="py-2 text-right tnum font-semibold">
                      {f.live === null
                        ? <span className={f.status === "skipped"
                            ? "text-[color:var(--warning)]" : "text-[color:var(--red)]"}>
                            {f.status === "skipped" ? "not queried" : "failed"}
                          </span>
                        : n(f.live)}
                    </td>
                    <td className={`py-2 text-right tnum ${
                      f.drift === undefined ? "text-muted-foreground"
                      : Math.abs(f.drift) < 0.01 ? "text-muted-foreground"
                      : "text-[color:var(--warning)]"}`}>
                      {f.drift === undefined ? "-" : `${f.drift > 0 ? "+" : ""}${(f.drift * 100).toFixed(1)}%`}
                    </td>
                    <td className="py-2 pl-4 text-[10.5px] text-muted-foreground tnum">{f.window}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-[11px] text-muted-foreground mt-3">
            Pulled {new Date(res.pulled_at).toLocaleString()} · anchored {res.anchored_at} ·{" "}
            {res.dau_method}. {res.scope}
          </p>

          <div className="mt-4 pt-4 border-t border-border space-y-3">
            <span className="label-mono">What a resync cannot refresh</span>
            {res.cannot_refresh.map((c) => (
              <div key={c.field} className="flex items-start gap-2.5">
                <TriangleAlert className="w-3.5 h-3.5 text-[color:var(--warning)] flex-shrink-0 mt-0.5" />
                <p className="text-[11.5px] text-muted-foreground leading-relaxed">
                  <span className="font-medium text-foreground">{c.field}.</span> {c.reason}
                </p>
              </div>
            ))}
          </div>
        </>
      )}
    </Panel>
  );
}

function SourceCard({ icon, name, detail, note }: {
  icon: React.ReactNode; name: string; detail: string; note: string;
}) {
  return (
    <div className="panel-flush p-4">
      <div className="meta-row">
        <span className="w-6 h-6 rounded-md metal-cyan flex items-center justify-center text-white flex-shrink-0">
          {icon}
        </span>
        <span className="label-mono">Connected</span>
        <Chip kind="OBSERVED" />
      </div>
      <p className="text-[13px] font-medium">{name}</p>
      <p className="text-[11.5px] text-muted-foreground mt-1.5 tnum">{detail}</p>
      <p className="text-[11px] text-muted-foreground mt-2.5 pt-2.5 border-t border-border leading-relaxed">
        {note}
      </p>
    </div>
  );
}
