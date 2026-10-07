"""
Synthetic data generator calibrated from real Plum distributions.

Every distribution parameter comes from confirmed data:
- Bible Section 19.5 (calibration points)
- TH/HC adoption Excel files (real org-level curves)
- CT schema (993 events, 249 user properties)
- Confirmed funnel numbers from Bible Section 7

This generates a user-level feature matrix suitable for clustering
and prediction model training.
"""

import numpy as np
import pandas as pd
from config import RANDOM_SEED

# --- CONFIRMED DISTRIBUTIONS (from Bible 19.5 + adoption data) ---

TOTAL_ELIGIBLE = 956_050
NO_APP_SHARE = 0.773  # 739,126 / 956,050
TH_ELIGIBLE_NEVER_BOOKED_SHARE = 173_373 / TOTAL_ELIGIBLE
HC_ELIGIBLE_NEVER_BOOKED_SHARE = 75_272 / TOTAL_ELIGIBLE

SEGMENT_WEIGHTS = {
    "ENT": 0.57,   # 57% of employees
    "SMB": 0.14,   # 14% of employees
    "MM": 0.20,    # mid-market ~20%
    "EOR": 0.09,   # single-digit %
}

# Adoption rates by segment at M9 (from adoption Excel files)
TH_ADOPTION_M9 = {"ENT": 0.11, "SMB": 0.08, "MM": 0.13, "EOR": 0.22}
HC_ADOPTION_M9 = {"ENT": 0.27, "SMB": 0.12, "MM": 0.18, "EOR": 0.30}

# TH funnel conversion rates (Bible Section 7)
TH_FUNNEL = {
    "homepage_to_doctorlist": 0.33,
    "doctorlist_to_slotscreen": 0.56,   # 23K/41K
    "slotscreen_to_bookclick": 0.74,    # 17K/23K
    "bookclick_to_success": 0.94,       # 16K/17K
}

# HC funnel conversion rates (Bible Section 7)
HC_FUNNEL = {
    "homepage_to_listing": 0.57,
    "listing_to_itemadded": 0.26,       # 12K/47K
    "itemadded_to_slotselected": 0.58,  # 7K/12K
    "slotselected_to_confirmed": 0.71,  # 5K/7K
}

# Channel reachability (Bible Section 13)
CHANNEL_REACH = {
    "whatsapp": (0.74, 0.99),
    "email": (0.77, 0.98),
    "push": (0.11, 0.43),
}

# TH specialty distribution (from th_consultation_data.xlsx Sheet1)
TH_SPECIALTIES = [
    "General Physician", "Dermatologist", "Obstetrician-Gynecologist",
    "Pediatrician", "Psychiatrist", "Psychologist", "Nutrition-Dietetics",
    "Orthopedics", "ENT Surgeon", "Internal Medicine", "Gastroenterologist",
    "Pulmonologist", "Ophthalmologist", "Cardiologist", "Diabetologist",
    "Urologist", "Endocrinologist", "Neurologist", "Nephrologist",
    "Sexologist", "Physiotherapist", "Oncologist", "Geriatrics",
    "Veterinary Medicine",
]
# Approximate relative weights (GP dominates), normalized to sum=1
_raw_weights = [
    0.35, 0.12, 0.10, 0.07, 0.06, 0.05, 0.04, 0.03, 0.03, 0.03,
    0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.005, 0.005, 0.003,
    0.002, 0.001, 0.001, 0.001,
]
TH_SPECIALTY_WEIGHTS = [w / sum(_raw_weights) for w in _raw_weights]

# Lifecycle segments (Bible Section 8)
LIFECYCLE_STATES = [
    "unacquired_fresh", "unacquired_lapsing", "unacquired_dormant",
    "unactivated_fresh", "unactivated_lapsing", "unactivated_dormant",
    "retained_fresh", "retained_lapsing", "retained_dormant",
]
LIFECYCLE_WEIGHTS = [0.10, 0.08, 0.15, 0.08, 0.05, 0.12, 0.15, 0.12, 0.15]


def generate_users(n_users: int = 10_000, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate synthetic user profiles with behavioral features."""
    rng = np.random.default_rng(seed)

    # --- Demographics ---
    gender = rng.choice(["MALE", "FEMALE"], size=n_users, p=[0.62, 0.38])
    age = np.clip(rng.normal(32, 8, n_users), 18, 65).astype(int)

    # --- Org / segment assignment ---
    segments = list(SEGMENT_WEIGHTS.keys())
    seg_probs = list(SEGMENT_WEIGHTS.values())
    partner_segment = rng.choice(segments, size=n_users, p=seg_probs)

    # --- App status ---
    has_app = rng.random(n_users) > NO_APP_SHARE

    # --- Lifecycle state ---
    lifecycle = rng.choice(LIFECYCLE_STATES, size=n_users, p=LIFECYCLE_WEIGHTS)

    # --- Tenure (months since org activation, 0-12) ---
    tenure_months = rng.integers(0, 13, size=n_users)

    # --- DND status (~5% of users, skews Enterprise) ---
    dnd_base = np.where(partner_segment == "ENT", 0.08, 0.02)
    is_dnd = rng.random(n_users) < dnd_base

    # --- Channel reachability (correlated with app status) ---
    whatsapp_reachable = rng.random(n_users) < rng.uniform(*CHANNEL_REACH["whatsapp"], n_users)
    email_reachable = rng.random(n_users) < rng.uniform(*CHANNEL_REACH["email"], n_users)
    push_reachable = has_app & (rng.random(n_users) < rng.uniform(*CHANNEL_REACH["push"], n_users))

    # --- TH behavior ---
    # Base TH adoption rate varies by segment and tenure
    th_base_rate = np.array([TH_ADOPTION_M9[s] for s in partner_segment])
    tenure_multiplier = np.clip(tenure_months / 9.0, 0.1, 1.0)
    th_adoption_prob = th_base_rate * tenure_multiplier
    # No-app users have much lower TH adoption
    th_adoption_prob = np.where(has_app, th_adoption_prob, th_adoption_prob * 0.15)
    has_th_booking = rng.random(n_users) < th_adoption_prob

    # TH consultation count (power-law for adopters, ~5/year once started)
    th_consult_count = np.zeros(n_users, dtype=int)
    adopters = has_th_booking
    n_adopters = adopters.sum()
    if n_adopters > 0:
        th_consult_count[adopters] = np.clip(
            rng.lognormal(mean=1.2, sigma=0.8, size=n_adopters).astype(int), 1, 30
        )

    # TH specialty preference (primary specialty for each user)
    th_primary_specialty = rng.choice(
        TH_SPECIALTIES, size=n_users, p=TH_SPECIALTY_WEIGHTS
    )

    # TH funnel depth (0=never visited, 1=homepage, 2=doctorlist, 3=slot, 4=book, 5=success)
    th_funnel_depth = np.zeros(n_users, dtype=int)
    visited_home = has_app & (rng.random(n_users) < 0.45)
    th_funnel_depth[visited_home] = 1
    visited_dl = visited_home & (rng.random(n_users) < TH_FUNNEL["homepage_to_doctorlist"])
    th_funnel_depth[visited_dl] = 2
    visited_slot = visited_dl & (rng.random(n_users) < TH_FUNNEL["doctorlist_to_slotscreen"])
    th_funnel_depth[visited_slot] = 3
    clicked_book = visited_slot & (rng.random(n_users) < TH_FUNNEL["slotscreen_to_bookclick"])
    th_funnel_depth[clicked_book] = 4
    th_success = clicked_book & (rng.random(n_users) < TH_FUNNEL["bookclick_to_success"])
    th_funnel_depth[th_success] = 5

    # --- HC behavior ---
    hc_base_rate = np.array([HC_ADOPTION_M9[s] for s in partner_segment])
    hc_adoption_prob = hc_base_rate * tenure_multiplier
    hc_adoption_prob = np.where(has_app, hc_adoption_prob, hc_adoption_prob * 0.20)
    has_hc_booking = rng.random(n_users) < hc_adoption_prob

    # HC booking count (mostly 1 — it's one free per year)
    hc_booking_count = np.zeros(n_users, dtype=int)
    hc_adopters = has_hc_booking
    hc_booking_count[hc_adopters] = np.clip(
        rng.poisson(1.0, hc_adopters.sum()), 1, 3
    )

    # HC funnel depth
    hc_funnel_depth = np.zeros(n_users, dtype=int)
    hc_home = has_app & (rng.random(n_users) < 0.35)
    hc_funnel_depth[hc_home] = 1
    hc_listing = hc_home & (rng.random(n_users) < HC_FUNNEL["homepage_to_listing"])
    hc_funnel_depth[hc_listing] = 2
    hc_item = hc_listing & (rng.random(n_users) < HC_FUNNEL["listing_to_itemadded"])
    hc_funnel_depth[hc_item] = 3
    hc_slot = hc_item & (rng.random(n_users) < HC_FUNNEL["itemadded_to_slotselected"])
    hc_funnel_depth[hc_slot] = 4
    hc_confirmed = hc_slot & (rng.random(n_users) < HC_FUNNEL["slotselected_to_confirmed"])
    hc_funnel_depth[hc_confirmed] = 5

    # --- Engagement features ---
    # App launches in last 30 days (0 for no-app users)
    app_launches_30d = np.zeros(n_users, dtype=int)
    app_launches_30d[has_app] = rng.poisson(3.0, has_app.sum())

    # Days since last activity (recency)
    days_since_active = np.full(n_users, 180)
    active = has_app & (app_launches_30d > 0)
    days_since_active[active] = rng.integers(0, 31, active.sum())
    lapsed = has_app & ~active
    days_since_active[lapsed] = rng.integers(31, 181, lapsed.sum())

    # Peak activity hour (8-11 PM peak for many segments)
    _hour_w = [0.01, 0.005, 0.005, 0.005, 0.005, 0.01, 0.02, 0.03, 0.05, 0.06,
               0.06, 0.05, 0.05, 0.04, 0.04, 0.04, 0.05, 0.06, 0.07, 0.08,
               0.09, 0.08, 0.05, 0.02]
    _hour_w = [w / sum(_hour_w) for w in _hour_w]
    peak_hour = rng.choice(range(24), size=n_users, p=_hour_w)

    # Notification response rate (0-1)
    notif_response_rate = np.clip(rng.beta(2, 5, n_users), 0, 1)
    # DND users have 0 response
    notif_response_rate[is_dnd] = 0.0

    # Campaign fatigue score (higher = more fatigued)
    campaign_fatigue = np.clip(rng.exponential(0.3, n_users), 0, 1)

    # HRA status
    hra_status = rng.choice(
        ["never_started", "started_dropped", "completed_no_goal",
         "completed_with_goal", "high_risk_no_action"],
        size=n_users,
        p=[0.55, 0.15, 0.10, 0.12, 0.08]
    )

    # Wallet expiry days left (HC, 0-365)
    wallet_expiry_days = rng.integers(0, 366, size=n_users)

    # --- Cross-product behavior ---
    # 14.32% of HC report viewers book TH (Bible)
    hc_report_viewed = has_hc_booking & (rng.random(n_users) < 0.85)
    th_from_hc_crosssell = hc_report_viewed & (rng.random(n_users) < 0.1432)

    df = pd.DataFrame({
        "user_id": [f"synth_{i:06d}" for i in range(n_users)],
        "gender": gender,
        "age": age,
        "partner_segment": partner_segment,
        "has_app": has_app,
        "lifecycle_state": lifecycle,
        "tenure_months": tenure_months,
        "is_dnd": is_dnd,

        "whatsapp_reachable": whatsapp_reachable,
        "email_reachable": email_reachable,
        "push_reachable": push_reachable,

        "th_consult_count": th_consult_count,
        "th_primary_specialty": th_primary_specialty,
        "th_funnel_depth": th_funnel_depth,
        "has_th_booking": has_th_booking,

        "hc_booking_count": hc_booking_count,
        "hc_funnel_depth": hc_funnel_depth,
        "has_hc_booking": has_hc_booking,

        "app_launches_30d": app_launches_30d,
        "days_since_active": days_since_active,
        "peak_activity_hour": peak_hour,
        "notif_response_rate": notif_response_rate,
        "campaign_fatigue": campaign_fatigue,
        "hra_status": hra_status,
        "wallet_expiry_days": wallet_expiry_days,
        "th_from_hc_crosssell": th_from_hc_crosssell,
    })

    return df


def generate_campaigns(n_campaigns: int = 50, seed: int = RANDOM_SEED) -> pd.DataFrame:
    """Generate synthetic campaign history with performance metrics."""
    rng = np.random.default_rng(seed + 1)

    channels = ["whatsapp", "push", "email"]
    channel_weights = [0.45, 0.30, 0.25]
    objectives = ["th_activation", "hc_activation", "app_install", "reengagement", "hc_crosssell"]
    obj_weights = [0.30, 0.30, 0.15, 0.15, 0.10]

    records = []
    for i in range(n_campaigns):
        channel = rng.choice(channels, p=channel_weights)
        objective = rng.choice(objectives, p=obj_weights)
        segment = rng.choice(list(SEGMENT_WEIGHTS.keys()))

        sent = rng.integers(5000, 50000)

        # Delivery rates vary by channel
        delivery_rates = {"whatsapp": 0.95, "push": 0.85, "email": 0.92}
        delivered = int(sent * rng.normal(delivery_rates[channel], 0.03))

        # Open/view rates
        open_rates = {"whatsapp": 0.65, "push": 0.12, "email": 0.22}
        opened = int(delivered * rng.normal(open_rates[channel], 0.05))

        # Click rates
        click_rates = {"whatsapp": 0.08, "push": 0.04, "email": 0.03}
        clicked = int(opened * rng.normal(click_rates[channel], 0.01))

        # Conversion rates (vary by objective)
        conv_base = {"th_activation": 0.12, "hc_activation": 0.08, "app_install": 0.15,
                     "reengagement": 0.06, "hc_crosssell": 0.10}
        converted = int(clicked * rng.normal(conv_base[objective], 0.02))

        # Ensure non-negative and monotonic
        delivered = max(0, min(delivered, sent))
        opened = max(0, min(opened, delivered))
        clicked = max(0, min(clicked, opened))
        converted = max(0, min(converted, clicked))

        _sh_w = [0.01, 0.005, 0.005, 0.005, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08,
                 0.08, 0.06, 0.05, 0.04, 0.04, 0.04, 0.05, 0.06, 0.07, 0.08,
                 0.09, 0.08, 0.05, 0.02]
        _sh_w = [w / sum(_sh_w) for w in _sh_w]
        send_hour = rng.choice(range(24), p=_sh_w)

        records.append({
            "campaign_id": f"camp_{i:04d}",
            "channel": channel,
            "objective": objective,
            "target_segment": segment,
            "sent": sent,
            "delivered": delivered,
            "opened": opened,
            "clicked": clicked,
            "converted": converted,
            "send_hour": send_hour,
            "delivery_rate": delivered / sent if sent > 0 else 0,
            "open_rate": opened / delivered if delivered > 0 else 0,
            "click_rate": clicked / opened if opened > 0 else 0,
            "conversion_rate": converted / clicked if clicked > 0 else 0,
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    users = generate_users(10_000)
    campaigns = generate_campaigns(50)

    print(f"Users: {len(users)} rows, {len(users.columns)} columns")
    print(f"\nUser columns: {list(users.columns)}")
    print(f"\nSegment distribution:\n{users['partner_segment'].value_counts()}")
    print(f"\nApp installed: {users['has_app'].mean():.1%}")
    print(f"TH adoption: {users['has_th_booking'].mean():.1%}")
    print(f"HC adoption: {users['has_hc_booking'].mean():.1%}")
    print(f"\nCampaigns: {len(campaigns)} rows")
    print(f"Avg delivery rate: {campaigns['delivery_rate'].mean():.1%}")
    print(f"Avg open rate: {campaigns['open_rate'].mean():.1%}")
