"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getSimOptions, getCohorts, simulate, getCopyOptions, generateCopy, analyzeCopy,
  n, compact, pct, CHART,
  type SimOptions, type SimResult, type Cohort,
  type CopyOptions, type CopyGenResponse, type CopyVariant,
  type CopyAnalysis, type CopyPrediction,
  askAssistant, getRules, SPECTRUM,
  type AssistantReply, type DecisionParam,
  type FunnelExplain, type TimingDetail,
} from "@/lib/api";
import {
  Panel, PanelHead, ChartFrame, Chip, Stat, ErrorState, ChartTip, AXIS, SeriesDefs, GRAD,
  PageBanner, MacBar, ProvenanceNote, StepHead,
} from "@/components/kit";
import { ChannelGlyph, ChannelTickY, PlumGlyph, WhatsAppGlyph, GmailGlyph } from "@/components/logos";
import { WaMessage } from "@/components/wa-message";
import {
  CartesianGrid,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList,
  PieChart, Pie,
} from "recharts";
import {
  ArrowRight, TriangleAlert, RotateCw, Check, Clock, Users, Radio,
  Sparkles, PenLine, TrendingUp, TrendingDown, MessageCircle, ChevronDown, Send,
} from "lucide-react";

export default function SimulatePage() {
  const [opts, setOpts] = useState<SimOptions | null>(null);
  const [copyOpts, setCopyOpts] = useState<CopyOptions | null>(null);
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [selected, setSelected] = useState<string[]>(["26_35"]);
  const [org, setOrg] = useState("all");
  const [objective, setObjective] = useState("th_activation");
  const [channel, setChannel] = useState("");           // "" = auto
  const [sendHour, setSendHour] = useState<string>("");
  const [excludeDnd, setExcludeDnd] = useState(true);
  const [excludeStale, setExcludeStale] = useState(true);

  const [result, setResult] = useState<SimResult | null>(null);
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);

  useEffect(() => {
    getSimOptions().then(setOpts).catch((e) => setError(e.message));
    getCopyOptions().then(setCopyOpts).catch(() => {});
  }, []);

  useEffect(() => {
    getCohorts(org).then((r) => setCohorts(r.cohorts)).catch(() => {});
  }, [org]);

  const run = useCallback(async () => {
    if (!selected.length) return;
    setRunning(true);
    setRunError(null);
    try {
      setResult(
        await simulate({
          objective,
          cohort_keys: selected,
          org: org === "all" ? null : org,
          channel: channel || null,
          send_hour: sendHour === "" ? null : Number(sendHour),
          exclude_dnd: excludeDnd,
          exclude_no_app_for_push: excludeStale,
        })
      );
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setRunning(false);
    }
  }, [objective, selected, org, channel, sendHour, excludeDnd, excludeStale]);

  if (error) return <ErrorState message={error} />;

  const selectedTotal = cohorts
    .filter((c) => selected.includes(c.key))
    .reduce((s, c) => s + c.total, 0);

  // The channel the copy studio writes for: an explicit pick wins, otherwise
  // the channel the last simulation recommended, otherwise WhatsApp.
  const copyChannel = channel || result?.channel.selected || "whatsapp";

  return (
    <div className="space-y-7">
      <PageBanner
        kicker="Simulator"
        title="Plan a campaign"
        sub="Pick cohorts, narrow the audience, size it against real reachability, then write the message in Plum's own voice."
        window="crewm / simulator"
        right={<Chip kind="PREDICTED" title="Funnel projections use modeled priors at low confidence" />}
      />

      {/* ---------- STEP 1 ---------- */}
      <Panel className="p-5 rise d1" ground="dot">
        <StepHead
          step={1}
          title="Choose cohorts"
          sub="Cohorts are the primary audience dimension. Select one or more."
          chip="MODELED"
          right={
            <div className="flex items-center gap-2">
              <button className="btn !px-2.5 !py-1.5 !text-[11px]"
                onClick={() => setSelected(cohorts.map((c) => c.key))}>
                All
              </button>
              <button className="btn !px-2.5 !py-1.5 !text-[11px]"
                onClick={() => setSelected([])}>
                None
              </button>
            </div>
          }
        />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 relative">
          {cohorts.map((c) => {
            const on = selected.includes(c.key);
            return (
              <button
                key={c.key}
                className="tile"
                data-selected={on}
                onClick={() =>
                  setSelected((prev) =>
                    prev.includes(c.key) ? prev.filter((k) => k !== c.key) : [...prev, c.key]
                  )
                }
              >
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="font-heading text-[13.5px] text-[color:var(--ink-text)]">{c.label}</span>
                  <span
                    className={`w-4 h-4 rounded-[5px] border flex items-center justify-center flex-shrink-0 ${
                      on ? "metal-cyan border-transparent" : "border-[color:var(--input)]"
                    }`}
                  >
                    {on && <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />}
                  </span>
                </div>
                <p className="figure text-[18px]">{compact(c.total)}</p>
                <p className="text-[10px] text-muted-foreground mt-1.5">
                  {compact(c.app)} app · {pct(c.app_share, 0)}
                </p>
              </button>
            );
          })}
        </div>
        {selected.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border flex items-center gap-2.5 relative">
            <Users className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-[12px] text-muted-foreground">
              {selected.length} cohort{selected.length !== 1 ? "s" : ""} selected:{" "}
              <span className="font-semibold text-foreground tnum">{n(selectedTotal)}</span> people
              before any objective or channel filter
            </span>
          </div>
        )}
      </Panel>

      {/* ---------- STEP 2 ---------- */}
      <Panel className="p-5 rise d2">
        <StepHead step={2} title="Narrow the audience" sub="Everything here filters the cohorts you picked above" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          <Field label="Objective" hint={opts?.objectives.find((o) => o.key === objective)?.desc}>
            <select className="field" value={objective} onChange={(e) => setObjective(e.target.value)}>
              {opts?.objectives.map((o) => (
                <option key={o.key} value={o.key}>{o.label}</option>
              ))}
            </select>
          </Field>

          <Field label="Org type" hint="Modeled, not a CleverTap property">
            <select className="field" value={org} onChange={(e) => setOrg(e.target.value)}>
              <option value="all">All org types</option>
              {opts?.org_types.map((o) => (
                <option key={o.key} value={o.key}>{o.label}</option>
              ))}
            </select>
          </Field>

          <Field label="Send hour" hint="Real booking peaks are 11:00 and 18:00 to 19:00 IST">
            <select className="field" value={sendHour} onChange={(e) => setSendHour(e.target.value)}>
              <option value="">Auto, observed booking peak</option>
              {Array.from({ length: 24 }, (_, i) => (
                <option key={i} value={i}>{String(i).padStart(2, "0")}:00</option>
              ))}
            </select>
          </Field>
        </div>

        {/* Channel picker with real logos */}
        <div className="mt-5">
          <label className="label-mono block mb-2.5">Channel</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <button className="tile !py-3" data-selected={channel === ""} onClick={() => setChannel("")}>
              <span className="flex items-center gap-2.5">
                <span className="w-[22px] h-[22px] rounded-md metal-cyan flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-3 h-3 text-white" />
                </span>
                <span>
                  <span className="text-[12.5px] font-medium block">Auto</span>
                  <span className="text-[10px] text-muted-foreground">Widest real reach</span>
                </span>
              </span>
            </button>
            <button className="tile !py-3" data-selected={channel === "whatsapp"} onClick={() => setChannel("whatsapp")}>
              <span className="flex items-center gap-2.5">
                <WhatsAppGlyph size={22} />
                <span>
                  <span className="text-[12.5px] font-medium block">WhatsApp</span>
                  <span className="text-[10px] text-muted-foreground">No app needed</span>
                </span>
              </span>
            </button>
            <button className="tile !py-3" data-selected={channel === "email"} onClick={() => setChannel("email")}>
              <span className="flex items-center gap-2.5">
                <GmailGlyph size={22} />
                <span>
                  <span className="text-[12.5px] font-medium block">Email</span>
                  <span className="text-[10px] text-muted-foreground">Work inbox</span>
                </span>
              </span>
            </button>
            <button className="tile !py-3" data-selected={channel === "push"} onClick={() => setChannel("push")}>
              <span className="flex items-center gap-2.5">
                <PlumGlyph size={22} />
                <span>
                  <span className="text-[12.5px] font-medium block">Push</span>
                  <span className="text-[10px] text-muted-foreground">App base only</span>
                </span>
              </span>
            </button>
          </div>
        </div>

        <div className="mt-5 pt-5 border-t border-border flex flex-wrap items-center gap-6">
          <Toggle checked={excludeDnd} onChange={setExcludeDnd}
            label="Exclude DND-suppressed"
            hint="is_in_DND_CT, must be checked by every campaign" />
          <Toggle checked={excludeStale} onChange={setExcludeStale}
            label="Exclude stale push tokens"
            hint="No-app users whose tokens were never invalidated" />
        </div>

        <div className="mt-5 pt-5 border-t border-border flex items-center gap-4 flex-wrap">
          <button
            onClick={run}
            disabled={running || selected.length === 0}
            className="btn btn-primary !px-7 !py-3 !text-[13.5px]"
          >
            {running ? <RotateCw className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
            {running ? "Sizing the audience" : result ? "Re-run simulation" : "Run simulation"}
          </button>
          {selected.length === 0 && (
            <span className="text-[12px] text-[color:var(--red)]">Select at least one cohort</span>
          )}
          {runError && <span className="text-[12px] text-[color:var(--red)]">{runError}</span>}
        </div>
      </Panel>

      {/* ---------- STEP 3: result ---------- */}
      {result ? (
        <Result result={result} />
      ) : (
        <Panel className="p-12 text-center rise d3" ticked>
          <div className="w-14 h-14 rounded-xl metal-ink flex items-center justify-center mx-auto mb-4">
            <Radio className="w-6 h-6 text-white" strokeWidth={1.6} />
          </div>
          <h3 className="text-[17px] mb-2">Nothing simulated yet</h3>
          <p className="text-[12.5px] text-muted-foreground max-w-md mx-auto leading-relaxed">
            Pick cohorts and an objective, then run it. Audience sizing comes straight out of the
            cohort model; the funnel projection is a modeled prior and is labelled as such.
          </p>
        </Panel>
      )}

      {/* ---------- STEP 4: copy studio ---------- */}
      <CopyStudio
        objective={objective}
        cohortKeys={selected}
        channel={copyChannel}
        channelWasAuto={!channel}
        audienceSent={result?.audience.sent ?? null}
        copyOpts={copyOpts}
      />

      {/* ---------- STEP 5: SIGNAL ----------
          Rendered non-compact so it brings its own window chrome and aurora
          ground. A bare phone floating in a wide empty panel reads thin; the
          framed version keeps the phone as the centrepiece with a surface
          under it. */}
      <div className="rise">
        <div className="mb-4">
          <span className="step-num">STEP 5</span>
          <div className="flex items-center gap-2.5 flex-wrap">
            <h3 className="section-title">Ask SIGNAL</h3>
            <Chip kind="DERIVED" />
          </div>
          <p className="text-[12.5px] text-muted-foreground mt-1.5">
            Grounded answers only. Every reply cites the figures it used and scores
            itself against the published rubric.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ==========================================================================
   Copy studio
   ========================================================================== */

function CopyStudio({
  objective, cohortKeys, channel, channelWasAuto, audienceSent, copyOpts,
}: {
  objective: string;
  cohortKeys: string[];
  channel: string;
  channelWasAuto: boolean;
  audienceSent: number | null;
  copyOpts: CopyOptions | null;
}) {
  const [angle, setAngle] = useState<string | null>(null);
  const [gen, setGen] = useState<CopyGenResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [customText, setCustomText] = useState("");
  const [customTitle, setCustomTitle] = useState("");
  const [customResult, setCustomResult] = useState<{ analysis: CopyAnalysis; prediction: CopyPrediction } | null>(null);
  const [customBusy, setCustomBusy] = useState(false);

  const angles = copyOpts?.angles[objective] ?? [];

  // Selection changed: previous output no longer describes the current plan.
  useEffect(() => {
    setGen(null);
    setAngle(null);
  }, [objective, channel, cohortKeys.join(",")]);   // eslint-disable-line react-hooks/exhaustive-deps

  async function doGenerate(nextAngle?: string | null) {
    if (!cohortKeys.length) return;
    setBusy(true);
    setErr(null);
    try {
      setGen(await generateCopy({
        objective,
        cohort_keys: cohortKeys,
        channel,
        angle: nextAngle === undefined ? angle : nextAngle,
        audience_sent: audienceSent,
      }));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setBusy(false);
    }
  }

  async function doAnalyze() {
    if (!customText.trim() || !cohortKeys.length) return;
    setCustomBusy(true);
    try {
      const r = await analyzeCopy({
        text: customText,
        title: channel === "push" || channel === "email" ? customTitle || null : null,
        channel,
        objective,
        cohort_key: cohortKeys[0],
        audience_sent: audienceSent,
      });
      setCustomResult({ analysis: r.analysis, prediction: r.prediction });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setCustomBusy(false);
    }
  }

  return (
    <Panel className="p-5 rise d4" ground="grid">
      <StepHead
        step={4}
        title="Copy studio"
        sub="Variants assembled from Plum's approved copy library, disciplined per channel, with predicted performance for this exact audience"
        chip="GENERATED"
        right={
          <span className="flex items-center gap-2 text-[11.5px] text-muted-foreground">
            Writing for
            <ChannelGlyph channel={channel} size={16} />
            <span className="font-medium text-foreground">
              {channel === "whatsapp" ? "WhatsApp" : channel === "email" ? "Email" : "Push"}
            </span>
            {channelWasAuto && <span className="text-muted-foreground">(auto)</span>}
          </span>
        }
      />

      {/* Angle chips */}
      <div className="relative flex items-center gap-2 flex-wrap mb-4">
        <span className="label-mono mr-1">Angle</span>
        <button
          className="btn !px-3 !py-1.5 !text-[11px]"
          style={angle === null ? { borderColor: "var(--cyan)", color: "var(--cyan-deep)", background: "var(--cyan-wash)" } : undefined}
          onClick={() => { setAngle(null); if (gen) doGenerate(null); }}
        >
          Best fit per band
        </button>
        {angles.map((a) => (
          <button
            key={a.key}
            className="btn !px-3 !py-1.5 !text-[11px]"
            style={angle === a.key ? { borderColor: "var(--cyan)", color: "var(--cyan-deep)", background: "var(--cyan-wash)" } : undefined}
            onClick={() => { setAngle(a.key); if (gen) doGenerate(a.key); }}
            title={a.label}
          >
            {a.label.split(":")[0]}
          </button>
        ))}
      </div>

      <div className="relative flex items-center gap-4 flex-wrap">
        <button
          onClick={() => doGenerate()}
          disabled={busy || cohortKeys.length === 0}
          className="btn btn-primary !px-6 !py-2.5 !text-[13px]"
        >
          {busy ? <RotateCw className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {busy ? "Writing" : gen ? "Regenerate" : "Generate copy"}
        </button>
        {audienceSent ? (
          <span className="text-[11.5px] text-muted-foreground">
            Predictions sized against the simulated send of{" "}
            <span className="font-semibold text-foreground tnum">{n(audienceSent)}</span>
          </span>
        ) : (
          <span className="text-[11.5px] text-muted-foreground">
            Run the simulation first and predictions gain absolute counts
          </span>
        )}
        {err && <span className="text-[12px] text-[color:var(--red)]">{err}</span>}
      </div>

      {/* Variants */}
      {gen && (
        <div className="relative mt-6 space-y-6">
          {gen.groups.map((g) => (
            <div key={g.band}>
              <div className="flex items-center gap-2.5 mb-3">
                <h4 className="text-[14px]">{g.band_label}</h4>
                <span className="text-[11px] text-muted-foreground">
                  {g.variants.length} variant{g.variants.length !== 1 ? "s" : ""}
                </span>
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                {g.variants.map((v, i) => (
                  <VariantCard key={v.id} v={v} objective={objective} angle={angle}
                    offset={i} />
                ))}
              </div>
            </div>
          ))}
          <p className="text-[10.5px] text-muted-foreground pt-1">
            {gen.discipline[gen.channel]}
          </p>
        </div>
      )}

      {/* Custom copy analyzer */}
      <div className="relative mt-6 pt-5 border-t border-border">
        <div className="flex items-center gap-2 mb-3">
          <PenLine className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-[13px] font-medium">Or check your own copy</span>
          <span className="text-[11px] text-muted-foreground">
            scored against the same discipline rules, for the {cohortKeys.length ? "first selected cohort" : "selected cohort"}
          </span>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="space-y-2.5">
            {(channel === "push" || channel === "email") && (
              <input className="field" placeholder={channel === "push" ? "Push title" : "Email subject"}
                value={customTitle} onChange={(e) => setCustomTitle(e.target.value)} />
            )}
            <textarea className="field min-h-[110px]" placeholder="Paste the message body"
              value={customText} onChange={(e) => setCustomText(e.target.value)} />
            <button onClick={doAnalyze} disabled={customBusy || !customText.trim()}
              className="btn !px-4 !py-2 !text-[12px]">
              {customBusy ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
              Analyze
            </button>
          </div>
          {customResult && (
            <div className="space-y-3">
              {/* Preview your own words in the real message shape, not just scored */}
              {channel === "whatsapp" && customText.trim() && (
                <WaMessage body={customText} objective={objective} angle={angle}
                  category={customResult.analysis.category} />
              )}
              <AnalysisBlock analysis={customResult.analysis} prediction={customResult.prediction} channel={channel} />
            </div>
          )}
        </div>
      </div>
    </Panel>
  );
}

/* ---------------------------------------------------------------- variants */

function VariantCard({ v, objective, angle, offset }: {
  v: CopyVariant; objective: string; angle: string | null; offset: number;
}) {
  const [open, setOpen] = useState(false);
  const a = v.analysis;

  return (
    <div className="mac-panel">
      <MacBar title={
        v.channel === "whatsapp" ? `whatsapp / ${a.category}` :
        v.channel === "push" ? "plum app / push" : "email / marketing"
      } />
      <div className="p-4">
        {/* Message preview */}
        {v.channel === "whatsapp" && (
          <WaMessage body={v.body} objective={objective} angle={angle}
            offset={offset} category={a.category} />
        )}
        {v.channel === "push" && (
          <div className="flex items-start gap-2.5 rounded-xl border border-border bg-[color:var(--muted)] px-3.5 py-3">
            <PlumGlyph size={26} />
            <div className="min-w-0">
              <p className="text-[12.5px] font-semibold">{v.title}</p>
              <p className="text-[12px] text-muted-foreground leading-snug mt-0.5">{v.body}</p>
            </div>
          </div>
        )}
        {v.channel === "email" && (
          <div className="rounded-xl border border-border overflow-hidden">
            <div className="flex items-center gap-2.5 px-3.5 py-2.5 bg-[color:var(--muted)] border-b border-border">
              <GmailGlyph size={16} />
              <div className="min-w-0">
                <p className="text-[12.5px] font-semibold truncate">{v.title}</p>
                {v.preheader && <p className="text-[10.5px] text-muted-foreground truncate">{v.preheader}</p>}
              </div>
            </div>
            <p className="text-[12px] leading-relaxed whitespace-pre-line px-3.5 py-3">{v.body}</p>
          </div>
        )}

        {/* Discipline strip */}
        <div className="flex items-center gap-2 flex-wrap mt-3">
          <Chip kind={a.category === "utility" ? "OBSERVED" : "RECOMMENDED"}
            title={a.category_basis} />
          <span className={`chip ${a.category === "utility" ? "chip-derived" : "chip-predicted"}`}>
            {v.channel === "whatsapp" ? `WA ${a.category}` : a.category}
          </span>
          <MeterChip
            label={v.channel === "push" ? `title ${a.title_chars}` : `${a.chars} chars`}
            ok={!a.checks.some((c) => c.status === "fail" && c.name.toLowerCase().includes("char"))}
          />
          <MeterChip label={`${a.emoji_count} emoji (${a.emoji_range_for_band[0]}-${a.emoji_range_for_band[1]} fits)`}
            ok={a.emoji_count >= a.emoji_range_for_band[0] - 1 && a.emoji_count <= a.emoji_range_for_band[1]} />
          {a.personalized && <MeterChip label="personalised" ok />}
          <span className="ml-auto text-[11px] tnum">
            <span className="text-muted-foreground">style</span>{" "}
            <span className={`font-semibold ${a.style_score >= 85 ? "text-[color:var(--success)]" : a.style_score >= 65 ? "text-[color:var(--warning)]" : "text-[color:var(--red)]"}`}>
              {a.style_score}
            </span>
          </span>
        </div>

        {/* Prediction */}
        <PredictionRow p={v.prediction} />

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
          <span className="text-[10px] text-muted-foreground">{v.source}</span>
          <button onClick={() => setOpen(!open)}
            className="text-[11px] text-[color:var(--cyan-deep)] hover:underline">
            {open ? "Hide checks" : `${a.checks.length} discipline checks`}
          </button>
        </div>
        {open && <ChecksList checks={a.checks} factors={v.prediction.factors} />}
      </div>
    </div>
  );
}

function PredictionRow({ p }: { p: CopyPrediction }) {
  const [why, setWhy] = useState(false);
  const cell = (label: string, base: number, pred: number, delta: number, dp = 1) => (
    <div>
      <p className="label-mono !text-[8.5px] mb-1">{label}</p>
      <p className="text-[14px] font-semibold tnum font-heading text-[color:var(--ink-text)]">
        {pct(pred, dp)}
        {Math.abs(delta) >= 0.005 && (
          <span className={`ml-1.5 text-[10px] font-sans inline-flex items-center gap-0.5 ${delta > 0 ? "text-[color:var(--success)]" : "text-[color:var(--red)]"}`}>
            {delta > 0 ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
            {delta > 0 ? "+" : ""}{(delta * 100).toFixed(0)}%
          </span>
        )}
      </p>
      <p className="text-[9.5px] text-muted-foreground tnum">baseline {pct(base, dp)}</p>
    </div>
  );
  return (
    <div className="mt-3 rounded-lg border border-border bg-[color:var(--card)] px-3.5 py-2.5">
      <div className="meta-row !mb-2">
        <Chip kind="PREDICTED" title={p.confidence_reason} />
        {/* A confidence caveat belongs on copy someone is testing. Crew M's own
            recommendation states what it was modelled from instead. */}
        <span className="text-[10px] text-muted-foreground">
          {p.from_library
            ? `modelled from ${p.library_size} shipped messages, deltas vs channel prior`
            : `${p.confidence} confidence, deltas vs channel prior`}
        </span>
        <button onClick={() => setWhy(!why)}
          className="ml-auto text-[10px] text-[color:var(--cyan-deep)] hover:underline flex-shrink-0">
          {why ? "Hide basis" : "What predicted this"}
        </button>
      </div>

      {why && (
        <div className="mb-3 rounded-lg border border-border bg-[color:var(--muted)] p-3 space-y-2">
          {([
            ["Copy", p.basis.copy],
            ["Delivery, open, click", p.basis.delivery_open_click],
            ["Convert", p.basis.convert],
          ] as const).map(([k, v]) => (
            <div key={k}>
              <span className="label-mono !text-[8.5px]">{k}</span>
              <p className="text-[10.5px] text-muted-foreground leading-relaxed mt-0.5">{v}</p>
            </div>
          ))}
          {p.factors.length > 0 && (
            <div className="pt-2 border-t border-border">
              <span className="label-mono !text-[8.5px]">Style rules that moved it</span>
              <ul className="mt-1 space-y-1">
                {p.factors.map((f) => (
                  <li key={f} className="text-[10.5px] text-muted-foreground leading-relaxed flex gap-1.5">
                    <span className="text-[color:var(--cyan-deep)]">·</span>{f}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-[10px] text-muted-foreground pt-2 border-t border-border">
            {p.confidence_reason}
          </p>
        </div>
      )}
      <div className="grid grid-cols-3 md:grid-cols-4 gap-3">
        {cell("Open", p.baseline.open, p.predicted.open, p.delta.open)}
        {cell("Click", p.baseline.click, p.predicted.click, p.delta.click)}
        {cell("Convert", p.baseline.convert, p.predicted.convert, p.delta.convert)}
        {p.funnel && (
          <div>
            <p className="label-mono !text-[8.5px] mb-1">Est. conversions</p>
            <p className="text-[14px] font-semibold tnum font-heading text-[color:var(--red)]">
              {n(p.funnel.converted)}
            </p>
            <p className="text-[9.5px] text-muted-foreground tnum">of {n(p.funnel.sent)} sent</p>
          </div>
        )}
      </div>
    </div>
  );
}

function ChecksList({ checks, factors }: { checks: CopyAnalysis["checks"]; factors: string[] }) {
  return (
    <div className="mt-2.5 space-y-1.5">
      {checks.map((c) => (
        <div key={c.name} className="flex items-start gap-2 text-[11px]">
          <span className={`mt-[3px] w-2 h-2 rounded-full flex-shrink-0 ${
            c.status === "pass" ? "bg-[color:var(--success)]"
            : c.status === "warn" ? "bg-[color:var(--warning)]" : "bg-[color:var(--red)]"
          }`} />
          <span className="text-foreground font-medium">{c.name}</span>
          <span className="text-muted-foreground">{c.detail}</span>
        </div>
      ))}
      {factors.length > 0 && (
        <div className="rounded-md bg-[color:var(--cyan-wash)] border border-[color:var(--cyanw-border)] px-3 py-2 mt-2">
          <p className="label-mono !text-[color:var(--cyan-deep)] mb-1">Prediction factors</p>
          {factors.map((f) => (
            <p key={f} className="text-[10.5px] text-foreground leading-relaxed">· {f}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function AnalysisBlock({ analysis, prediction, channel }: {
  analysis: CopyAnalysis; prediction: CopyPrediction; channel: string;
}) {
  return (
    <div className="panel-flush p-4">
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <span className={`chip ${analysis.category === "utility" ? "chip-derived" : "chip-predicted"}`}>
          {channel === "whatsapp" ? `WA ${analysis.category}` : analysis.category}
        </span>
        <span className="text-[11px] text-muted-foreground">{analysis.category_basis}</span>
        <span className="ml-auto text-[11px] tnum">
          style <span className="font-semibold">{analysis.style_score}</span>
        </span>
      </div>
      <PredictionRow p={prediction} />
      <ChecksList checks={analysis.checks} factors={prediction.factors} />
    </div>
  );
}

function MeterChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-[10px] tnum ${
      ok ? "border-border text-muted-foreground bg-[color:var(--card)]"
        : "border-[color:var(--red)]/40 text-[color:var(--red)] bg-[color:var(--red)]/[0.05]"
    }`}>
      {label}
    </span>
  );
}

/* ==========================================================================
   Simulation result (unchanged logic, channel chart now carries real logos)
   ========================================================================== */

function Result({ result: r }: { result: SimResult }) {
  // Every stage is expressed as a share of SENT, the first stage, not of the
  // stage before it. Computed from the counts themselves so the label and the
  // bar can never disagree: the last one is the true end-to-end rate.
  const ofSent = (count: number) => (r.funnel.sent ? count / r.funnel.sent : 0);
  const funnel = [
    { stage: "Sent", count: r.funnel.sent, rate: 1 },
    { stage: "Delivered", count: r.funnel.delivered, rate: ofSent(r.funnel.delivered) },
    { stage: "Opened", count: r.funnel.opened, rate: ofSent(r.funnel.opened) },
    { stage: "Clicked", count: r.funnel.clicked, rate: ofSent(r.funnel.clicked) },
    { stage: "Converted", count: r.funnel.converted, rate: ofSent(r.funnel.converted) },
  ];

  const channelData = Object.entries(r.channel.options).map(([key, v]) => ({
    channel: v.label,
    addressable: v.addressable,
    isChosen: key === r.channel.selected,
  }));

  return (
    <div className="space-y-5 rise">
      <Panel ground="aurora" ticked className="p-6">
        <div className="relative grid grid-cols-12 gap-7 items-start">
          <div className="col-span-12 lg:col-span-5">
            <div className="meta-row">
              <span className="label-mono">Addressable audience</span>
              <Chip kind="DERIVED" />
            </div>
            <p className="figure text-[46px]">{n(r.audience.addressable)}</p>
            <p className="text-[12px] text-muted-foreground mt-2.5 leading-relaxed flex items-center gap-1.5 flex-wrap">
              {r.selection.cohorts.join(", ")} · {r.selection.org} · via
              <ChannelGlyph channel={r.channel.selected} size={15} />
              <strong className="text-foreground">{r.channel.selected_label}</strong>
            </p>
          </div>
          <div className="col-span-12 lg:col-span-7 grid grid-cols-2 sm:grid-cols-4 gap-5">
            <Stat label="Cohort size" value={compact(r.selection.cohort_total)} sub="Before filters" size="sm" />
            <Stat label="Objective pool" value={compact(r.audience.objective_pool)}
              sub={r.audience.pool_description} size="sm" />
            <Stat label="Control group" value={n(r.audience.control_group)} sub="5% held back, flat" size="sm" />
            <Stat label="Will send to" value={n(r.audience.sent)} sub="Audience minus control" size="sm" tone="cyan" />
          </div>
        </div>
      </Panel>

      {r.warnings.length > 0 && (
        <div className="space-y-3">
          {r.warnings.map((w, i) => (
            <div key={i} className="panel-flush p-4 border-[color:var(--red)]/30 bg-[color:var(--red)]/[0.035]">
              <div className="flex items-start gap-2.5">
                <TriangleAlert className="w-4 h-4 text-[color:var(--red)] flex-shrink-0 mt-0.5" />
                <p className="text-[12px] leading-relaxed">{w}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {r.decision && <DecisionBreakdown result={r} />}

      <div className="grid grid-cols-12 gap-5">
        <ChartFrame
          title="Channel choice"
          sub="How many of the objective pool each channel can actually reach"
          chip="DERIVED"
          filename="channel-choice"
          caption="Addressable audience by channel. Crew M"
          className="col-span-12 lg:col-span-5"
        >
          <div className="h-[196px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={channelData} layout="vertical"
                margin={{ left: 14, right: 44, top: 4, bottom: 4 }}>
                <SeriesDefs />
                <XAxis type="number" tickFormatter={compact} {...AXIS} />
                <YAxis type="category" dataKey="channel" width={96}
                  tick={<ChannelTickY />} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTip formatter={(v) => n(v)} />}
                  cursor={{ fill: "var(--cursor-fill)" }} />
                <Bar dataKey="addressable" name="Addressable" radius={[0, 5, 5, 0]} barSize={26}>
                  {channelData.map((d) => (
                    <Cell key={d.channel} fill={d.isChosen ? GRAD.ink : GRAD.sand} />
                  ))}
                  <LabelList dataKey="addressable" position="right"
                    formatter={(v: unknown) => (typeof v === "number" ? compact(v) : "")}
                    style={{ fontSize: 10.5, fill: "var(--tick)", fontFamily: "Vollkorn, Georgia, serif" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 pt-3 border-t border-border flex items-center gap-4 flex-wrap">
            <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
              <span className="w-2.5 h-2.5 rounded-sm border border-[color:var(--swatch-border)]" style={{ background: CHART.ink }} />
              Selected ({r.channel.label.toLowerCase()})
            </span>
            <span className="text-[11px] text-muted-foreground">
              Push counts only devices that can actually receive it
            </span>
          </div>
        </ChartFrame>

        <ChartFrame
          title="Projected funnel"
          sub="Delivery, open and click are learned from this account's own campaigns for push and email. WhatsApp stays a labelled prior."
          chip="PREDICTED"
          filename="projected-funnel"
          caption="Projected campaign funnel, PREDICTED from modeled priors. Crew M"
          className="col-span-12 lg:col-span-7"
        >
          <div className="h-[196px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={funnel} margin={{ left: -6, right: 12, top: 20, bottom: 0 }}>
                <SeriesDefs />
                <CartesianGrid strokeDasharray="3 7" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="stage" {...AXIS} />
                <YAxis tickFormatter={compact} {...AXIS} width={44} />
                <Tooltip content={<ChartTip formatter={(v, name) => (name === "Users" ? n(v) : pct(v))} />}
                  cursor={{ fill: "var(--cursor-fill)" }} />
                <Bar dataKey="count" name="Users" radius={[5, 5, 0, 0]} barSize={44}>
                  {funnel.map((d, i) => (
                    <Cell key={d.stage} fill={i === funnel.length - 1 ? GRAD.red : GRAD.ink} />
                  ))}
                  <LabelList dataKey="rate" position="top"
                    formatter={(v: unknown) => (typeof v === "number" && v < 1 ? pct(v, 1) : "")}
                    style={{ fontSize: 10, fill: "var(--tick)", fontFamily: "Vollkorn, Georgia, serif" }} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-border">
            <Stat label="Delivered" value={pct(r.funnel.delivery_rate)} size="sm" />
            <Stat label="Opened" value={pct(r.funnel.open_rate)} size="sm" />
            <Stat label="Clicked" value={pct(r.funnel.click_rate)} size="sm" />
            <Stat label="End to end" value={pct(r.funnel.conversion_rate, 2)} size="sm" tone="red" />
          </div>
        </ChartFrame>
      </div>

      {r.funnel_explain && <FunnelExplainer fx={r.funnel_explain} />}
      {r.timing_detail && <TimingPanel t={r.timing_detail} />}

      <div className="grid grid-cols-12 gap-5">
        <Panel className="col-span-12 lg:col-span-8 p-5">
          <PanelHead title="How much to trust this" chip="PREDICTED" />
          <div className="flex items-start gap-4">
            <div className="px-3 py-1.5 rounded-md bg-[color:var(--amber-bg)] border border-[color:var(--amber-border)] flex-shrink-0">
              <span className="label-mono !text-[color:var(--amber-text)] !text-[10px]">
                {r.confidence} confidence
              </span>
            </div>
            <p className="text-[12px] text-muted-foreground leading-relaxed">
              {r.confidence_reason}
            </p>
          </div>
          <div className="mt-4 pt-4 border-t border-border grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="rounded-lg bg-[color:var(--cyan-wash)] border border-[color:var(--cyanw-border)] p-3.5">
              <p className="label-mono !text-[color:var(--cyan-deep)] mb-1.5">Solid</p>
              <p className="text-[11.5px] leading-relaxed">
                Audience sizing. {n(r.audience.addressable)} is an exact count out of the cohort
                model, reconciled to the documented reachability figures.
              </p>
            </div>
            <div className="rounded-lg bg-[color:var(--amber-bg)] border border-[color:var(--amber-border)] p-3.5">
              <p className="label-mono !text-[color:var(--amber-text)] mb-1.5">Soft</p>
              <p className="text-[11.5px] leading-relaxed">
                Everything downstream of send. For push and email these rates are learned
                from 458 real campaigns and 11.3 million sends. For WhatsApp they are still
                an external prior, because Plum sends WhatsApp through WATI, not CleverTap.
              </p>
            </div>
          </div>
        </Panel>

        <Panel className="col-span-12 lg:col-span-4 p-5" ticked>
          <PanelHead title="Suppression in this selection" chip="OBSERVED" />
          <p className="figure text-[32px] text-[color:var(--red)]">
            {n(r.selection.dnd_in_selection)}
          </p>
          <p className="text-[12px] text-muted-foreground mt-2 leading-relaxed">
            people carry is_in_DND_CT inside this selection and must be excluded
            explicitly. Nothing enforces it centrally.
          </p>
        </Panel>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="label-mono block mb-2">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-muted-foreground mt-1.5 leading-snug">{hint}</p>}
    </div>
  );
}

function Toggle({
  checked, onChange, label, hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  hint: string;
}) {
  return (
    <button onClick={() => onChange(!checked)} className="flex items-start gap-2.5 text-left group">
      <span
        className={`w-4 h-4 rounded-[5px] border flex items-center justify-center flex-shrink-0 mt-0.5 transition-all ${
          checked ? "metal-cyan border-transparent" : "border-[color:var(--input)] group-hover:border-[color:var(--cyan)]"
        }`}
      >
        {checked && <Check className="w-2.5 h-2.5 text-white" strokeWidth={3} />}
      </span>
      <span>
        <span className="text-[12px] font-medium block">{label}</span>
        <span className="text-[10.5px] text-muted-foreground">{hint}</span>
      </span>
    </button>
  );
}

/* ==========================================================================
   Decision breakdown: the recommendation's parameters and weights, as a
   spectrum pie (deliberately outside the plum data palette) plus per-channel
   rubric scores. Collapsed by default so it explains without crowding.
   ========================================================================== */

function DecisionBreakdown({ result: r }: { result: SimResult }) {
  const [open, setOpen] = useState(false);
  const d = r.decision!;
  const pie = d.rule.parameters.map((p, i) => ({
    name: p.label, value: p.weight, fill: SPECTRUM[i % SPECTRUM.length], desc: p.desc,
  }));
  const ranked = Object.entries(d.channels).sort((a, b) => b[1].total - a[1].total);
  const maxScore = ranked[0]?.[1].total || 1;

  return (
    <Panel className="p-0 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-[color:var(--muted)] transition-colors"
        aria-expanded={open}
      >
        <span className="w-8 h-8 rounded-lg metal-cyan flex items-center justify-center flex-shrink-0">
          <ChevronDown className={`w-4 h-4 text-white transition-transform ${open ? "rotate-180" : ""}`} />
        </span>
        <span className="flex-1">
          <span className="text-[13.5px] font-medium font-heading block">How this recommendation was calculated</span>
          <span className="text-[11px] text-muted-foreground">
            {d.rule.parameters.length} weighted parameters · rubric v{d.rule.version} · every weight published
          </span>
        </span>
        <Chip kind="RECOMMENDED" />
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 border-t border-border">
          <div className="grid grid-cols-12 gap-6 items-center">
            {/* Weight pie */}
            <div className="col-span-12 md:col-span-4 flex items-center gap-5">
              <div className="w-[150px] h-[150px] flex-shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                      innerRadius={42} outerRadius={68} paddingAngle={3} strokeWidth={0} />
                    <Tooltip content={<ChartTip formatter={(v) => `${v}% weight`} />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 min-w-0">
                {pie.map((p) => (
                  <div key={p.name} className="flex items-center gap-2 text-[11px]" title={p.desc}>
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: p.fill }} />
                    <span className="text-muted-foreground truncate">{p.name}</span>
                    <span className="tnum font-semibold ml-auto">{p.value}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Per-channel rubric scores */}
            <div className="col-span-12 md:col-span-8 space-y-3.5">
              {ranked.map(([key, ch]) => (
                <div key={key}>
                  <div className="flex items-baseline justify-between gap-3 mb-1.5">
                    <span className="text-[12.5px] font-medium inline-flex items-center gap-2">
                      <ChannelGlyph channel={key} size={15} />
                      {ch.label}
                      {key === d.selected && (
                        <span className="chip chip-derived !text-[8px]">SELECTED</span>
                      )}
                    </span>
                    <span className="text-[12.5px] tnum">
                      <span className="font-semibold">{ch.total}</span>
                      <span className="text-muted-foreground">/100 · {n(ch.addressable)} addressable</span>
                    </span>
                  </div>
                  <div className="ribbon">
                    <span style={{
                      width: `${(ch.total / Math.max(maxScore, 1)) * 100}%`,
                      // Selected reads as the cyan-to-seafoam spectrum rather
                      // than pure blue; unselected uses a visible mid-tone
                      // instead of --border-strong, which rendered near-black.
                      background: key === d.selected
                        ? "linear-gradient(90deg, #0E9AA7, #22C8D6 55%, #4FE3C1)"
                        : "linear-gradient(90deg, var(--series-3), var(--sand-deep))",
                    }} />
                  </div>
                </div>
              ))}
              {r.conversion_provenance && (
                <ProvenanceNote label="Click to convert basis" kind={r.conversion_provenance.kind}>
                  {r.conversion_provenance.basis}
                </ProvenanceNote>
              )}
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}

/* ==========================================================================
   Ask Crew M: grounded campaign Q&A. Every reply carries the facts it used
   with provenance, and a quality score against the published 9-parameter
   rubric, computed from the reply itself.
   ========================================================================== */

function FunnelExplainer({ fx }: { fx: FunnelExplain }) {
  const [open, setOpen] = useState(false);
  const pie = fx.rule.parameters.map((p, i) => ({
    name: p.label, value: p.weight, fill: SPECTRUM[i % SPECTRUM.length], desc: p.desc,
  }));

  return (
    <Panel className="p-0 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-[color:var(--muted)] transition-colors"
        aria-expanded={open}
      >
        <span className="w-8 h-8 rounded-lg metal-cyan flex items-center justify-center flex-shrink-0">
          <ChevronDown className={`w-4 h-4 text-white transition-transform ${open ? "rotate-180" : ""}`} />
        </span>
        <span className="flex-1">
          <span className="section-title !text-[16px] block">How this funnel was calculated</span>
          <span className="text-[12px] text-muted-foreground">
            {fx.steps.length} stages · {fx.composition.observed} observed,{" "}
            {fx.composition.derived} derived, {fx.composition.modeled} modeled
          </span>
        </span>
        <Chip kind="PREDICTED" />
      </button>

      {open && (
        <div className="px-5 pb-5 pt-1 border-t border-border">
          <div className="grid grid-cols-12 gap-6">
            {/* stage-by-stage arithmetic */}
            <div className="col-span-12 lg:col-span-8 space-y-2">
              {fx.steps.map((st) => (
                <div key={st.stage} className="panel-flush p-3.5">
                  <div className="meta-row">
                    <span className="label-mono">{st.stage}</span>
                    <Chip kind={st.provenance} />
                    <span className="text-[11px] tnum ml-auto">
                      <span className="text-muted-foreground">of {fx.steps[0].stage.toLowerCase()}</span>{" "}
                      <span className="font-semibold">{pct(st.of_first, 2)}</span>
                      {st.rate !== null && (
                        <span className="text-muted-foreground">
                          {" "}· step {pct(st.rate, 2)}
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between gap-3">
                    <code className="text-[11.5px] text-muted-foreground">{st.math}</code>
                    <span className="figure text-[19px] flex-shrink-0">{n(st.value)}</span>
                  </div>
                  <p className="text-[10.5px] text-muted-foreground mt-1.5">{st.basis}</p>
                </div>
              ))}
            </div>

            {/* weights + honesty */}
            <div className="col-span-12 lg:col-span-4">
              <p className="label-mono mb-2">Weight of each input</p>
              <div className="h-[150px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pie} dataKey="value" nameKey="name" cx="50%" cy="50%"
                      innerRadius={38} outerRadius={62} paddingAngle={3} strokeWidth={0} />
                    <Tooltip content={<ChartTip formatter={(v) => `${v}% weight`} />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 mt-2">
                {pie.map((p) => (
                  <div key={p.name} className="flex items-center gap-2 text-[11px]" title={p.desc}>
                    <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: p.fill }} />
                    <span className="text-muted-foreground truncate">{p.name}</span>
                    <span className="tnum font-semibold ml-auto">{p.value}%</span>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground mt-3.5 pt-3.5 border-t border-border leading-relaxed">
                {fx.honesty}
              </p>
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}

/* ==========================================================================
   Timing panel: the real booking clock, the send slot, and why.
   ========================================================================== */

function TimingPanel({ t }: { t: TimingDetail }) {
  const [open, setOpen] = useState(false);
  const clock = Object.entries(t.clock.shares).map(([h, v]) => ({
    hour: `${String(h).padStart(2, "0")}`,
    share: v,
    isPeak: `${String(h).padStart(2, "0")}:00` === t.primary.intent_peak
         || `${String(h).padStart(2, "0")}:00` === t.secondary.intent_peak,
  }));

  return (
    <Panel className="p-5" ground="dot">
      <PanelHead
        title="Send time"
        sub={`Built on ${n(t.clock.observations)} real bookings in ${t.clock.tz}, not a stated peak window`}
        chip="RECOMMENDED"
        right={
          <div className="flex items-center gap-2">
            <ChannelGlyph channel={t.channel} size={18} />
            <span className="text-[12px] font-medium">{t.channel_label}</span>
          </div>
        }
      />

      <div className="relative grid grid-cols-12 gap-6 items-start">
        {/* the two slots */}
        <div className="col-span-12 md:col-span-4 space-y-3">
          {[t.primary, t.secondary].map((slot, i) => (
            <div key={slot.window}
              className={`rounded-xl border p-4 ${i === 0
                ? "border-[color:var(--cyan)] bg-[color:var(--cyan-wash)]"
                : "border-border bg-[color:var(--muted)]"}`}>
              <div className="meta-row">
                <span className="label-mono">{i === 0 ? "Primary slot" : "Second slot"}</span>
                {i === 0 && <Chip kind="RECOMMENDED" />}
              </div>
              <p className="figure text-[30px]">{slot.send_at}</p>
              <p className="text-[11.5px] text-muted-foreground mt-2 leading-relaxed">
                Lands {slot.lead_minutes} min before the {slot.intent_peak} intent peak,
                which carries {pct(slot.intent_share)} of bookings.
              </p>
              {slot.inbox_sweep && (
                <p className="text-[10.5px] text-muted-foreground mt-1.5">
                  Inside the {slot.inbox_sweep} inbox sweep
                </p>
              )}
            </div>
          ))}
        </div>

        {/* the observed clock */}
        <div className="col-span-12 md:col-span-8">
          <p className="label-mono mb-2">When this audience actually books, by hour {t.clock.tz}</p>
          <div className="h-[168px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={clock} margin={{ left: -14, right: 6, top: 4, bottom: 0 }}>
                <SeriesDefs />
                <CartesianGrid strokeDasharray="3 7" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="hour" {...AXIS} interval={2} tick={{ ...AXIS.tick, fontSize: 10 }} />
                <YAxis tickFormatter={(v: number) => pct(v, 0)} {...AXIS} width={40} />
                <Tooltip content={<ChartTip formatter={(v) => pct(v, 2)} />}
                  cursor={{ fill: "var(--cursor-fill)" }} />
                <Bar dataKey="share" name="Share of bookings" radius={[3, 3, 0, 0]}>
                  {clock.map((d) => (
                    <Cell key={d.hour} fill={d.isPeak ? GRAD.red : GRAD.ink} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 pt-3 border-t border-border">
            <Stat label="Morning 09-14" value={pct(t.clock.morning_share)} size="sm" />
            <Stat label="Evening 17-21" value={pct(t.clock.evening_share)} size="sm" />
            <Stat label="Night 21-24" value={pct(t.clock.night_share)} size="sm" />
            <Stat label="Dead 01-06" value={pct(t.clock.dead_share)} size="sm" tone="red" />
          </div>
        </div>
      </div>

      <button onClick={() => setOpen(!open)}
        className="relative mt-4 text-[12px] text-[color:var(--cyan-deep)] hover:underline">
        {open ? "Hide how this is calculated" : "How this is calculated"}
      </button>

      {open && (
        <div className="relative mt-3 pt-4 border-t border-border grid grid-cols-12 gap-5">
          <div className="col-span-12 lg:col-span-5 space-y-2">
            <p className="label-mono mb-1">Weights</p>
            {t.rule.parameters.map((p, i) => (
              <div key={p.key}>
                <div className="flex items-baseline justify-between gap-2 mb-1">
                  <span className="text-[11.5px] font-medium">{p.label}</span>
                  <span className="tnum text-[11.5px] font-semibold">{p.weight}%</span>
                </div>
                <div className="ribbon !h-[6px]">
                  <span style={{ width: `${p.weight}%`, background: SPECTRUM[i % SPECTRUM.length] }} />
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">{p.desc}</p>
              </div>
            ))}
          </div>
          <div className="col-span-12 lg:col-span-7 space-y-3">
            <div className="panel-flush p-3.5">
              <p className="label-mono mb-1.5">Why this channel sends when it does</p>
              <p className="text-[12px] leading-relaxed">{t.why}</p>
              <p className="text-[11px] text-muted-foreground mt-2">
                Read latency: {t.read_latency}. Quiet hours {t.quiet_hours} are never used.
              </p>
            </div>
            <div className="panel-flush p-3.5">
              <p className="label-mono mb-1.5">Journey slots this channel carries</p>
              {t.journey_slots.length ? t.journey_slots.map((j) => (
                <p key={`${j.day}`} className="text-[11.5px]">
                  Day {j.day}
                  {j.touch ? `, touch ${j.touch}` : ", supplementary"}: {j.role}
                </p>
              )) : <p className="text-[11.5px] text-muted-foreground">Not used in the standard journey.</p>}
            </div>
            {t.corrections.map((c) => (
              <div key={c.claim} className="rounded-lg border border-[color:var(--red)]/25 bg-[color:var(--red)]/[0.04] p-3.5">
                <div className="meta-row">
                  <span className="label-mono">Corrected</span>
                  <Chip kind="OBSERVED" />
                </div>
                <p className="text-[11.5px] leading-relaxed">
                  <span className="line-through text-muted-foreground">{c.claim}</span>
                  {" "}{c.finding}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </Panel>
  );
}
