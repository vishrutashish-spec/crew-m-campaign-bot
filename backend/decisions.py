"""
Decision rules for Crew M: every recommendation is a weighted score over named
parameters, and the weights are published, not implied.

Why this exists. The old channel recommendation was argmax(addressable reach),
which is one parameter wearing a recommendation's clothes. It also picked Email
over WhatsApp for no-app audiences on a 3-point reach edge while ignoring that
WhatsApp opens at 64.8% versus Email's 22.1%, and that the Bible calls WhatsApp
marginally the strongest channel in the whole project. A weighted rubric fixes
that class of mistake and makes every choice auditable: the UI renders these
exact weights as a pie, and the score components come back with every result.

Rules are versioned. Changing a weight means bumping RULES_VERSION so a saved
screenshot can be traced to the rubric that produced it.

--- Data access note (governance) ---
Pure functions over aggregate counts already in memory. No user data.
"""

from __future__ import annotations

import anchors as A

RULES_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Channel recommendation rubric. Weights sum to 100.
# ---------------------------------------------------------------------------

CHANNEL_RULE = {
    "id": "channel_choice",
    "label": "Channel recommendation",
    "version": RULES_VERSION,
    "parameters": [
        {"key": "reach", "label": "Deliverable reach", "weight": 40,
         "desc": "Share of the objective pool this channel can actually deliver to, stale tokens excluded",
         "provenance": "DERIVED"},
        {"key": "engagement", "label": "Open propensity", "weight": 22,
         "desc": "Channel open rate prior, normalised against the best channel",
         "provenance": "MODELED"},
        {"key": "click", "label": "Click propensity", "weight": 12,
         "desc": "Channel click rate prior, normalised against the best channel",
         "provenance": "MODELED"},
        {"key": "delivery", "label": "Delivery reliability", "weight": 10,
         "desc": "Share of sends that arrive at all",
         "provenance": "MODELED"},
        {"key": "frequency", "label": "Frequency headroom", "weight": 9,
         "desc": "Meta caps WhatsApp marketing per user; push and email carry no platform cap",
         "provenance": "OBSERVED"},
        {"key": "suppression", "label": "Suppression safety", "weight": 7,
         "desc": "Share of the channel's audience that survives the DND check",
         "provenance": "OBSERVED"},
    ],
}

# Frequency headroom: WhatsApp Marketing is subject to Meta's per-user
# frequency cap (documented in the copy brief); push and email are not.
_FREQ_HEADROOM = {"whatsapp": 0.75, "email": 1.0, "push": 1.0}


def score_channels(pool: int, options: dict[str, int],
                   dnd_keep: float) -> dict:
    """
    Score each channel 0-100 against the rubric.

    options: {channel: addressable count} (already pool-capped, stale-safe).
    dnd_keep: share of the selection that is not DND-suppressed.
    Returns per-channel component values (each 0-1), weighted totals, and the
    winner, so the UI can show the whole calculation.
    """
    max_open = max(b["open"] for b in A.CHANNEL_BENCHMARKS.values())
    max_click = max(b["click"] for b in A.CHANNEL_BENCHMARKS.values())

    out = {}
    for ch in A.CHANNELS:
        b = A.CHANNEL_BENCHMARKS[ch]
        components = {
            "reach": (options.get(ch, 0) / pool) if pool else 0.0,
            "engagement": b["open"] / max_open,
            "click": b["click"] / max_click,
            "delivery": b["delivery"],
            "frequency": _FREQ_HEADROOM[ch],
            "suppression": dnd_keep,
        }
        total = sum(
            p["weight"] * components[p["key"]]
            for p in CHANNEL_RULE["parameters"]
        )
        # A channel that reaches nobody is not a recommendation at any score.
        if options.get(ch, 0) == 0:
            total = 0.0
        out[ch] = {
            "label": A.CHANNEL_LABELS[ch],
            "components": {k: round(v, 4) for k, v in components.items()},
            "total": round(total, 1),
            "addressable": options.get(ch, 0),
        }

    winner = max(out, key=lambda c: out[c]["total"])
    return {
        "rule": CHANNEL_RULE,
        "channels": out,
        "selected": winner,
    }


# ---------------------------------------------------------------------------
# Timing rubric: published for the UI, applied in server.py.
# ---------------------------------------------------------------------------

# The send-time rubric now lives in timing.py, built on the observed booking
# clock rather than the stated 20:00-23:00 window, which real bookings do not
# support. Kept out of this registry so there is only one source.

# ---------------------------------------------------------------------------
# Copy scoring rubric: the discipline checks in copy_engine, with weights.
# ---------------------------------------------------------------------------

COPY_RULE = {
    "id": "copy_style",
    "label": "Copy discipline score",
    "version": RULES_VERSION,
    "parameters": [
        {"key": "length", "label": "Channel length limits", "weight": 25,
         "desc": "WATI 1024 cap, push title and body limits, email subject cap",
         "provenance": "OBSERVED"},
        {"key": "emoji", "label": "Emoji fit per band", "weight": 16,
         "desc": "Each band has a comfort range from shipped copy; every emoji tied to its word",
         "provenance": "OBSERVED"},
        {"key": "voice", "label": "Voice rules", "weight": 24,
         "desc": "No fear framing under 26, HC never says book again, TH friction device stays out of HC",
         "provenance": "OBSERVED"},
        {"key": "category", "label": "Utility vs Marketing", "weight": 15,
         "desc": "Classification decides Meta category, cost and frequency caps",
         "provenance": "DERIVED"},
        {"key": "cta", "label": "Soft CTA", "weight": 10,
         "desc": "Tap-below style, never hard-sell urgency",
         "provenance": "OBSERVED"},
        {"key": "hygiene", "label": "House hygiene", "weight": 10,
         "desc": "Personalisation token where shipped copy carries one; no em dashes",
         "provenance": "OBSERVED"},
    ],
}

# ---------------------------------------------------------------------------
# Assistant answer rubric: 9 parameters, weights sum to 100. Every chat reply
# is scored against these, and the scoring is computed from the reply object
# itself, never asserted.
# ---------------------------------------------------------------------------

ASSISTANT_RULE = {
    "id": "assistant_quality",
    "label": "Answer quality score",
    "version": RULES_VERSION,
    "parameters": [
        {"key": "grounding", "label": "Grounded in the model", "weight": 18,
         "desc": "Every claim traces to a figure the cohort model actually serves"},
        {"key": "numbers", "label": "Numeric traceability", "weight": 14,
         "desc": "Exact counts, never rounded storytelling"},
        {"key": "provenance", "label": "Provenance labelling", "weight": 12,
         "desc": "OBSERVED, DERIVED, MODELED and PREDICTED never blurred"},
        {"key": "specificity", "label": "Cohort specificity", "weight": 10,
         "desc": "Answers about the selected cohorts, not the base in general"},
        {"key": "discipline", "label": "Channel discipline", "weight": 10,
         "desc": "Copy advice obeys the channel limits and voice rules"},
        {"key": "action", "label": "Actionability", "weight": 14,
         "desc": "Ends with something the marketer can do next"},
        {"key": "honesty", "label": "Confidence honesty", "weight": 12,
         "desc": "Predictions carry low confidence and say why; unknowns are said plainly"},
        {"key": "length", "label": "Length discipline", "weight": 5,
         "desc": "Tight answers; no padding"},
        {"key": "hygiene", "label": "House hygiene", "weight": 5,
         "desc": "No em dashes, no fabricated statistics"},
    ],
}

ALL_RULES = [CHANNEL_RULE, COPY_RULE, ASSISTANT_RULE]


def registry() -> dict:
    return {"version": RULES_VERSION, "rules": ALL_RULES}
