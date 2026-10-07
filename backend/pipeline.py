"""
ML pipeline: feature engineering → clustering → persona discovery → prediction.

Personas emerge from K-Means clustering on real behavioral features.
The LLM writes narrative descriptions, but every claim traces to cluster statistics.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import json
from config import N_PERSONAS, RANDOM_SEED


# Features used for clustering (all numeric, behavioral)
CLUSTER_FEATURES = [
    "age",
    "tenure_months",
    "th_consult_count",
    "th_funnel_depth",
    "hc_booking_count",
    "hc_funnel_depth",
    "app_launches_30d",
    "days_since_active",
    "peak_activity_hour",
    "notif_response_rate",
    "campaign_fatigue",
    "wallet_expiry_days",
    # Encoded categoricals
    "has_app_enc",
    "is_dnd_enc",
    "has_th_booking_enc",
    "has_hc_booking_enc",
    "gender_female",
    "segment_ent",
    "segment_smb",
    "segment_mm",
]


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Convert raw user data into ML-ready feature matrix."""
    feat = df.copy()

    feat["has_app_enc"] = feat["has_app"].astype(float)
    feat["is_dnd_enc"] = feat["is_dnd"].astype(float)
    feat["has_th_booking_enc"] = feat["has_th_booking"].astype(float)
    feat["has_hc_booking_enc"] = feat["has_hc_booking"].astype(float)
    feat["gender_female"] = (feat["gender"] == "FEMALE").astype(float)
    feat["segment_ent"] = (feat["partner_segment"] == "ENT").astype(float)
    feat["segment_smb"] = (feat["partner_segment"] == "SMB").astype(float)
    feat["segment_mm"] = (feat["partner_segment"] == "MM").astype(float)

    return feat


def cluster_users(df: pd.DataFrame, n_clusters: int = N_PERSONAS) -> dict:
    """
    Run K-Means clustering and return persona definitions.

    Returns dict with:
    - labels: cluster assignment per user
    - personas: list of persona dicts with statistics
    - silhouette: model quality score
    - scaler: fitted StandardScaler
    - model: fitted KMeans
    """
    feat = engineer_features(df)
    X = feat[CLUSTER_FEATURES].fillna(0).values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, n_init=10)
    labels = kmeans.fit_predict(X_scaled)

    sil_score = silhouette_score(X_scaled, labels, sample_size=min(5000, len(X_scaled)))

    feat["cluster"] = labels

    personas = []
    for c in range(n_clusters):
        cluster_df = feat[feat["cluster"] == c]
        n = len(cluster_df)

        persona = {
            "id": c,
            "size": n,
            "share": round(n / len(feat), 3),

            # OBSERVED: demographics
            "avg_age": round(cluster_df["age"].mean(), 1),
            "female_share": round(cluster_df["gender_female"].mean(), 3),
            "segment_mix": {
                "ENT": round(cluster_df["segment_ent"].mean(), 3),
                "SMB": round(cluster_df["segment_smb"].mean(), 3),
                "MM": round(cluster_df["segment_mm"].mean(), 3),
                "EOR": round(1 - cluster_df[["segment_ent", "segment_smb", "segment_mm"]].sum(axis=1).mean(), 3),
            },

            # OBSERVED: engagement
            "app_installed_share": round(cluster_df["has_app_enc"].mean(), 3),
            "avg_app_launches_30d": round(cluster_df["app_launches_30d"].mean(), 1),
            "avg_days_since_active": round(cluster_df["days_since_active"].mean(), 1),
            "avg_notif_response_rate": round(cluster_df["notif_response_rate"].mean(), 3),
            "avg_campaign_fatigue": round(cluster_df["campaign_fatigue"].mean(), 3),
            "peak_hour_mode": int(cluster_df["peak_activity_hour"].mode().iloc[0]) if len(cluster_df) > 0 else 20,

            # OBSERVED: product usage
            "th_adoption_rate": round(cluster_df["has_th_booking_enc"].mean(), 3),
            "avg_th_consults": round(cluster_df["th_consult_count"].mean(), 1),
            "avg_th_funnel_depth": round(cluster_df["th_funnel_depth"].mean(), 2),
            "hc_adoption_rate": round(cluster_df["has_hc_booking_enc"].mean(), 3),
            "avg_hc_bookings": round(cluster_df["hc_booking_count"].mean(), 2),
            "avg_hc_funnel_depth": round(cluster_df["hc_funnel_depth"].mean(), 2),

            # OBSERVED: reachability
            "dnd_share": round(cluster_df["is_dnd_enc"].mean(), 3),
            "avg_tenure_months": round(cluster_df["tenure_months"].mean(), 1),
            "avg_wallet_expiry_days": round(cluster_df["wallet_expiry_days"].mean(), 1),

            # Channel reachability
            "channel_reach": {
                "whatsapp": round(cluster_df["whatsapp_reachable"].astype(float).mean(), 3),
                "email": round(cluster_df["email_reachable"].astype(float).mean(), 3),
                "push": round(cluster_df["push_reachable"].astype(float).mean(), 3),
            },

            # Top lifecycle states
            "lifecycle_distribution": cluster_df["lifecycle_state"].value_counts(normalize=True).head(3).to_dict(),

            # Top TH specialties
            "top_th_specialties": cluster_df[cluster_df["has_th_booking"]]["th_primary_specialty"].value_counts().head(3).to_dict() if cluster_df["has_th_booking"].any() else {},

            # HRA status distribution
            "hra_distribution": cluster_df["hra_status"].value_counts(normalize=True).to_dict(),

            # Age distribution histogram
            "age_distribution": {
                label: int(((cluster_df["age"] >= lo) & (cluster_df["age"] <= hi)).sum())
                for label, lo, hi in [("18-25", 18, 25), ("26-30", 26, 30), ("31-35", 31, 35), ("36-40", 36, 40), ("41-50", 41, 50), ("51+", 51, 100)]
            },

            # Gender distribution counts
            "male_count": int((cluster_df["gender"] == "MALE").sum()),
            "female_count": int((cluster_df["gender"] == "FEMALE").sum()),

            # App installed counts
            "app_installed_count": int(cluster_df["has_app_enc"].sum()),
            "app_not_installed_count": int((1 - cluster_df["has_app_enc"]).sum()),

            # Org type counts (absolute)
            "org_type_counts": {
                "ENT": int(cluster_df["segment_ent"].sum()),
                "SMB": int(cluster_df["segment_smb"].sum()),
                "MM": int(cluster_df["segment_mm"].sum()),
                "EOR": int((1 - cluster_df[["segment_ent", "segment_smb", "segment_mm"]].sum(axis=1)).clip(lower=0).sum()),
            },
        }
        personas.append(persona)

    # Sort by size descending
    personas.sort(key=lambda p: p["size"], reverse=True)
    for i, p in enumerate(personas):
        p["rank"] = i + 1

    return {
        "labels": labels,
        "personas": personas,
        "silhouette_score": round(sil_score, 4),
        "n_users": len(df),
        "n_clusters": n_clusters,
        "features_used": CLUSTER_FEATURES,
    }


def assign_persona_names(personas: list) -> list:
    """
    Assign descriptive names based on cluster characteristics.
    These are plain names — no fantasy naming.
    Guarantees unique names by using segment + behavioral differentiators.
    """
    for p in personas:
        # Engagement level
        if p["avg_days_since_active"] < 14:
            engagement = "Active"
        elif p["avg_days_since_active"] < 60:
            engagement = "Occasional"
        else:
            engagement = "Dormant"

        # Product affinity
        if p["th_adoption_rate"] > 0.15 and p["hc_adoption_rate"] > 0.15:
            product = "Dual-Product"
        elif p["th_adoption_rate"] > 0.15:
            product = "TH-Engaged"
        elif p["hc_adoption_rate"] > 0.15:
            product = "HC-Engaged"
        elif p["app_installed_share"] > 0.5:
            product = "Pre-Activation"
        elif p["app_installed_share"] < 0.05:
            product = "No-App"
        else:
            product = "Low-App"

        # Dominant segment as differentiator
        seg = max(p["segment_mix"], key=p["segment_mix"].get)

        # Behavioral modifier
        modifier = ""
        if p["dnd_share"] > 0.1:
            modifier = "DND-Locked"
        elif p["avg_campaign_fatigue"] > 0.5:
            modifier = "Fatigued"
        elif p["avg_tenure_months"] < 3:
            modifier = "New"
        elif p["avg_tenure_months"] > 9:
            modifier = "Tenured"
        elif p["avg_notif_response_rate"] > 0.35:
            modifier = "Responsive"
        elif p["avg_wallet_expiry_days"] < 60:
            modifier = "Expiring-Soon"

        p["name"] = f"{engagement} {product} ({seg})"
        if modifier:
            p["name"] = f"{engagement} {product} — {modifier} ({seg})"

    # Deduplicate: if names collide, differentiate by the metric that varies most
    name_groups: dict[str, list] = {}
    for p in personas:
        name_groups.setdefault(p["name"], []).append(p)

    for name, group in name_groups.items():
        if len(group) <= 1:
            continue
        # Find a distinguishing metric
        diff_options = [
            ("avg_notif_response_rate", lambda p: p["avg_notif_response_rate"], lambda v: "Responsive" if v > 0.3 else "Quiet"),
            ("avg_days_since_active", lambda p: p["avg_days_since_active"], lambda v: "Recent" if v < 30 else "Lapsed"),
            ("avg_tenure_months", lambda p: p["avg_tenure_months"], lambda v: "New" if v < 4 else "Tenured"),
            ("avg_age", lambda p: p["avg_age"], lambda v: f"~{v:.0f}y"),
            ("size", lambda p: p["size"], lambda v: "Large" if v > 500 else "Small"),
        ]
        # Pick the metric with the widest relative spread among colliding personas
        best_key, best_fn, best_fmt = diff_options[0]
        best_spread = 0
        for key, fn, fmt in diff_options:
            vals = [fn(p) for p in group]
            range_val = max(vals) - min(vals)
            denom = max(abs(max(vals)), 1e-6)
            spread = range_val / denom
            if spread > best_spread:
                best_spread = spread
                best_key, best_fn, best_fmt = key, fn, fmt

        # Sort group by the distinguishing metric and append a readable label
        group.sort(key=best_fn, reverse=True)
        for p in group:
            p["name"] = f"{p['name']} · {best_fmt(best_fn(p))}"

    return personas


def score_audience_fit(persona: dict, campaign_objective: str) -> dict:
    """
    Score how well a persona fits a campaign objective using continuous values.
    Returns a fit score (0-100) with reasoning.

    Uses actual data values for granular differentiation, not binary thresholds.
    All scores are RECOMMENDED — the system's suggestion based on OBSERVED data.
    """
    score = 0.0
    reasons = []

    if campaign_objective == "th_activation":
        # Headroom: lower adoption = more room to activate (0-30 pts)
        headroom = max(0, 1.0 - persona["th_adoption_rate"])
        score += headroom * 30
        if headroom > 0.8:
            reasons.append(f"TH adoption only {persona['th_adoption_rate']:.0%} — large activation headroom")

        # Warm intent: funnel exploration signals interest (0-25 pts)
        funnel_signal = min(persona["avg_th_funnel_depth"] / 3.0, 1.0)
        score += funnel_signal * 25
        if funnel_signal > 0.3:
            reasons.append(f"Already explored TH funnel (avg depth {persona['avg_th_funnel_depth']:.1f}/5)")

        # Reachability: app installed = push viable (0-20 pts)
        score += persona["app_installed_share"] * 20
        if persona["app_installed_share"] > 0.5:
            reasons.append(f"App installed ({persona['app_installed_share']:.0%}) — push + in-app viable")
        elif persona["app_installed_share"] < 0.05:
            reasons.append(f"No app ({persona['app_installed_share']:.0%}) — WhatsApp/email only")

        # Responsiveness (0-15 pts)
        score += persona["avg_notif_response_rate"] * 15

        # DND penalty (0-10 pts deducted)
        score -= persona["dnd_share"] * 10
        if persona["dnd_share"] > 0.1:
            reasons.append(f"DND share {persona['dnd_share']:.0%} limits reach")

    elif campaign_objective == "hc_activation":
        headroom = max(0, 1.0 - persona["hc_adoption_rate"])
        score += headroom * 25
        if headroom > 0.8:
            reasons.append(f"HC adoption only {persona['hc_adoption_rate']:.0%} — large headroom")

        # Urgency: wallet expiring soon (0-25 pts, peaks at <60 days)
        urgency = max(0, 1.0 - persona["avg_wallet_expiry_days"] / 365)
        score += urgency * 25
        if persona["avg_wallet_expiry_days"] < 90:
            reasons.append(f"Wallet expires in ~{persona['avg_wallet_expiry_days']:.0f} days — natural urgency")

        # Funnel warmth (0-20 pts)
        funnel = min(persona["avg_hc_funnel_depth"] / 3.0, 1.0)
        score += funnel * 20
        if funnel > 0.3:
            reasons.append(f"HC funnel explored (avg depth {persona['avg_hc_funnel_depth']:.1f}/5)")

        score += persona["app_installed_share"] * 15
        score += persona["avg_notif_response_rate"] * 15

    elif campaign_objective == "app_install":
        # Inverse: fewer app installs = better target (0-40 pts)
        no_app = 1.0 - persona["app_installed_share"]
        score += no_app * 40
        if no_app > 0.7:
            reasons.append(f"Only {persona['app_installed_share']:.0%} have app — prime install target")

        # Newer users more likely to install (0-25 pts)
        newness = max(0, 1.0 - persona["avg_tenure_months"] / 12)
        score += newness * 25
        if persona["avg_tenure_months"] < 3:
            reasons.append(f"Avg tenure {persona['avg_tenure_months']:.0f}mo — onboarding window open")

        score += persona["avg_notif_response_rate"] * 20
        # Low fatigue = better conversion
        score += (1.0 - persona["avg_campaign_fatigue"]) * 15

    elif campaign_objective == "reengagement":
        # More dormant = bigger reengagement target (0-30 pts)
        dormancy = min(persona["avg_days_since_active"] / 180, 1.0)
        score += dormancy * 30
        if persona["avg_days_since_active"] > 60:
            reasons.append(f"Avg {persona['avg_days_since_active']:.0f} days dormant — reengagement target")

        # Some responsiveness = recoverable (0-25 pts)
        score += persona["avg_notif_response_rate"] * 25
        if persona["avg_notif_response_rate"] > 0.15:
            reasons.append(f"Notif response {persona['avg_notif_response_rate']:.0%} — still recoverable")

        # Size matters for reengagement ROI (0-15 pts)
        score += min(persona["size"] / 3000, 1.0) * 15

        # Fatigue penalty (0-20 pts)
        fatigue_penalty = persona["avg_campaign_fatigue"] * 20
        score -= fatigue_penalty
        if persona["avg_campaign_fatigue"] > 0.5:
            reasons.append(f"Fatigue {persona['avg_campaign_fatigue']:.0%} — high opt-out risk")

    elif campaign_objective == "hc_crosssell":
        # Sweet spot: has TH but not HC (0-35 pts)
        th_user = min(persona["th_adoption_rate"] / 0.2, 1.0)
        hc_headroom = max(0, 1.0 - persona["hc_adoption_rate"])
        crosssell = th_user * hc_headroom
        score += crosssell * 35
        if persona["th_adoption_rate"] > 0.05 and persona["hc_adoption_rate"] < 0.1:
            reasons.append(f"TH users ({persona['th_adoption_rate']:.0%}) who haven't tried HC ({persona['hc_adoption_rate']:.0%})")

        score += persona["app_installed_share"] * 20
        score += persona["avg_notif_response_rate"] * 20
        # Wallet urgency helps
        urgency = max(0, 1.0 - persona["avg_wallet_expiry_days"] / 365)
        score += urgency * 15
        score += (1.0 - persona["avg_campaign_fatigue"]) * 10

    # Channel feasibility (0-10 pts)
    best_channel = max(persona["channel_reach"], key=persona["channel_reach"].get)
    best_reach = persona["channel_reach"][best_channel]
    score += best_reach * 10
    if best_reach > 0.9:
        reasons.append(f"High {best_channel} reachability ({best_reach:.0%})")

    score = max(0, min(100, round(score)))

    if not reasons:
        reasons.append(f"Baseline fit — {persona['size']} users, {best_channel} reachable")

    return {
        "persona_id": persona["id"],
        "persona_name": persona.get("name", f"Persona {persona['id']}"),
        "score": score,
        "reasons": reasons,
        "best_channel": best_channel,
        "label": "RECOMMENDED",
    }


if __name__ == "__main__":
    from synthetic import generate_users

    users = generate_users(10_000)
    result = cluster_users(users)

    personas = assign_persona_names(result["personas"])

    print(f"Silhouette score: {result['silhouette_score']}")
    print(f"Number of personas: {len(personas)}\n")

    for p in personas:
        print(f"  #{p['rank']} {p['name']}")
        print(f"     Size: {p['size']} ({p['share']:.1%}) | Age: {p['avg_age']} | App: {p['app_installed_share']:.0%}")
        print(f"     TH: {p['th_adoption_rate']:.1%} | HC: {p['hc_adoption_rate']:.1%} | Active: {p['avg_days_since_active']:.0f}d ago")
        print()

    print("\n--- Audience fit for 'hc_activation' ---")
    for p in personas:
        fit = score_audience_fit(p, "hc_activation")
        print(f"  {fit['persona_name']}: {fit['score']}/100 — {', '.join(fit['reasons'][:2])}")
