"use client";

import { useEffect, useState } from "react";
import {
  getCohorts, getCohort, n, compact, pct, CHART,
  type Cohort, type CohortsResponse, type CohortDetail,
} from "@/lib/api";
import {
  Panel, PanelHead, ChartFrame, Chip, Stat, BarRow, SplitRibbon,
  InsightCard, ErrorState, Skeleton, ChartTip, AXIS, SeriesDefs, GRAD, PageBanner,
} from "@/components/kit";
import { ChannelGlyph } from "@/components/logos";
import { getCohortIntel, type CohortIntel } from "@/lib/api";
import {
  CartesianGrid,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  RadialBarChart, RadialBar, PolarAngleAxis, LabelList,
} from "recharts";
import { Smartphone, TriangleAlert, Clock } from "lucide-react";

const ORGS = [
  { key: "all", label: "All orgs" },
  { key: "ENT", label: "Enterprise" },
  { key: "MM", label: "Mid-Market" },
  { key: "SMB", label: "SMB" },
  { key: "EOR", label: "EOR" },
];

export default function CohortsPage() {
  const [org, setOrg] = useState("all");
  const [list, setList] = useState<CohortsResponse | null>(null);
  const [active, setActive] = useState<string>("26_35");
  const [detail, setDetail] = useState<CohortDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCohorts(org).then(setList).catch((e) => setError(e.message));
  }, [org]);

  useEffect(() => {
    setDetail(null);
    getCohort(active, org).then(setDetail).catch((e) => setError(e.message));
  }, [active, org]);

  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-7">
      <PageBanner
        kicker="Cohorts"
        title="Six ways into the base"
        sub="Age is the primary audience dimension. Pick a cohort, then narrow by org type."
        window="crewm / cohorts"
        right={
          <div className="seg" role="tablist" aria-label="Organisation type">
            {ORGS.map((o) => (
              <button key={o.key} data-active={org === o.key} onClick={() => setOrg(o.key)}
                role="tab" aria-selected={org === o.key}>
                {o.label}
              </button>
            ))}
          </div>
        }
      />

      {/* Cohort tiles run across the full width: no left rail, so no dead gutter */}
      {list && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 rise d1">
          {list.cohorts.map((c) => (
            <button
              key={c.key}
              className="tile"
              data-selected={active === c.key}
              onClick={() => setActive(c.key)}
            >
              <div className="flex items-baseline justify-between gap-2 mb-2">
                <span className="font-heading text-[14px] text-[color:var(--ink-text)]">{c.label}</span>
                <span className="label-mono !text-[9px]">{pct(c.share_of_base, 0)}</span>
              </div>
              <p className="figure text-[19px]">{compact(c.total)}</p>
              <div className="ribbon mt-2.5">
                <span style={{ width: `${c.app_share * 100}%`, background: CHART.ink }} />
                <span style={{ width: `${(1 - c.app_share) * 100}%`, background: CHART.sand }} />
              </div>
              <p className="text-[10px] text-muted-foreground mt-1.5">
                {pct(c.app_share, 0)} have the app
              </p>
            </button>
          ))}
        </div>
      )}

      {!list ? <Skeleton /> : <CohortCompare cohorts={list.cohorts} />}

      {detail ? (
        <Detail detail={detail} org={org} />
      ) : (
        <div className="h-72 bg-[color:var(--muted)] rounded-xl animate-pulse" />
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function CohortCompare({ cohorts }: { cohorts: Cohort[] }) {
  const data = cohorts.map((c) => ({
    label: c.label,
    whatsapp: c.reach.whatsapp.count,
    email: c.reach.email.count,
    push: c.reach.push.with_app ?? 0,
  }));

  const booking = cohorts.map((c) => ({
    label: c.label,
    th: c.th_booked,
    hc: c.hc_booked,
    thRate: c.th_booked_of_app,
  }));

  return (
    <div className="grid grid-cols-12 gap-5 rise d2">
      <ChartFrame
        title="Deliverable reach by cohort"
        sub="Push shown as real capacity only: stale tokens excluded"
        chip="DERIVED"
        filename="cohort-reach"
        caption="Deliverable channel reach by age cohort: Crew M"
        className="col-span-12 lg:col-span-7"
        ground="dot"
      >
        <div className="h-[236px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ left: -6, right: 12, top: 6, bottom: 0 }} barGap={2}>
                <SeriesDefs />
                <CartesianGrid strokeDasharray="3 7" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" {...AXIS} />
              <YAxis tickFormatter={compact} {...AXIS} width={44} />
              <Tooltip content={<ChartTip formatter={(v) => n(v)} />}
                cursor={{ fill: "var(--cursor-fill)" }} />
              <Bar dataKey="whatsapp" name="WhatsApp" fill={GRAD.ink} radius={[4, 4, 0, 0]} barSize={17} />
              <Bar dataKey="email" name="Email" fill={GRAD.red} radius={[4, 4, 0, 0]} barSize={17} />
              <Bar dataKey="push" name="Push (real)" fill={GRAD.sand} radius={[4, 4, 0, 0]} barSize={17} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-5 mt-3 pt-3 border-t border-border flex-wrap">
          <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="w-2.5 h-2.5 rounded-sm border border-[color:var(--swatch-border)]" style={{ background: CHART.ink }} />
            <ChannelGlyph channel="whatsapp" size={14} /> WhatsApp
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="w-2.5 h-2.5 rounded-sm border border-[color:var(--swatch-border)]" style={{ background: CHART.red }} />
            <ChannelGlyph channel="email" size={14} /> Gmail
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="w-2.5 h-2.5 rounded-sm border border-[color:var(--swatch-border)]" style={{ background: CHART.sand }} />
            <ChannelGlyph channel="push" size={14} /> Plum push, deliverable only
          </span>
        </div>
      </ChartFrame>

      <ChartFrame
        title="Bookings by cohort"
        sub="Absolute bookings in the 120-day funnel window"
        chip="OBSERVED"
        filename="cohort-bookings"
        caption="Telehealth and health checkup bookings by age cohort: Crew M"
        className="col-span-12 lg:col-span-5"
      >
        <div className="h-[236px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={booking} margin={{ left: -6, right: 12, top: 6, bottom: 0 }} barGap={2}>
                <SeriesDefs />
                <CartesianGrid strokeDasharray="3 7" stroke="var(--border)" vertical={false} />
              <XAxis dataKey="label" {...AXIS} tick={{ ...AXIS.tick, fontSize: 10 }} />
              <YAxis tickFormatter={compact} {...AXIS} width={40} />
              <Tooltip content={<ChartTip formatter={(v) => n(v)} />}
                cursor={{ fill: "var(--cursor-fill)" }} />
              <Bar dataKey="th" name="Telehealth" fill={GRAD.ink} radius={[4, 4, 0, 0]} barSize={20} />
              <Bar dataKey="hc" name="Health checkup" fill={GRAD.red} radius={[4, 4, 0, 0]} barSize={20} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex items-center gap-5 mt-3 pt-3 border-t border-border">
          <Legend color={CHART.ink} label="Telehealth" />
          <Legend color={CHART.red} label="Health checkup" />
        </div>
      </ChartFrame>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Detail({ detail, org }: { detail: CohortDetail; org: string }) {
  const c = detail.cohort;
  const base = detail.base_totals;
  const push = c.reach.push;
  const realPush = push.with_app ?? 0;
  const stale = push.stale_tokens ?? 0;

  const orgRows = Object.entries(c.org_breakdown);

  // step is the share of the FIRST funnel stage, not of the preceding stage, so
  // the last bar reads as the true end-to-end conversion.
  const funnelData = (f: Cohort["th_funnel"]) =>
    f.map((s) => ({ stage: s.stage, count: s.count, step: s.cumulative }));

  const appGauge = [{ name: "app", value: c.app_share * 100, fill: CHART.ink }];

  return (
    <div className="space-y-5">
      {/* ---- Cohort header ---- */}
      <Panel ground="aurora" ticked className="p-6 rise">
        <div className="relative grid grid-cols-12 gap-7 items-start">
          <div className="col-span-12 lg:col-span-3">
            {/* meta row keeps this label/chip pair on the same baseline as
                every Stat beside it, so the row scans as one line */}
            <div className="meta-row">
              <span className="label-mono">Cohort</span>
              <Chip kind="MODELED" title="Age composition is modeled: see methodology" />
            </div>
            <h2 className="section-title !text-[34px] !leading-none">{c.label}</h2>
            <p className="figure text-[28px] mt-3">{n(c.total)}</p>
            <p className="text-[12px] text-muted-foreground mt-2">
              {pct(c.share_of_base)} of the eligible base
              {org !== "all" && <> · {ORGS.find((o) => o.key === org)?.label}</>}
            </p>
          </div>

          <div className="col-span-12 lg:col-span-3 flex items-start justify-center pt-1">
            <div className="relative w-[132px] h-[132px]">
              <ResponsiveContainer width="100%" height="100%">
                <RadialBarChart data={appGauge} innerRadius="66%" outerRadius="100%"
                  startAngle={90} endAngle={-270}>
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="value" cornerRadius={9} background={{ fill: "var(--muted)" }} />
                </RadialBarChart>
              </ResponsiveContainer>
              <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                <span className="figure text-[24px]">{pct(c.app_share, 0)}</span>
                <span className="label-mono !text-[8.5px] mt-0.5">Have app</span>
              </div>
            </div>
          </div>

          {/* two columns, not four: at four the provenance chips collided
              with the next label. Two gives each meta row room to breathe. */}
          <div className="col-span-12 lg:col-span-6 grid grid-cols-2 gap-x-8 gap-y-6">
            <Stat label="Has app" value={compact(c.app)} sub={`${pct(c.app_share)} of cohort`} size="sm" chip="OBSERVED" />
            <Stat label="No app" value={compact(c.no_app)} sub={`${pct(c.no_app_share)} of cohort`} size="sm" tone="red" chip="OBSERVED" />
            <Stat label="Active 30d" value={compact(c.mau)} sub={`${pct(c.mau_share_of_app)} of app base`} size="sm" chip="DERIVED" />
            <Stat label="Quiet 30d+" value={compact(c.app_dormant)} sub="Installed, not opened" size="sm" chip="DERIVED" />
          </div>
        </div>
      </Panel>

      {/* ---- Reach + demographics ---- */}
      <div className="grid grid-cols-12 gap-5">
        <Panel className="col-span-12 lg:col-span-5 p-5">
          <PanelHead title="Reachability" sub="Counts first: rates come from them" chip="DERIVED" />
          <div className="space-y-4">
            <BarRow label="WhatsApp" icon={<ChannelGlyph channel="whatsapp" size={15} />} value={c.reach.whatsapp.count} total={c.total} color={CHART.ink}
              note={`${n(c.reach.whatsapp.campaign_ready)} campaign-ready after DND`} />
            <BarRow label="Gmail" icon={<ChannelGlyph channel="email" size={15} />} value={c.reach.email.count} total={c.total} color={CHART.red}
              note={`${n(c.reach.email.campaign_ready)} campaign-ready after DND`} />
            <BarRow label="Push, deliverable" icon={<ChannelGlyph channel="push" size={15} />} value={realPush} total={c.total} color={CHART.sand}
              note={`${n(push.count)} reported, ${n(stale)} of those are stale tokens`} />
          </div>
          {stale > 0 && (
            <div className="mt-4 rounded-lg border border-[color:var(--red)]/25 bg-[color:var(--red)]/[0.04] p-3.5">
              <div className="flex items-start gap-2.5">
                <TriangleAlert className="w-4 h-4 text-[color:var(--red)] flex-shrink-0 mt-0.5" />
                <p className="text-[11.5px] leading-relaxed">
                  Plan push against <strong>{n(realPush)}</strong>, not {n(push.count)}. The
                  difference is stale tokens on uninstalled apps.
                </p>
              </div>
            </div>
          )}
        </Panel>

        <Panel className="col-span-12 lg:col-span-4 p-5">
          <PanelHead title="Who they are" sub="Device and gender" chip="MODELED" />
          <div className="space-y-5">
            <div>
              <div className="flex items-center gap-2 mb-2.5">
                <Smartphone className="w-3.5 h-3.5 text-muted-foreground" />
                <p className="label-mono !mb-0">Device: app base</p>
              </div>
              <SplitRibbon parts={[
                { label: "Android", value: c.android, color: CHART.ink },
                { label: "iOS", value: c.ios, color: CHART.red },
              ]} />
              <p className="text-[10.5px] text-muted-foreground mt-2.5 leading-snug">
                iOS at {pct(c.ios_share_of_app, 0)} here vs {pct(base.ios_share_of_app, 0)} base-wide.
                iOS needs explicit push opt-in.
              </p>
            </div>
            <div className="pt-4 border-t border-border">
              <p className="label-mono mb-2.5">Gender: whole cohort</p>
              <SplitRibbon parts={[
                { label: "Male", value: c.male, color: CHART.ink },
                { label: "Female", value: c.female, color: CHART.sand },
              ]} />
            </div>
            <div className="pt-4 border-t border-border">
              <div className="meta-row">
                <span className="label-mono">Real booking peak</span>
                <Chip kind="OBSERVED" />
              </div>
              <SendClock cohortKey={c.key} />
            </div>
          </div>
        </Panel>

        <Panel className="col-span-12 lg:col-span-3 p-5">
          <PanelHead title="Suppression" chip="OBSERVED" />
          <p className="figure text-[30px] text-[color:var(--red)]">{n(c.dnd)}</p>
          <p className="text-[11.5px] text-muted-foreground mt-2 leading-relaxed">
            {pct(c.dnd_share)} of this cohort carries <code className="text-[10.5px]">is_in_DND_CT</code>.
            DND is set per whole org, so every segment must exclude it explicitly.
          </p>
          <div className="mt-4 pt-4 border-t border-border">
            <p className="label-mono mb-2">Campaign-ready</p>
            <p className="figure text-[19px]">{n(c.reach.whatsapp.campaign_ready)}</p>
            <p className="text-[10.5px] text-muted-foreground mt-1">
              Reachable on WhatsApp and not suppressed
            </p>
          </div>
        </Panel>
      </div>

      {/* ---- Org drill-down ---- */}
      <Panel className="p-5">
        <PanelHead
          title="Org type breakdown"
          sub="Where this cohort sits across organisation types"
          chip="MODELED"
        />
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border">
                {["Org type", "Users", "Share", "Has app", "App %", "Active 30d",
                  "WhatsApp", "Push real", "TH booked", "HC booked", "DND"].map((h, i) => (
                  <th key={h} className={`label-mono !text-[9px] pb-2.5 ${i === 0 ? "text-left" : "text-right"}`}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {orgRows.map(([key, o]) => (
                <tr key={key} className="border-b border-border/60 last:border-0 hover:bg-[color:var(--muted)]">
                  <td className="py-2.5">
                    <span className="font-medium text-foreground">{o.label}</span>
                    <span className="label-mono !text-[9px] ml-2">{key}</span>
                  </td>
                  <td className="text-right tnum py-2.5 font-semibold">{n(o.total)}</td>
                  <td className="text-right tnum py-2.5 text-muted-foreground">{pct(o.share_of_cohort, 0)}</td>
                  <td className="text-right tnum py-2.5">{n(o.app)}</td>
                  <td className="text-right tnum py-2.5 text-muted-foreground">{pct(o.app_share, 0)}</td>
                  <td className="text-right tnum py-2.5">{n(o.mau)}</td>
                  <td className="text-right tnum py-2.5">{n(o.ready.whatsapp)}</td>
                  <td className="text-right tnum py-2.5">{n(o.ios + o.android)}</td>
                  <td className="text-right tnum py-2.5">{n(o.th_booked)}</td>
                  <td className="text-right tnum py-2.5">{n(o.hc_booked)}</td>
                  <td className="text-right tnum py-2.5 text-[color:var(--red)]">{n(o.dnd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-[10.5px] text-muted-foreground mt-3.5 pt-3.5 border-t border-border leading-relaxed">
          Org type is not a CleverTap property: there is no <code className="text-[10px]">partner_type</code> field
          in the export, so this split is modeled from employee share and adoption, and must be
          joined via org ID for a real campaign. SMB is best judged by accounts activated rather
          than employees: it is roughly 65% of accounts but only 14% of employees.
        </p>
      </Panel>

      {/* ---- Funnels ---- */}
      <div className="grid grid-cols-12 gap-5">
        {([
          ["Telehealth funnel", c.th_funnel] as const,
          ["Health checkup funnel", c.hc_funnel] as const,
        ]).map(([title, f]) => (
          <ChartFrame
            key={title}
            title={`${title}: ${c.label}`}
            sub={`${pct(f[f.length - 1].cumulative, 2)} of homepage viewers book · 120-day window`}
            chip="OBSERVED"
            filename={`${title}-${c.label}`}
            caption={`${title} for the ${c.label} cohort: Crew M`}
            className="col-span-12 lg:col-span-6"
          >
            <div className="h-[204px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={funnelData(f)} margin={{ left: -6, right: 12, top: 20, bottom: 0 }}>
                <SeriesDefs />
                <CartesianGrid strokeDasharray="3 7" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="stage" {...AXIS} interval={0} tick={{ ...AXIS.tick, fontSize: 9.5 }} />
                  <YAxis tickFormatter={compact} {...AXIS} width={42} />
                  <Tooltip content={<ChartTip formatter={(v, name) => (name === "Users" ? n(v) : pct(v))} />}
                    cursor={{ fill: "var(--cursor-fill)" }} />
                  <Bar dataKey="count" name="Users" fill={GRAD.ink} radius={[4, 4, 0, 0]} barSize={38}>
                    <LabelList dataKey="step" position="top"
                      formatter={(v: unknown) =>
                  // A decimal below 20%, or 12.76% and 13.3% both read "13%".
                  typeof v === "number" && v < 1 ? pct(v, v < 0.2 ? 1 : 0) : ""}
                      style={{ fontSize: 9.5, fill: "var(--tick)", fontFamily: "Vollkorn, Georgia, serif" }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </ChartFrame>
        ))}
      </div>

      {/* ---- Insights ---- */}
      {detail.insights.length > 0 && (
        <div>
          <div className="flex items-center gap-3 mb-4">
            <h2 className="text-[19px]">What this cohort tells you</h2>
            <span className="text-[11.5px] text-muted-foreground">
              {detail.insights.length} findings, each with its arithmetic
            </span>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {detail.insights.map((ins) => <InsightCard key={ins.id} insight={ins} />)}
          </div>
        </div>
      )}
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
      <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0 border border-[color:var(--swatch-border)]"
        style={{ background: color }} />
      {label}
    </span>
  );
}


/* --------------------------------------------------------------------------
   SendClock: the observed booking peak for this cohort, pulled from the real
   consultation clock rather than the modeled peak-hour table the panel used
   to show. Falls back silently if the intel endpoint is unavailable.
   -------------------------------------------------------------------------- */

function SendClock({ cohortKey }: { cohortKey: string }) {
  const [intel, setIntel] = useState<CohortIntel | null>(null);
  useEffect(() => {
    let live = true;
    getCohortIntel(cohortKey).then((d) => { if (live) setIntel(d); }).catch(() => {});
    return () => { live = false; };
  }, [cohortKey]);

  if (!intel) {
    return <div className="h-[52px] bg-[color:var(--muted)] rounded-lg animate-pulse" />;
  }
  const clk = intel.booking_clock;
  const hh = (h: number) => `${String(h).padStart(2, "0")}:00`;
  return (
    <div className="flex items-start gap-3">
      <div className="w-9 h-9 rounded-lg metal-cyan flex items-center justify-center flex-shrink-0">
        <Clock className="w-4 h-4 text-white" />
      </div>
      <div className="min-w-0">
        <p className="figure text-[21px]">{hh(clk.peak_hour)} IST</p>
        <p className="text-[11px] text-muted-foreground mt-1 leading-snug">
          From {n(clk.n)} real bookings. {pct(clk.morning_share, 0)} land 09:00 to
          14:00 and {pct(clk.evening_share, 0)} land 17:00 to 21:00.
        </p>
      </div>
    </div>
  );
}
