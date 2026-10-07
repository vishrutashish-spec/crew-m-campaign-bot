"""
Per-angle WhatsApp copy for Crew M.

The bug this fixes: the copy engine accepted an `angle` for every channel but
only push actually used it, so all four messaging angles returned the identical
WhatsApp body. Choosing "Mental health" and choosing "Nutrition" produced the
same message, which makes the angle control a lie.

Each angle here is a genuinely different mechanism, not a reworded opener:

  Health checkup
    ownership     entitlement. You already own this, go and use it.
    baseline      reference point. Know what normal looks like for you.
    silent_shift  early movement. Markers shift before you feel anything.
    reassurance   closure. Most results come back fine, and that is the point.

  Telehealth
    friction            speed and effort. Fifteen minutes, no travel.
    normalised_symptoms the thing you stopped noticing because it never stops.
    mental_health       someone to talk to, framed as ordinary and covered.
    nutrition           energy, diet and weight, as a plan rather than advice.

Two tiers per angle rather than six, because the discipline rules that actually
bind are tiered, not per-year:

  young  (u20, 21-25, 26-35)  emoji bullet block, lighter register, no fear
                              framing at all for the under-26 bands
  older  (36-40, 41-50, 51+)  plain list and 1 to 2 emojis, because the emoji
                              comfort range for 41+ is 1 to 3 and shipped copy
                              for these bands reads most direct

Discipline held in every string below, matching the analyser's checks:
  * no em or en dashes
  * health checkup copy never borrows telehealth's friction device, and never
    says "book again": one free checkup per plan year, structurally
  * no fear words (cancer, cardiac, disease, diagnosis, serious, risk) in any
    copy that can reach the under-26 bands
  * a soft CTA closes every message
  * paragraphs are separated by a blank line, so the message renders with real
    spacing in a WhatsApp bubble rather than as one wall of text

--- Data access note (governance) ---
Templates only. This module reads no user data of any kind.
"""

from __future__ import annotations

# Bullet blocks. The emoji version is for the younger tier; the plain version
# keeps the older tier inside its 1 to 3 emoji range.
#
# Three bullets, not four: the 26-35 comfort range is 2 to 5, and a four-bullet
# block plus a hook emoji lands on 6, which the analyser fails.
HC_BULLETS_EMOJI = (
    "\U0001F3E0 At-home sample pickup\n"
    "⏱️ Results in 24 to 48 hrs on the Plum app\n"
    "\U0001F468‍⚕️ A doctor explains your results"
)
HC_BULLETS_PLAIN = (
    "At-home sample pickup, so nothing needs planning.\n"
    "Results in 24 to 48 hours on the Plum app.\n"
    "A doctor talks you through what they mean."
)

TH_BULLETS_EMOJI = (
    "✅ Video or chat with a verified specialist\n"
    "\U0001F4C4 Digital prescription, valid pan India\n"
    "\U0001F4F1 Full record saved on your Plum app"
)
TH_BULLETS_PLAIN = (
    "Video or chat with a verified specialist.\n"
    "Digital prescription, valid across India.\n"
    "The whole record stays on your Plum app."
)

_HC_OWN = ("Your Plum benefits include a full Health Checkup. Not the "
           "blood-pressure-and-weight kind, but a deeper panel most people pay "
           "thousands for. Already paid for. Already yours.")


# ===========================================================================
# Health checkup
# ===========================================================================

HC = {
    "ownership": {
        "young": (
            "There is a full health checkup sitting in your Plum account, and "
            "most people never open it. \U0001F381\n\n"
            + _HC_OWN + "\n\n"
            "Nothing to claim, nothing to expense, no approval to chase. It is "
            "already covered, and it stays unused until you pick a slot.\n\n"
            "Here is what you get:\n" + HC_BULLETS_EMOJI + "\n\n"
            "One thing you own that is worth actually using. Tap below. \U0001F447"
        ),
        "older": (
            "You have a full health checkup included in your Plum benefits, and "
            "it has not been used. \U0001F4CB\n\n"
            + _HC_OWN + "\n\n"
            "There is nothing to claim and nothing to approve. It is paid for "
            "already, and it expires unused if it is never booked.\n\n"
            + HC_BULLETS_PLAIN + "\n\n"
            "Worth using something you already own. Tap below to pick a slot."
        ),
    },
    "baseline": {
        "young": (
            "Here is a question almost nobody can answer about themselves: what "
            "is normal, for you? \U0001F9EA\n\n"
            "Not the population average. Your own numbers, written down once, so "
            "there is something to compare against later.\n\n"
            + _HC_OWN + "\n\n"
            "You may feel completely fine. That is exactly when a baseline is "
            "worth having, because a first reading taken while everything is "
            "good is the useful one.\n\n"
            "Here is what you get:\n" + HC_BULLETS_EMOJI + "\n\n"
            "Get your own numbers on record. Tap below. \U0001F447"
        ),
        "older": (
            "Most people have no idea what their own normal looks like. \U0001F4CA\n\n"
            "Not the average for your age. Your own readings, recorded once, so "
            "every later result has something to be measured against.\n\n"
            + _HC_OWN + "\n\n"
            "Feeling well is not the same as having a reference point. The first "
            "reading is the one that makes the next five useful.\n\n"
            + HC_BULLETS_PLAIN + "\n\n"
            "Start the record this year. Tap below whenever it is convenient."
        ),
    },
    "silent_shift": {
        # Deliberately no fear vocabulary. This angle is about timing and
        # measurement, and it has to clear the under-26 rule as written.
        "young": (
            "Some things about your health change quietly, and slowly, and you "
            "would not notice either way. \U0001F331\n\n"
            "Vitamin D, B12, iron, thyroid. These drift on their own schedule, "
            "and the first sign is usually just being more tired than the week "
            "seems to justify.\n\n"
            + _HC_OWN + "\n\n"
            "A panel picks up the drift while it is still small and easy to "
            "correct, often with nothing more than a supplement.\n\n"
            "Here is what you get:\n" + HC_BULLETS_EMOJI + "\n\n"
            "Catch the small stuff early. Tap below. \U0001F447"
        ),
        "older": (
            "Blood sugar and cholesterol move before anything feels different. "
            "\U0001FA7A\n\n"
            "That is simply how they behave. Numbers shift first, and the body "
            "reports it much later, which is why a reading is worth more than "
            "how you feel on the day.\n\n"
            + _HC_OWN + "\n\n"
            "This is a good age to see a change while it is still just a change, "
            "when it is easiest to do something about.\n\n"
            + HC_BULLETS_PLAIN + "\n\n"
            "See it while it is small. Tap below to book."
        ),
    },
    "reassurance": {
        "young": (
            "Most checkups come back completely unremarkable, and that is a good "
            "outcome, not a wasted appointment. ✅\n\n"
            "Knowing everything is where it should be is worth something on its "
            "own. It also takes a low background hum of wondering and turns it "
            "off.\n\n"
            + _HC_OWN + "\n\n"
            "And if something is a little off, it is almost always the ordinary "
            "kind, the sort a supplement and a follow up sorts out.\n\n"
            "Here is what you get:\n" + HC_BULLETS_EMOJI + "\n\n"
            "Confirm nothing has changed. Tap below. \U0001F447"
        ),
        "older": (
            "Most results come back fine. That is the likely outcome here, and "
            "it is worth having in writing. ✅\n\n"
            "A clear panel is not a wasted morning. It is a year of not "
            "wondering, and a record to hold the next one against.\n\n"
            + _HC_OWN + "\n\n"
            "If something needs attention, it is far better found now, when the "
            "answer is usually straightforward.\n\n"
            + HC_BULLETS_PLAIN + "\n\n"
            "Confirm everything is where it should be. Tap below."
        ),
    },
}


# ===========================================================================
# Telehealth
# ===========================================================================

TH = {
    "friction": {
        "young": (
            "A doctor in about fifteen minutes, from wherever you already are. "
            "⚡\n\n"
            "No commute, no waiting room, no morning given up to a queue. You "
            "open the app, pick a specialist, and talk.\n\n"
            "Your Plum benefits include unlimited consults, so this costs you "
            "nothing beyond the fifteen minutes.\n\n"
            "Here is what you get:\n" + TH_BULLETS_EMOJI + "\n\n"
            "Fifteen minutes, not a whole morning. Tap below. \U0001F447"
        ),
        "older": (
            "A verified doctor in roughly fifteen minutes, without leaving the "
            "house. ⚡\n\n"
            "No commute, no waiting room, no half day spent on something that "
            "needed one short conversation.\n\n"
            "Consultations are included in your Plum cover, so there is nothing "
            "to pay and nothing to claim back.\n\n"
            + TH_BULLETS_PLAIN + "\n\n"
            "One short call, whenever it suits you. Tap below."
        ),
    },
    "normalised_symptoms": {
        "young": (
            "The headache that shows up every afternoon. The sleep that never "
            "quite lands. The stomach thing you have stopped mentioning. "
            "\U0001F914\n\n"
            "None of it is dramatic enough to act on, which is exactly why it "
            "has been going on for months.\n\n"
            "A consult is included in your Plum benefits, and fifteen minutes is "
            "usually enough to find out whether it is nothing or something "
            "simple.\n\n"
            "Here is what you get:\n" + TH_BULLETS_EMOJI + "\n\n"
            "Ask about the thing you keep ignoring. Tap below. \U0001F447"
        ),
            "older": (
            "The recurring headache. The sleep that never quite settles. The "
            "digestion you have stopped mentioning. \U0001F914\n\n"
            "Nothing urgent enough to take action on, so it quietly continues "
            "for months and becomes normal.\n\n"
            "A consultation is included in your cover. Fifteen minutes is "
            "usually enough to know whether it needs anything at all.\n\n"
            + TH_BULLETS_PLAIN + "\n\n"
            "Worth asking about once. Tap below to talk to someone."
        ),
    },
    "mental_health": {
        "young": (
            "Talking to someone should not be a whole production. \U0001F4AC\n\n"
            "No referral, no explaining yourself to three people first, nothing "
            "that goes anywhere near your manager. You book a slot and you talk, "
            "and it is entirely private.\n\n"
            "Your Plum benefits cover sessions with qualified psychologists and "
            "psychiatrists, the same as any other consult.\n\n"
            "Here is what you get:\n" + TH_BULLETS_EMOJI + "\n\n"
            "Book a first conversation. Tap below. \U0001F447"
        ),
        "older": (
            "Talking to someone is a normal thing to do, and it is covered. "
            "\U0001F4AC\n\n"
            "No referral needed, no explaining yourself first, and nothing that "
            "reaches anyone at work. You pick a time and you talk.\n\n"
            "Sessions with qualified psychologists and psychiatrists are "
            "included in your Plum cover, like any other consultation.\n\n"
            + TH_BULLETS_PLAIN + "\n\n"
            "A first conversation is enough to start. Tap below."
        ),
    },
    "nutrition": {
        "young": (
            "Tired by four in the afternoon, and it has nothing to do with how "
            "much you slept. \U0001F957\n\n"
            "Energy, appetite and weight all run on what you eat and when, and "
            "most advice you find online is written for somebody else.\n\n"
            "Your Plum benefits include consults with qualified nutritionists, "
            "so you can get a plan built around what you actually eat rather "
            "than a diet you will abandon.\n\n"
            "Here is what you get:\n" + TH_BULLETS_EMOJI + "\n\n"
            "Get a plan that fits your week. Tap below. \U0001F447"
        ),
        "older": (
            "Energy, appetite and weight all track back to food, and generic "
            "advice rarely survives a real week. \U0001F957\n\n"
            "A nutritionist can work from what you already eat and adjust it, "
            "rather than handing you a diet to abandon by Thursday.\n\n"
            "These consultations are included in your Plum cover, with follow "
            "ups, so the plan can change as it needs to.\n\n"
            + TH_BULLETS_PLAIN + "\n\n"
            "Build a plan around your actual week. Tap below."
        ),
    },
}


YOUNG = {"u20", "21_25", "26_35"}

BY_OBJECTIVE = {"hc_activation": HC, "th_activation": TH}


def has(objective: str, angle: str | None) -> bool:
    """Is there angle-specific WhatsApp copy for this pairing?"""
    return bool(angle) and angle in BY_OBJECTIVE.get(objective, {})


def body(objective: str, angle: str, band: str) -> str:
    """The angle's WhatsApp body for this band's tier."""
    tier = "young" if band in YOUNG else "older"
    return BY_OBJECTIVE[objective][angle][tier]


def angles_for(objective: str) -> list[str]:
    return list(BY_OBJECTIVE.get(objective, {}).keys())
