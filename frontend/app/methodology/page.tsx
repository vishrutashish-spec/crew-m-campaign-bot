"use client";

import { useEffect, useState } from "react";
import { getMethodology, n, pct, type Methodology } from "@/lib/api";
import { Panel, PanelHead, Chip, ErrorState, Skeleton, PageBanner } from "@/components/kit";
import { CheckCircle2, AlertTriangle } from "lucide-react";

export default function MethodologyPage() {
  const [data, setData] = useState<Methodology | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMethodology().then(setData).catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorState message={error} />;

  return (
    <div className="space-y-7">
      <PageBanner
        kicker="Methodology"
        title="Where every number comes from"
        sub="What is measured versus modeled, and the invariants the model asserts before it will serve a request."
        window="crewm / methodology"
      />

      {!data ? <Skeleton rows={2} /> : <Body data={data} />}
    </div>
  );
}

function Body({ data }: { data: Methodology }) {
  const p = data.provenance;

  return (
    <>
      {/* Four-way distinction */}
      <Panel className="p-6 rise d1" ground="grid">
        <PanelHead
          title="The four-way distinction"
          sub="Every figure in Crew M carries one of these labels. They are never blurred together."
        />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 relative">
          {[
            ["OBSERVED", "Read off the source of record: a CleverTap count or a documented segment export."],
            ["DERIVED", "Exact arithmetic on observed facts. No assumptions added."],
            ["MODELED", "A calibrated assumption, used where no measurement exists. Always calibrated so the totals still reconcile."],
            ["PREDICTED", "A forecast. Only the simulator produces these, and only at low confidence."],
          ].map(([kind, desc]) => (
            <div key={kind} className="panel-flush p-4">
              <Chip kind={kind} />
              <p className="text-[11.5px] text-muted-foreground mt-2.5 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </Panel>

      {/* Notes: the corrections that matter */}
      <div className="rise d2">
        <h2 className="text-[19px] mb-4">Things that are easy to get wrong</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {p.notes.map((note) => (
            <Panel key={note.title} className="p-4">
              <div className="flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-[color:var(--red)] flex-shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-[13px] leading-snug mb-1.5">{note.title}</h4>
                  <p className="text-[11.5px] text-muted-foreground leading-relaxed">{note.body}</p>
                </div>
              </div>
            </Panel>
          ))}
        </div>
      </div>

      {/* Reach decomposition */}
      <Panel className="p-5 rise d3">
        <PanelHead
          title="How reachability was decomposed"
          sub="The base and no-app segments partition the eligible base exactly, so app-installed reach falls out by subtraction."
          chip="DERIVED"
        />
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border">
                {["Channel", "Total reachable", "Of no-app segment", "Of app base", "App rate", "No-app rate"].map((h, i) => (
                  <th key={h} className={`label-mono !text-[9px] pb-2.5 ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.reach_decomposed).map(([ch, d]) => (
                <tr key={ch} className="border-b border-border/60 last:border-0">
                  <td className="py-2.5 font-medium capitalize">{ch}</td>
                  <td className="py-2.5 text-right tnum font-semibold">{n(d.total)}</td>
                  <td className="py-2.5 text-right tnum">{n(d.no_app)}</td>
                  <td className="py-2.5 text-right tnum">{n(d.app)}</td>
                  <td className="py-2.5 text-right tnum text-muted-foreground">{pct(d.app_rate)}</td>
                  <td className="py-2.5 text-right tnum text-muted-foreground">{pct(d.no_app_rate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Segment reachability source table */}
      <Panel className="p-5 rise d4">
        <PanelHead
          title="Source reachability table"
          sub="Straight from the CleverTap reachability panel. Percentages are shares of the whole segment, not of app users."
          chip="OBSERVED"
        />
        <div className="overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="border-b border-border">
                {["Segment", "Users", "Push", "Email", "WhatsApp"].map((h, i) => (
                  <th key={h} className={`label-mono !text-[9px] pb-2.5 ${i === 0 ? "text-left" : "text-right"}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(data.segment_reachability).map(([key, v]) => (
                <tr key={key} className="border-b border-border/60 last:border-0">
                  <td className="py-2.5 font-mono text-[11px]">{key}</td>
                  <td className="py-2.5 text-right tnum font-semibold">{n(v.users)}</td>
                  <td className="py-2.5 text-right tnum">{pct(v.push, 0)}</td>
                  <td className="py-2.5 text-right tnum">{pct(v.email, 0)}</td>
                  <td className="py-2.5 text-right tnum">{pct(v.whatsapp, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Funnel events */}
      <div className="grid grid-cols-12 gap-5 rise d5">
        {([["Telehealth", data.funnels.th], ["Health checkup", data.funnels.hc]] as const).map(
          ([title, stages]) => (
            <Panel key={title} className="col-span-12 lg:col-span-6 p-5">
              <PanelHead
                title={`${title} funnel events`}
                sub={data.funnels.window}
                chip="OBSERVED"
              />
              <div className="space-y-2.5">
                {stages.map((s) => (
                  <div key={s.stage} className="panel-flush p-3">
                    <div className="flex items-baseline justify-between gap-3 mb-1">
                      <span className="text-[12.5px] font-medium">{s.stage}</span>
                      <span className="tnum text-[12.5px] font-semibold">{n(s.count)}</span>
                    </div>
                    <code className="text-[10px] text-muted-foreground break-all">{s.event}</code>
                  </div>
                ))}
              </div>
              <p className="text-[10.5px] text-muted-foreground mt-3.5 pt-3.5 border-t border-border leading-relaxed">
                These are the literal event names, verified against the schema export. The Bible
                writes them in shorthand: the telehealth events all carry an{" "}
                <code className="text-[10px]">EmployeeMobileApp_Telehealth_</code> prefix and the
                checkup events a <code className="text-[10px]">healthCheckup</code> prefix. Segments
                built on the shorthand match nobody.
              </p>
            </Panel>
          )
        )}
      </div>

      {/* Derived MAU */}
      <Panel className="p-5 rise d6">
        <PanelHead title="30-day active inside the eligible base" chip="DERIVED" />
        <p className="figure text-[30px]">{n(data.mau_scoped.value)}</p>
        <p className="text-[11.5px] text-muted-foreground mt-2.5 leading-relaxed max-w-3xl">
          {data.mau_scoped.provenance}
        </p>
      </Panel>

      {/* Invariants */}
      <Panel className="p-5 rise d6">
        <PanelHead
          title="Invariants the model asserts"
          sub="Checked at startup. If any of these fails the API refuses to serve a request rather than return a wrong number."
          chip="OBSERVED"
          right={
            <span className="label-mono">{data.checks.length} checks</span>
          }
        />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-x-6 gap-y-2">
          {data.checks.map((c) => (
            <div key={c} className="flex items-start gap-2 text-[11.5px]">
              <CheckCircle2 className="w-3.5 h-3.5 text-[color:var(--success)] flex-shrink-0 mt-0.5" />
              <span className="text-muted-foreground font-mono">{c}</span>
            </div>
          ))}
        </div>
      </Panel>

      {/* Provenance detail */}
      <Panel className="p-5 rise d6">
        <PanelHead title="Field-level provenance" />
        <div className="space-y-5">
          <ProvBlock kind="OBSERVED" source={p.observed.source} fields={p.observed.fields}
            extra={`Pulled ${p.observed.pulled_at} · ${p.observed.window_days}-day window`} />
          <ProvBlock kind="DERIVED" source={p.derived.how} fields={p.derived.fields} />
          <div>
            <Chip kind="MODELED" />
            <div className="mt-2.5 space-y-2.5">
              {Object.entries(p.modeled)
                .filter(([k]) => k !== "fields")
                .map(([k, v]) => (
                  <div key={k} className="panel-flush p-3.5">
                    <p className="label-mono mb-1.5">{k}</p>
                    <p className="text-[11.5px] text-muted-foreground leading-relaxed">{String(v)}</p>
                  </div>
                ))}
            </div>
          </div>
          <div className="panel-flush p-3.5">
            <p className="label-mono mb-1.5">CleverTap scope</p>
            <p className="text-[11.5px] text-muted-foreground leading-relaxed">{p.ct_live_scope}</p>
          </div>
          <div className="panel-flush p-3.5">
            <p className="label-mono mb-1.5">DAU method</p>
            <p className="text-[11.5px] text-muted-foreground leading-relaxed">{p.dau_method}</p>
          </div>
        </div>
      </Panel>
    </>
  );
}

function ProvBlock({
  kind, source, fields, extra,
}: {
  kind: string;
  source: string;
  fields: string[];
  extra?: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2.5 flex-wrap">
        <Chip kind={kind} />
        <span className="text-[12px] text-foreground">{source}</span>
      </div>
      {extra && <p className="text-[10.5px] text-muted-foreground mt-1.5">{extra}</p>}
      <div className="flex flex-wrap gap-1.5 mt-2.5">
        {fields.map((f) => (
          <code key={f} className="text-[10px] px-2 py-1 rounded bg-[color:var(--muted)] border border-border">
            {f}
          </code>
        ))}
      </div>
    </div>
  );
}
