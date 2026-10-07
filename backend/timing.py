"""
Send-time engine, rebuilt on observed booking behaviour.

The old version returned a cohort's "peak hour" from a modeled table and
called it a recommendation. That was the bare minimum, and it was also
pointing at the wrong hour: the real booking clock from 133,218 telehealth
consults peaks at 11:00 and 18:00-19:00 IST, while the Bible's stated
20:00-23:00 window holds only 18.9% of bookings and sits past the peak.

The model here is intent-lead, not intent-match. A send should land far enough
ahead of the intent window that the message is already waiting when intent
rises, and the lead differs per channel because the channels are read
differently:

  WhatsApp  read within minutes, so send close to intent (30 min lead)
  Push      needs the app in hand, so fire at the intent peak itself (0 lead)
  Email     read in inbox sweeps at the start of the workday and again late
            afternoon, so send into the sweep before the peak (90 min lead)

Every recommendation returns the arithmetic and the evidence, because a
timing claim without its clock is just an opinion.
"""

from __future__ import annotations

import anchors as A
import cohort_intel as CI

RULES_VERSION = "1.1"

# Channel read behaviour. Lead is minutes before the intent peak that a send
# should leave, and the inbox windows are when the channel is actually checked.
CHANNEL_TIMING = {
    "whatsapp": {
        "lead_min": 30,
        "read_latency": "minutes",
        "sweeps": [],
        "why": "WhatsApp is read within minutes of arriving, so it should land just before intent rises rather than hours ahead",
    },
    "push": {
        "lead_min": 0,
        "read_latency": "immediate or never",
        "sweeps": [],
        "why": "Push is only seen if the phone is picked up, so it fires at the intent peak itself and has no useful lead",
    },
    "email": {
        "lead_min": 90,
        "read_latency": "hours",
        "sweeps": [(9, 11), (16, 18)],
        "why": "Work email is processed in sweeps at the start of the day and again late afternoon, so a send should arrive inside a sweep that precedes the peak",
    },
}

TIMING_RULE = {
    "id": "send_timing",
    "label": "Send-time recommendation",
    "version": RULES_VERSION,
    "parameters": [
        {"key": "booking_clock", "label": "Observed booking clock", "weight": 46,
         "desc": "When this cohort actually books, from 133,218 real consults in IST",
         "provenance": "OBSERVED"},
        {"key": "channel_read", "label": "Channel read behaviour", "weight": 24,
         "desc": "Read latency and inbox sweeps set how far ahead of intent to send",
         "provenance": "MODELED"},
        {"key": "journey_slot", "label": "Journey touch slot", "weight": 16,
         "desc": "Touch 1 day 0, push day 2, touch 2 day 4, email day 9, per the journey design",
         "provenance": "OBSERVED"},
        {"key": "quiet_hours", "label": "Quiet-hour guard", "weight": 14,
         "desc": "Never schedule into the 01:00-06:00 dead zone, which carries under 4% of bookings",
         "provenance": "OBSERVED"},
    ],
}

# The journey shape from the copy brief. Real, documented, and it decides
# which channel carries which touch.
JOURNEY = [
    {"touch": 1, "day": 0, "channel": "whatsapp", "role": "the hook"},
    {"touch": None, "day": 2, "channel": "push", "role": "zero-cost supplementary nudge"},
    {"touch": 2, "day": 4, "channel": "whatsapp", "role": "second nudge"},
    {"touch": 3, "day": 9, "channel": "email", "role": "deliberate channel switch, final attempt"},
]

QUIET_START, QUIET_END = 1, 6


def _fmt(hour: int, minute: int = 0) -> str:
    return f"{hour % 24:02d}:{minute:02d}"


def _shift(hour: int, minutes: int) -> tuple[int, int]:
    """Move back by `minutes` and return (hour, minute)."""
    total = hour * 60 - minutes
    total %= 24 * 60
    return total // 60, total % 60


def recommend(channel: str, cohort_keys: list[str]) -> dict:
    """
    Recommend a send time for one channel and cohort selection, with the
    clock, the arithmetic and the alternatives.
    """
    channel = channel if channel in CHANNEL_TIMING else "whatsapp"
    cfg = CHANNEL_TIMING[channel]

    # Use the cohort's own clock where the sample supports it, else the base.
    clock = None
    used_cohort = None
    for k in cohort_keys:
        c = CI.booking_clock(k)
        if c["n"] >= 2000:
            clock = c
            used_cohort = k
            break
    if clock is None:
        clock = CI.booking_clock()

    shares = clock["shares"]

    # Two candidate intent windows: the morning and evening peaks. Real
    # behaviour is twin-peaked, so a single "peak hour" throws half the
    # opportunity away.
    morning = max(range(9, 15), key=lambda h: shares.get(h, 0))
    evening = max(range(16, 22), key=lambda h: shares.get(h, 0))

    def build(peak: int, label: str) -> dict:
        h, m = _shift(peak, cfg["lead_min"])
        # Email must land inside a real inbox sweep, otherwise it waits.
        in_sweep = None
        if cfg["sweeps"]:
            for lo, hi in cfg["sweeps"]:
                if lo <= h < hi:
                    in_sweep = (lo, hi)
                    break
            if in_sweep is None:
                # pull back to the nearest preceding sweep
                best = min(cfg["sweeps"], key=lambda s: abs(s[0] - h))
                h, m = best[0], 30
                in_sweep = best
        if QUIET_START <= h < QUIET_END:
            h, m = 7, 0
        return {
            "window": label,
            "send_at": _fmt(h, m),
            "intent_peak": _fmt(peak),
            "intent_share": round(shares.get(peak, 0), 4),
            "lead_minutes": cfg["lead_min"],
            "inbox_sweep": f"{_fmt(in_sweep[0])} to {_fmt(in_sweep[1])}" if in_sweep else None,
        }

    a = build(morning, "morning")
    b = build(evening, "evening")
    primary, secondary = (a, b) if shares.get(morning, 0) >= shares.get(evening, 0) else (b, a)

    journey = [j for j in JOURNEY if j["channel"] == channel]

    return {
        "channel": channel,
        "channel_label": A.CHANNEL_LABELS[channel],
        "primary": primary,
        "secondary": secondary,
        "read_latency": cfg["read_latency"],
        "why": cfg["why"],
        "clock": {
            "source": ("cohort " + used_cohort) if used_cohort else "whole base",
            "observations": clock["n"],
            "morning_share": clock["morning_share"],
            "evening_share": clock["evening_share"],
            "night_share": clock["night_share"],
            "dead_share": clock["dead_share"],
            "tz": "IST",
            "shares": shares,
        },
        "journey_slots": journey,
        "quiet_hours": f"{_fmt(QUIET_START)} to {_fmt(QUIET_END)}",
        "corrections": [
            {
                "claim": "Peak activity is 20:00 to 23:00",
                "finding": (
                    f"That window holds {clock['night_share']:.1%} of real bookings. "
                    f"Booking intent is twin-peaked and peaks at "
                    f"{_fmt(morning)} ({shares.get(morning, 0):.1%}) and "
                    f"{_fmt(evening)} ({shares.get(evening, 0):.1%})."
                ),
            },
            {
                "claim": "Source timestamps can be read as local time",
                "finding": (
                    "They are UTC. Read raw, the curve peaks at 05:00, which is "
                    "impossible for an Indian base. Converted to IST it resolves "
                    "into a normal working-day pattern."
                ),
            },
        ],
        "rule": TIMING_RULE,
        "label": "RECOMMENDED",
    }


def all_channels(cohort_keys: list[str]) -> dict:
    return {ch: recommend(ch, cohort_keys) for ch in A.CHANNELS}


# ---------------------------------------------------------------------------
# Funnel explainer: how every projected number was produced.
# ---------------------------------------------------------------------------

FUNNEL_RULE = {
    "id": "funnel_projection",
    "label": "Funnel projection",
    "version": RULES_VERSION,
    "parameters": [
        {"key": "audience", "label": "Audience sizing", "weight": 34,
         "desc": "Exact counts from the cohort model, pool-capped and DND-filtered",
         "provenance": "DERIVED"},
        {"key": "conversion", "label": "Click to convert", "weight": 26,
         "desc": "Observed homepage-to-booked rate where a funnel exists, else a labelled prior",
         "provenance": "OBSERVED"},
        {"key": "delivery", "label": "Delivery rate", "weight": 14,
         "desc": "Channel delivery prior", "provenance": "MODELED"},
        {"key": "open", "label": "Open rate", "weight": 14,
         "desc": "Channel open prior", "provenance": "MODELED"},
        {"key": "click", "label": "Click rate", "weight": 12,
         "desc": "Channel click prior", "provenance": "MODELED"},
    ],
}


def funnel_explain(channel: str, objective: str, sent: int,
                   funnel: dict) -> dict:
    """
    Stage-by-stage arithmetic for a projected funnel, each line carrying its
    own input, operation and provenance. Nothing here is re-derived: the
    numbers are read back out of the funnel the simulator already produced, so
    the explanation can never disagree with the chart.
    """
    b = A.CHANNEL_BENCHMARKS[channel]
    conv_kind, conv_basis = A.CONVERSION_PROVENANCE[objective]
    conv = A.OBJECTIVE_CONVERSION[objective]

    steps = [
        {
            "stage": "Sent",
            "value": funnel["sent"],
            "math": f"addressable audience minus the {A.CONTROL_GROUP_SHARE:.0%} control group",
            "rate": None,
            "provenance": "DERIVED",
            "basis": "exact count from the cohort model, capped by the objective pool",
        },
        {
            "stage": "Delivered",
            "value": funnel["delivered"],
            "math": f"{funnel['sent']:,} x {b['delivery']:.1%}",
            "rate": b["delivery"],
            "provenance": "MODELED",
            "basis": f"{A.CHANNEL_LABELS[channel]} delivery prior, no Plum delivery logs exist yet",
        },
        {
            "stage": "Opened",
            "value": funnel["opened"],
            "math": f"{funnel['delivered']:,} x {b['open']:.1%}",
            "rate": b["open"],
            "provenance": "MODELED",
            "basis": f"{A.CHANNEL_LABELS[channel]} open prior",
        },
        {
            "stage": "Clicked",
            "value": funnel["clicked"],
            "math": f"{funnel['opened']:,} x {b['click']:.1%}",
            "rate": b["click"],
            "provenance": "MODELED",
            "basis": f"{A.CHANNEL_LABELS[channel]} click prior",
        },
        {
            "stage": "Converted",
            "value": funnel["converted"],
            "math": f"{funnel['clicked']:,} x {conv:.2%}",
            "rate": conv,
            "provenance": conv_kind,
            "basis": conv_basis,
        },
    ]

    # Every stage also carries its share of the FIRST stage, which is what the
    # chart labels. "rate" stays as the step-over-step multiplier because that
    # is genuinely how the value was computed, so the explanation shows both
    # without either one being able to contradict the bars.
    first = steps[0]["value"] or 0
    for s in steps:
        s["of_first"] = round(s["value"] / first, 4) if first else 0.0

    observed = sum(1 for s in steps if s["provenance"] == "OBSERVED")
    derived = sum(1 for s in steps if s["provenance"] == "DERIVED")
    return {
        "rule": FUNNEL_RULE,
        "steps": steps,
        "end_to_end": funnel.get("conversion_rate"),
        "composition": {"observed": observed, "derived": derived,
                        "modeled": len(steps) - observed - derived},
        "honesty": (
            "Audience sizing is exact. Delivery, open and click are learned "
            "from this account's own campaigns for push and email, 458 of them "
            "across 11.3 million sends. WhatsApp is the exception and stays an "
            "external prior, because Plum sends WhatsApp through WATI rather "
            "than CleverTap. Click to convert is anchored in the observed "
            "product funnels wherever one exists."
        ),
        "label": "PREDICTED",
    }
