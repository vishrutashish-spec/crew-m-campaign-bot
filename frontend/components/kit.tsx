"use client";

/**
 * Shared UI primitives for Crew M.
 *
 * ChartFrame is the important one: every chart on every screen goes through it,
 * so the title, provenance chip, PNG export and empty state are identical
 * everywhere and can't drift apart screen by screen.
 */

import { useRef, useState, type ReactNode } from "react";
import { Download, Check, AlertTriangle, Info } from "lucide-react";
import { exportSvgToPng, findChartSvg } from "@/lib/export-png";
import { pct, n, type Provenance } from "@/lib/api";

/* --------------------------------------------------------------------------
   Provenance chip: the four-way distinction, never blurred
   -------------------------------------------------------------------------- */

const CHIP_CLASS: Record<string, string> = {
  OBSERVED: "chip-observed",
  DERIVED: "chip-derived",
  PREDICTED: "chip-predicted",
  RECOMMENDED: "chip-recommended",
  MODELED: "chip-modeled",
};

export function Chip({ kind, title }: { kind: Provenance | string; title?: string }) {
  return (
    <span className={`chip ${CHIP_CLASS[kind] ?? "chip-modeled"}`} title={title}>
      {kind}
    </span>
  );
}

/* --------------------------------------------------------------------------
   Panel
   -------------------------------------------------------------------------- */

export function Panel({
  children,
  className = "",
  ground,
  ticked,
}: {
  children: ReactNode;
  className?: string;
  ground?: "grid" | "dot" | "aurora";
  ticked?: boolean;
}) {
  const groundClass =
    ground === "grid" ? "grid-ground" : ground === "dot" ? "dot-ground grid-ground" : ground === "aurora" ? "aurora" : "";
  return (
    <div className={`panel ${groundClass} ${ticked ? "panel-ticked" : ""} ${className}`}>
      {children}
    </div>
  );
}

export function PanelHead({
  title,
  sub,
  chip,
  right,
}: {
  title: string;
  sub?: string;
  chip?: Provenance | string;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-4 relative">
      <div className="min-w-0">
        <div className="flex items-center gap-2.5 flex-wrap">
          <h3 className="section-title">{title}</h3>
          {chip && <Chip kind={chip} />}
        </div>
        {sub && <p className="text-[12.5px] text-muted-foreground mt-1.5 leading-relaxed">{sub}</p>}
      </div>
      {right && <div className="flex-shrink-0">{right}</div>}
    </div>
  );
}

/* --------------------------------------------------------------------------
   ChartFrame: wraps every chart, owns the PNG export
   -------------------------------------------------------------------------- */

export function ChartFrame({
  title,
  sub,
  chip,
  caption,
  filename,
  children,
  right,
  ground,
  className = "",
}: {
  title: string;
  sub?: string;
  chip?: Provenance | string;
  /** Burned into the PNG footer: keeps an exported image self-describing. */
  caption?: string;
  filename?: string;
  children: ReactNode;
  right?: ReactNode;
  ground?: "grid" | "dot" | "aurora";
  className?: string;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "working" | "done" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function download() {
    const svg = findChartSvg(holder.current);
    if (!svg) {
      setState("error");
      setError("No chart found to export");
      return;
    }
    setState("working");
    setError(null);
    try {
      await exportSvgToPng(svg, {
        filename: filename ?? title,
        caption: caption ?? `${title}: Crew M`,
        scale: 2,
      });
      setState("done");
      setTimeout(() => setState("idle"), 1800);
    } catch (e) {
      setState("error");
      setError(e instanceof Error ? e.message : "Export failed");
      setTimeout(() => setState("idle"), 3200);
    }
  }

  return (
    <Panel ground={ground} className={`p-5 ${className}`}>
      <PanelHead
        title={title}
        sub={sub}
        chip={chip}
        right={
          <div className="flex items-center gap-2">
            {right}
            <button
              onClick={download}
              disabled={state === "working"}
              className="btn !px-2.5 !py-1.5 !text-[11px]"
              title={error ?? "Download this chart as a PNG"}
              aria-label="Download chart as PNG"
            >
              {state === "done" ? (
                <>
                  <Check className="w-3.5 h-3.5" /> Saved
                </>
              ) : state === "error" ? (
                <>
                  <AlertTriangle className="w-3.5 h-3.5" /> Failed
                </>
              ) : (
                <>
                  <Download className="w-3.5 h-3.5" />
                  {state === "working" ? "…" : "PNG"}
                </>
              )}
            </button>
          </div>
        }
      />
      <div ref={holder} className="relative">
        {children}
      </div>
    </Panel>
  );
}

/* --------------------------------------------------------------------------
   Stats
   -------------------------------------------------------------------------- */

export function Stat({
  label,
  value,
  sub,
  tone = "ink",
  size = "md",
  chip,
}: {
  label: string;
  value: string;
  sub?: string;
  tone?: "ink" | "red" | "cyan" | "muted";
  size?: "sm" | "md" | "lg" | "xl";
  chip?: Provenance | string;
}) {
  const sizes = { sm: "text-[22px]", md: "text-[29px]", lg: "text-[37px]", xl: "text-[49px]" };
  const tones = {
    ink: "text-[color:var(--ink-text)]",
    red: "text-[color:var(--red)]",
    cyan: "text-[color:var(--cyan-deep)]",
    muted: "text-muted-foreground",
  };
  return (
    <div>
      {/* meta row: label and chip aligned above the value, never beside it */}
      <div className="meta-row">
        <span className="label-mono">{label}</span>
        {chip && <Chip kind={chip} />}
      </div>
      <p className={`figure ${sizes[size]} ${tones[tone]}`}>{value}</p>
      {sub && <p className="text-[12px] text-muted-foreground mt-2 leading-snug">{sub}</p>}
    </div>
  );
}

/** A metric row with an inline proportional bar. */
export function BarRow({
  label,
  value,
  total,
  color,
  note,
  icon,
}: {
  label: string;
  value: number;
  total: number;
  color: string;
  note?: string;
  icon?: ReactNode;
}) {
  const share = total > 0 ? value / total : 0;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3 mb-1.5">
        <span className="text-[12.5px] text-foreground font-medium inline-flex items-center gap-1.5">
          {icon}
          {label}
        </span>
        <span className="text-[12.5px] tnum">
          <span className="font-semibold">{n(value)}</span>
          <span className="text-muted-foreground ml-1.5">{pct(share)}</span>
        </span>
      </div>
      <div className="ribbon">
        <span style={{ width: `${Math.max(share * 100, 0.5)}%`, background: color }} />
      </div>
      {note && <p className="text-[10.5px] text-muted-foreground mt-1.5">{note}</p>}
    </div>
  );
}

/** A stacked ribbon for a two- or three-way split. */
export function SplitRibbon({
  parts,
}: {
  parts: { label: string; value: number; color: string }[];
}) {
  const total = parts.reduce((s, p) => s + p.value, 0) || 1;
  return (
    <div>
      <div className="ribbon mb-2.5">
        {parts.map((p) => (
          <span key={p.label} style={{ width: `${(p.value / total) * 100}%`, background: p.color }} />
        ))}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1.5">
        {parts.map((p) => (
          <span key={p.label} className="flex items-center gap-1.5 text-[11px]">
            <span
              className="w-2.5 h-2.5 rounded-full flex-shrink-0 border border-[color:var(--swatch-border)]"
              style={{ background: p.color }}
            />
            <span className="text-muted-foreground">{p.label}</span>
            <span className="tnum font-semibold text-foreground">{n(p.value)}</span>
            <span className="text-muted-foreground tnum">{pct(p.value / total, 0)}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------
   Insight card
   -------------------------------------------------------------------------- */

export function InsightCard({ insight }: { insight: import("@/lib/api").Insight }) {
  const [open, setOpen] = useState(false);
  const accent =
    insight.severity === "high"
      ? "var(--red)"
      : insight.severity === "medium"
      ? "var(--sand-deep)"
      : "var(--ink-soft)";

  return (
    <div className="panel-flush p-4 relative overflow-hidden">
      <span className="absolute left-0 top-0 bottom-0 w-[3px]" style={{ background: accent }} />
      <div className="pl-3">
        <div className="flex items-start justify-between gap-3 mb-2">
          <h4 className="text-[13.5px] leading-snug flex-1">{insight.title}</h4>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <Chip kind={insight.kind} />
            {insight.modeled && <Chip kind="MODELED" />}
          </div>
        </div>
        <p className="text-[12px] text-muted-foreground leading-relaxed">{insight.body}</p>

        <button
          onClick={() => setOpen(!open)}
          className="mt-2.5 text-[11px] text-[color:var(--cyan-deep)] hover:underline flex items-center gap-1"
        >
          <Info className="w-3 h-3" />
          {open ? "Hide the arithmetic" : "Show the arithmetic"}
        </button>

        {open && (
          <div className="mt-2 space-y-2">
            <div className="rounded-md bg-[color:var(--muted)] border border-border px-3 py-2">
              <p className="label-mono mb-1">How this was computed</p>
              <p className="text-[11.5px] font-mono text-foreground">{insight.arithmetic}</p>
            </div>
            <div className="rounded-md bg-[color:var(--cyan-wash)] border border-[color:var(--cyanw-border)] px-3 py-2">
              <p className="label-mono mb-1 !text-[color:var(--cyan-deep)]">Do this</p>
              <p className="text-[11.5px] text-foreground">{insight.action}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------
   States
   -------------------------------------------------------------------------- */

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="max-w-lg mx-auto py-20">
      <Panel className="p-8 text-center" ticked>
        <div className="w-12 h-12 rounded-xl metal-red flex items-center justify-center mx-auto mb-4">
          <AlertTriangle className="w-6 h-6 text-white" />
        </div>
        <h3 className="text-[17px] mb-2">The API is not reachable</h3>
        <p className="text-[12.5px] text-muted-foreground mb-1">{message}</p>
        <p className="text-[12.5px] text-muted-foreground mb-5">
          The cohort model is served by the Python API: start it and this page will load.
        </p>
        <code className="text-[11.5px] bg-[color:var(--muted)] border border-border px-3.5 py-2 rounded-md font-mono inline-block">
          cd backend &amp;&amp; python3 server.py
        </code>
      </Panel>
    </div>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-6 py-2">
      <div className="h-9 w-64 bg-[color:var(--muted)] rounded-lg animate-pulse" />
      <div className="grid grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 bg-[color:var(--muted)] rounded-xl animate-pulse" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-64 bg-[color:var(--muted)] rounded-xl animate-pulse" />
      ))}
    </div>
  );
}

/* --------------------------------------------------------------------------
   Chart tooltip: shared so every chart reads the same
   -------------------------------------------------------------------------- */

export function ChartTip({
  active,
  payload,
  label,
  formatter,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number | string; color?: string; payload?: Record<string, unknown> }[];
  label?: string | number;
  formatter?: (v: number, name: string, row?: Record<string, unknown>) => string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-xl px-3.5 py-2.5">
      {label !== undefined && (
        <p className="text-[11.5px] font-semibold text-[color:var(--ink-text)] mb-1.5 font-heading">{label}</p>
      )}
      <div className="space-y-1">
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2 text-[11.5px]">
            {p.color && (
              <span
                className="w-2 h-2 rounded-full flex-shrink-0 border border-[color:var(--swatch-border)]"
                style={{ background: p.color }}
              />
            )}
            <span className="text-muted-foreground">{p.name}</span>
            <span className="tnum font-semibold text-foreground ml-auto">
              {formatter && typeof p.value === "number"
                ? formatter(p.value, p.name ?? "", p.payload)
                : typeof p.value === "number"
                ? n(p.value)
                : String(p.value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Resolve a Recharts paint value to something a CSS background can show.
 * Gradient fills arrive as url(#gs1); map those back to the matching solid
 * series token so the tooltip swatch is filled and colour-correct.
 */
export function solidPaint(paint: string): string {
  const m = /url\(#gs(\d)\)/.exec(paint);
  if (m) return `var(--series-${m[1]})`;
  return paint;
}

/** Shared axis styling so every chart's ticks match. */
export const AXIS = {
  tick: { fontSize: 11, fill: "var(--tick)", fontFamily: "Vollkorn, Georgia, serif" },
  axisLine: false as const,
  tickLine: false as const,
};

/* --------------------------------------------------------------------------
   macOS window chrome + the premium page banner
   -------------------------------------------------------------------------- */

export function MacBar({ title }: { title: string }) {
  return (
    <div className="mac-bar">
      <span className="mac-dot mac-dot-r" />
      <span className="mac-dot mac-dot-y" />
      <span className="mac-dot mac-dot-g" />
      <span className="mac-title">{title}</span>
    </div>
  );
}

/**
 * The main text banner every page opens with: mac window chrome on top,
 * engineered grid + warm aurora behind a large Vollkorn title. White only.
 */
export function PageBanner({
  kicker,
  title,
  sub,
  right,
  children,
  window: windowTitle,
}: {
  kicker: string;
  title: string;
  sub?: string;
  right?: ReactNode;
  children?: ReactNode;
  window?: string;
}) {
  return (
    <section className="mac-panel rise">
      <MacBar title={windowTitle ?? `crewm / ${kicker.toLowerCase()}`} />
      <div className="grid-ground aurora px-8 pt-7 pb-7">
        <div className="relative flex items-end justify-between gap-8 flex-wrap">
          <div className="min-w-0">
            <span className="banner-kicker">{kicker}</span>
            <h1 className="banner-title mt-2.5">{title}</h1>
            {sub && (
              <p className="text-[13.5px] text-muted-foreground mt-3 max-w-2xl leading-relaxed">
                {sub}
              </p>
            )}
          </div>
          {right && <div className="flex-shrink-0 relative">{right}</div>}
        </div>
        {children && <div className="glass relative mt-7 rounded-2xl px-6 py-5">{children}</div>}
      </div>
    </section>
  );
}

/* --------------------------------------------------------------------------
   Chart polish: gradient series fills + soft grid, shared by every chart.
   Diagonal gradients read well in both bar orientations, and the stops are
   theme tokens, so dark mode re-lights every chart automatically.
   -------------------------------------------------------------------------- */

export function SeriesDefs() {
  return (
    <defs>
      {[1, 2, 3].map((i) => (
        <linearGradient key={i} id={`gs${i}`} x1="0" y1="0" x2="0.6" y2="1">
          <stop offset="0%" stopColor={`var(--series-${i}-hi)`} />
          <stop offset="100%" stopColor={`var(--series-${i})`} />
        </linearGradient>
      ))}
      <filter id="soft-glow" x="-30%" y="-30%" width="160%" height="160%">
        <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="var(--series-1)" floodOpacity="0.18" />
      </filter>
    </defs>
  );
}

/** Series gradient fills, indexed to match CHART.ink/red/sand. */
export const GRAD = {
  ink: "url(#gs1)",
  red: "url(#gs2)",
  sand: "url(#gs3)",
} as const;

/* --------------------------------------------------------------------------
   ProvenanceNote: a labelled line that carries a chip without stuffing it
   mid-sentence. Use this anywhere a caveat needs a provenance label.
   -------------------------------------------------------------------------- */

export function ProvenanceNote({
  label, kind, children,
}: {
  label: string;
  kind: Provenance | string;
  children: ReactNode;
}) {
  return (
    <div className="chip-line">
      <span className="label-mono">{label}</span>
      <Chip kind={kind} />
      <span className="text-[12px] text-muted-foreground flex-1 min-w-[12rem]">{children}</span>
    </div>
  );
}

/** A numbered step heading: "1" above, title below, no dash separator. */
export function StepHead({
  step, title, sub, chip, right,
}: {
  step: number | string;
  title: string;
  sub?: string;
  chip?: Provenance | string;
  right?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-4 relative">
      <div className="min-w-0">
        <span className="step-num">STEP {step}</span>
        <div className="flex items-center gap-2.5 flex-wrap">
          <h3 className="section-title">{title}</h3>
          {chip && <Chip kind={chip} />}
        </div>
        {sub && <p className="text-[12.5px] text-muted-foreground mt-1.5 leading-relaxed">{sub}</p>}
      </div>
      {right && <div className="flex-shrink-0">{right}</div>}
    </div>
  );
}
