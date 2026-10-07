"use client";

/**
 * SIGNAL: the campaign analyst, presented as a phone.
 *
 * The phone IS the interface, not a thumbnail beside a panel. Identity,
 * suggestions and the quality rubric all live inside the frame, so the dock
 * can be phone-shaped rather than a generic card. The frame carries real
 * chrome: notch, status bar, home indicator.
 *
 * Every reply shows the facts it used with provenance chips and a quality
 * score against the published 10-parameter rubric. Scoring is computed
 * server-side from the reply object, never asserted here.
 */

import { useEffect, useRef, useState } from "react";
import {
  askAssistant, getSignalSuggestions, getRules, getSignalTuning, SPECTRUM,
  type AssistantReply, type DecisionParam, type TuningParam,
} from "@/lib/api";
import { Chip } from "@/components/kit";
import { SignalAvatar } from "@/components/signal-avatar";
import {
  Send, RotateCw, Sparkles, Wifi, BatteryFull, Gauge, X, SlidersHorizontal,
} from "lucide-react";

interface Msg {
  role: "user" | "ai";
  text: string;
  reply?: AssistantReply;
}

export function SignalChat({
  cohortKeys, org, compact = false,
}: {
  cohortKeys: string[];
  org: string | null;
  /** Dock mode: the phone stands alone, no outer window chrome. */
  compact?: boolean;
}) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [suggested, setSuggested] = useState<string[]>([]);
  const [rubric, setRubric] = useState<DecisionParam[] | null>(null);
  const [tuneSpec, setTuneSpec] = useState<{ parameters: TuningParam[]; locked: string[] } | null>(null);
  const [tuning, setTuning] = useState<Record<string, string | boolean>>({});
  const [pane, setPane] = useState<"rubric" | "tuning">("rubric");
  const [sheet, setSheet] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getSignalSuggestions(cohortKeys)
      .then((r) => setSuggested(r.suggestions))
      .catch(() => {});
  }, [cohortKeys.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    getRules().then((r) => {
      const rule = r.rules.find((x) => x.id === "signal_quality");
      if (rule) setRubric(rule.parameters);
    }).catch(() => {});
    getSignalTuning().then((t) => {
      setTuneSpec(t);
      // Seed from the published defaults so the controls and the server agree.
      const seed: Record<string, string | boolean> = {};
      t.parameters.forEach((prm) => { seed[prm.key] = prm.default; });
      setTuning(seed);
    }).catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight, behavior: "smooth",
    });
  }, [messages, busy]);

  async function send(text?: string) {
    const msg = (text ?? input).trim();
    if (!msg || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setBusy(true);
    try {
      const reply = await askAssistant({
        message: msg, cohort_keys: cohortKeys, org, tuning,
      });
      setMessages((m) => [...m, { role: "ai", text: reply.answer, reply }]);
    } catch (e) {
      setMessages((m) => [...m, {
        role: "ai",
        text: e instanceof Error ? `That did not work: ${e.message}` : "That did not work.",
      }]);
    } finally {
      setBusy(false);
    }
  }

  const scored = messages.filter((m) => m.reply);
  const avg = scored.length
    ? scored.reduce((s, m) => s + (m.reply?.score.total ?? 0), 0) / scored.length
    : null;

  const phone = (
    <div className="phone">
      <div className="phone-frame">
        <div className="phone-screen relative">
          {/* status bar */}
          <div className="phone-status">
            <span className="tnum">9:41</span>
            <span className="phone-notch" aria-hidden />
            <span className="flex items-center gap-1.5">
              <Wifi className="w-3 h-3" />
              <BatteryFull className="w-3.5 h-3.5" />
            </span>
          </div>

          {/* identity strip: the avatar is the hero */}
          <div className="phone-identity">
            <SignalAvatar size={38} live thinking={busy} />
            <div className="min-w-0 flex-1">
              <span className="phone-identity-name">SIGNAL</span>
              <p className="text-[10px] text-muted-foreground mt-1 truncate">
                {busy ? "reading the model" : "cohort analyst · online"}
              </p>
            </div>
            {avg !== null && (
              <span className="inline-flex items-center gap-1 flex-shrink-0">
                <span className="label-mono !text-[8.5px]">AVG</span>
                <span className="tnum font-bold text-[13px] text-[color:var(--success)]">
                  {avg.toFixed(1)}
                </span>
              </span>
            )}
            <button
              onClick={() => { setPane("tuning"); setSheet(true); }}
              className="w-7 h-7 rounded-lg border border-border flex items-center justify-center flex-shrink-0 hover:border-[color:var(--cyan)]"
              aria-label="Tune SIGNAL"
              title="Tune how SIGNAL answers"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-muted-foreground" />
            </button>
            <button
              onClick={() => { setPane("rubric"); setSheet(true); }}
              className="w-7 h-7 rounded-lg border border-border flex items-center justify-center flex-shrink-0 hover:border-[color:var(--cyan)]"
              aria-label="Answer quality rubric"
              title="How answers are scored"
            >
              <Gauge className="w-3.5 h-3.5 text-muted-foreground" />
            </button>
          </div>

          {/* thread */}
          <div ref={scrollRef} className="phone-thread">
            {messages.length === 0 && (
              <div className="flex items-start gap-2 min-w-0">
                <SignalAvatar size={24} live />
                <div className="bubble bubble-ai min-w-0">
                  <p className="text-[12px] leading-relaxed">
                    Ask me which biomarker is off in a cohort, what the consult pattern
                    looks like, or which filters build a segment. I only answer with
                    numbers the data actually holds.
                  </p>
                </div>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="flex justify-end">
                  <div className="bubble bubble-me min-w-0">
                    <p className="text-[12px] leading-relaxed">{m.text}</p>
                  </div>
                </div>
              ) : (
                <AiBubble key={i} msg={m} />
              )
            )}

            {busy && (
              <div className="flex items-start gap-2">
                <SignalAvatar size={24} live thinking />
                <div className="bubble bubble-ai">
                  <span className="typing"><i /><i /><i /></span>
                </div>
              </div>
            )}
          </div>

          {/* suggestion tray, inside the frame */}
          {messages.length === 0 && suggested.length > 0 && (
            <div className="phone-tray">
              {suggested.slice(0, 3).map((q) => (
                <button key={q} onClick={() => send(q)} className="phone-chip">
                  <Sparkles className="w-3 h-3 flex-shrink-0 text-[color:var(--cyan-deep)]" />
                  <span>{q}</span>
                </button>
              ))}
            </div>
          )}

          {/* composer */}
          <div className="phone-composer">
            <input
              className="phone-input"
              placeholder="Ask SIGNAL"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
            />
            <button onClick={() => send()} disabled={busy || !input.trim()}
              className="phone-send" aria-label="Send">
              {busy ? <RotateCw className="w-3.5 h-3.5 animate-spin" />
                    : <Send className="w-3.5 h-3.5" />}
            </button>
          </div>
          <div className="phone-home" aria-hidden />

          {/* sheet: rubric on one pane, tuning on the other */}
          {sheet && (
            <div className="phone-sheet glass">
              <div className="flex items-center gap-1.5 mb-3">
                <button onClick={() => setPane("rubric")}
                  className={`sheet-tab ${pane === "rubric" ? "is-on" : ""}`}>
                  Scoring
                </button>
                <button onClick={() => setPane("tuning")}
                  className={`sheet-tab ${pane === "tuning" ? "is-on" : ""}`}>
                  Tuning
                </button>
                <button onClick={() => setSheet(false)}
                  className="w-6 h-6 rounded-md border border-border flex items-center justify-center ml-auto flex-shrink-0"
                  aria-label="Close">
                  <X className="w-3 h-3" />
                </button>
              </div>

              {pane === "tuning" && tuneSpec && (
                <div className="space-y-3">
                  <p className="text-[10.5px] text-muted-foreground leading-relaxed">
                    These change how SIGNAL answers, and take effect on the next
                    question.
                  </p>
                  {tuneSpec.parameters.map((prm) => (
                    <div key={prm.key}>
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-medium flex-1 min-w-0">{prm.label}</span>
                        {prm.type === "toggle" ? (
                          <button
                            role="switch"
                            aria-checked={Boolean(tuning[prm.key])}
                            aria-label={prm.label}
                            onClick={() => setTuning((t) => ({ ...t, [prm.key]: !t[prm.key] }))}
                            className={`tune-switch ${tuning[prm.key] ? "is-on" : ""}`}
                          >
                            <span />
                          </button>
                        ) : (
                          <div className="flex gap-1 flex-shrink-0">
                            {prm.options?.map((o) => (
                              <button key={o}
                                onClick={() => setTuning((t) => ({ ...t, [prm.key]: o }))}
                                className={`tune-opt ${tuning[prm.key] === o ? "is-on" : ""}`}>
                                {o}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      <p className="text-[9.5px] text-muted-foreground leading-snug mt-1">
                        {prm.desc}
                      </p>
                    </div>
                  ))}
                  <div className="pt-2.5 border-t border-border space-y-1.5">
                    <span className="label-mono !text-[8.5px]">Not tunable</span>
                    {tuneSpec.locked.map((l) => (
                      <p key={l} className="text-[9.5px] text-muted-foreground leading-snug">{l}</p>
                    ))}
                  </div>
                </div>
              )}

              {pane === "rubric" && rubric && (
              <>
              <p className="text-[10.5px] text-muted-foreground mb-3 leading-relaxed">
                Every reply is scored on these {rubric.length} parameters, computed from
                the reply itself. Weights sum to 100.
              </p>
              <div className="space-y-2">
                {rubric.map((p, i) => (
                  <div key={p.key} className="flex items-start gap-2 text-[10.5px]">
                    <span className="w-2 h-2 rounded-full mt-1 flex-shrink-0"
                      style={{ background: SPECTRUM[i % SPECTRUM.length] }} />
                    <span className="flex-1 min-w-0">
                      <span className="font-medium">{p.label}</span>
                      <span className="text-muted-foreground block text-[9.5px] leading-snug">
                        {p.desc}
                      </span>
                    </span>
                    <span className="tnum font-semibold flex-shrink-0">{p.weight}</span>
                  </div>
                ))}
              </div>
              </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  // In the dock the phone stands alone. Inline it keeps its window chrome.
  if (compact) return phone;

  return (
    <section className="mac-panel">
      <div className="mac-bar">
        <span className="mac-dot mac-dot-r" />
        <span className="mac-dot mac-dot-y" />
        <span className="mac-dot mac-dot-g" />
        <span className="mac-title">signal / cohort analyst</span>
      </div>
      <div className="grid-ground aurora px-6 py-7">
        <div className="relative flex flex-col items-center gap-5">
          {phone}
          {/* A single evidence line under the phone. Keeps the phone the
              centrepiece while giving the surface a reason to be there. */}
          <p className="text-[11.5px] text-muted-foreground text-center max-w-lg leading-relaxed">
            Reads the cohort model over 956,050 eligible people, 133,218 telehealth
            consults across 24 specialties, and 36,526 checkup bookings across 11
            scored biomarkers. It answers with figures those actually hold, and
            labels every one.
          </p>
        </div>
      </div>
    </section>
  );
}

function AiBubble({ msg }: { msg: Msg }) {
  const [open, setOpen] = useState(false);
  const r = msg.reply;
  return (
    <div className="flex items-start gap-2 min-w-0">
      <SignalAvatar size={24} live />
      <div className="bubble bubble-ai min-w-0">
        <AnswerBody text={msg.text} />

        {r?.action && (
          <p className="text-[11px] mt-2.5 pt-2.5 border-t border-border leading-relaxed">
            <span className="label-mono !text-[color:var(--cyan-deep)] !text-[8.5px] block mb-1">
              Do this
            </span>
            {r.action}
          </p>
        )}

        {r && r.facts.length > 0 && (
          <div className="mt-2.5 space-y-1.5">
            {r.facts.slice(0, 5).map((f, i) => (
              <div key={i} className="sig-fact">
                <Chip kind={f.provenance} />
                <span className="sig-fact-label">{f.label}</span>
                <span className="sig-fact-value tnum">{f.value}</span>
              </div>
            ))}
          </div>
        )}

        {r && (
          <>
            <div className="flex items-center justify-between gap-2 mt-2.5 pt-2 border-t border-border">
              <button onClick={() => setOpen(!open)}
                className="text-[10px] text-[color:var(--cyan-deep)] hover:underline">
                {open ? "Hide scoring" : "How this was scored"}
              </button>
              <span className="inline-flex items-center gap-1.5 flex-shrink-0">
                <span className="label-mono !text-[8.5px]">Quality</span>
                <span className={`tnum font-bold text-[13px] ${
                  r.score.total >= 9 ? "text-[color:var(--success)]"
                  : r.score.total >= 7 ? "text-[color:var(--warning)]"
                  : "text-[color:var(--red)]"}`}>
                  {r.score.total}/{r.score.out_of}
                </span>
              </span>
            </div>
            {open && (
              <div className="mt-2 space-y-1">
                {r.score.parameters.map((p, i) => (
                  <div key={p.key} className="flex items-center gap-2 text-[9.5px]">
                    <span className="w-[78px] text-muted-foreground truncate flex-shrink-0">
                      {p.label}
                    </span>
                    <div className="ribbon flex-1 !h-[5px]">
                      <span style={{ width: `${p.score * 100}%`,
                        background: SPECTRUM[i % SPECTRUM.length] }} />
                    </div>
                    <span className="tnum w-8 text-right text-muted-foreground flex-shrink-0">
                      {p.points}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/**
 * Renders a SIGNAL answer.
 *
 * Segment answers carry machine tokens (CleverTap property and event names)
 * far wider than a phone bubble. Those get their own non-wrapping row that
 * scrolls horizontally, so a 78-character property name never breaks one
 * character per line or spills past the glass. Prose wraps normally.
 */
function AnswerBody({ text }: { text: string }) {
  const lines = text.split("\n");
  return (
    <div className="text-[12px] leading-relaxed space-y-1.5">
      {lines.map((raw, i) => {
        const line = raw.trimEnd();
        if (!line.trim()) return null;

        if (line.includes(" · ") && /^\s/.test(raw)) {
          return <code key={i} className="rule-row">{line.trim()}</code>;
        }
        if (/^\s{4,}/.test(raw)) {
          return <span key={i} className="rule-why">{line.trim()}</span>;
        }
        if (/^(Base user properties|Product eligibility|Event conditions|Suppression)$/
              .test(line.trim())) {
          return <span key={i} className="rule-group">{line.trim()}</span>;
        }
        return <p key={i}>{line}</p>;
      })}
    </div>
  );
}
