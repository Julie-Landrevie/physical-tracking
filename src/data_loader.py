"""
src/data_loader.py
------------------
Ce fichier s'occupe de TÉLÉCHARGER et CHARGER les données SkillCorner.

SkillCorner open data (version actuelle) = 10 matchs A-League 2024/2025.
Les données sont hébergées sur GitHub et téléchargeables gratuitement.

Pour chaque match, les fichiers disponibles sont :
  1. {id}_match.json          → infos du match (équipes, joueurs, score...)
  2. {id}_dynamic_events.csv  → actions des joueurs avec vitesse, distance, positions
  3. {id}_phases_of_play.csv  → phases de jeu (possession, transition...)

NOTE TECHNIQUE : Le tracking XY brut (positions frame par frame) est stocké
dans Git LFS (Large File Storage) — non accessible via raw.githubusercontent.
On utilise donc les dynamic_events qui contiennent déjà les métriques physiques
clés : distance_covered, speed_avg, x_start/x_end, y_start/y_end.
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional
from io import StringIO

# ============================================================
# URL ET FICHIERS
# ============================================================

BASE_URL = "https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches"
MATCHES_URL = "https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches.json"

# Zones d'intensité standard (basées sur speed_avg_band de SkillCorner)
# SkillCorner utilise : walking, jogging, lsr (low speed running),
#                       hsr (high speed running), sprinting
# Mapping exact des valeurs SkillCorner dans dynamic_events
# jogging = 0-15 km/h | running = 15-20 | hsr = 20-25 | sprinting = >25
SPEED_ZONES_SKC = {
    "Jogging":         "jogging",
    "Running":         "running",
    "Haute intensité": "hsr",
    "Sprint":          "sprinting",
}

ZONE_COLORS = {
    "Jogging":         "#8BC34A",
    "Running":         "#FFC107",
    "Haute intensité": "#FF5722",
    "Sprint":          "#F44336",
}

# Zones numériques pour le calcul depuis speed_avg (km/h)
SPEED_ZONES_KMH = {
    "Jogging":         (0.0,  15.0),
    "Running":         (15.0, 20.0),
    "Haute intensité": (20.0, 25.0),
    "Sprint":          (25.0, 999.0),
}


# ============================================================
# CHARGEMENT DE LA LISTE DES MATCHS
# ============================================================

@st.cache_data(show_spinner=False)
def load_matches_list() -> list:
    """
    Charge la liste de tous les matchs disponibles depuis matches.json.
    Retourne une liste de dicts avec id, home_team, away_team, date_time.
    """
    try:
        r = requests.get(MATCHES_URL, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur chargement liste des matchs : {e}")
        return []


def get_matches_dict() -> dict:
    """
    Retourne un dictionnaire {match_id: infos} pour faciliter l'accès.
    """
    matches = load_matches_list()
    result = {}
    for m in matches:
        result[m["id"]] = {
            "home":        m["home_team"]["short_name"],
            "away":        m["away_team"]["short_name"],
            "home_id":     m["home_team"]["id"],
            "away_id":     m["away_team"]["id"],
            "date":        m["date_time"][:10],
            "competition": "A-League 2024/2025",
        }
    return result


def get_match_label(match_id: int, matches_dict: dict = None) -> str:
    """Retourne le label lisible d'un match."""
    if matches_dict is None:
        matches_dict = get_matches_dict()
    info = matches_dict.get(match_id, {})
    if not info:
        return f"Match {match_id}"
    return f"{info['home']} vs {info['away']} ({info['date']})"


# ============================================================
# CHARGEMENT DES DONNÉES D'UN MATCH
# ============================================================

@st.cache_data(show_spinner=False)
def load_match_metadata(match_id: int) -> Optional[dict]:
    """
    Charge les métadonnées d'un match : équipes, joueurs, score, stade.

    Le fichier {id}_match.json contient :
    - home_team / away_team : nom, couleurs du maillot
    - home_team_score / away_team_score : score final
    - players : liste de tous les joueurs avec leur position
    - stadium : nom et ville du stade
    """
    url = f"{BASE_URL}/{match_id}/{match_id}_match.json"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Erreur chargement match_data {match_id}: {e}")
        return None


@st.cache_data(show_spinner=False)
def load_dynamic_events(match_id: int) -> Optional[pd.DataFrame]:
    """
    Charge les événements dynamiques du match.

    Ce fichier CSV contient une ligne par action (possession, course, engagement...)
    avec les colonnes physiques clés :
      - distance_covered : distance parcourue pendant l'action (mètres)
      - speed_avg        : vitesse moyenne pendant l'action (km/h)
      - speed_avg_band   : zone d'intensité (walking/jogging/lsr/hsr/sprinting)
      - x_start, y_start : position de début de l'action sur le terrain
      - x_end, y_end     : position de fin de l'action
      - player_name      : nom du joueur
      - team_shortname   : nom de l'équipe
      - period           : 1 (1ère mi-temps) ou 2 (2ème mi-temps)
      - minute_start     : minute de l'action
    """
    url = f"{BASE_URL}/{match_id}/{match_id}_dynamic_events.csv"
    try:
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text), low_memory=False)
        return df
    except Exception as e:
        st.error(f"Erreur chargement dynamic_events {match_id}: {e}")
        return None


# ============================================================
# CALCUL DES MÉTRIQUES PHYSIQUES PAR JOUEUR
# ============================================================

@st.cache_data(show_spinner=False)
def compute_player_metrics(match_id: int) -> Optional[pd.DataFrame]:
    """
    Calcule les métriques physiques agrégées par joueur sur tout le match.

    On agrège les dynamic_events pour chaque joueur :
    - Distance totale = somme des distance_covered de toutes ses actions
    - Vitesse max = max des speed_avg
    - Distance par zone = somme des distance_covered filtrée par speed_avg_band
    - Nombre de sprints = nombre d'actions dans la zone 'sprinting'
    - Distance haute intensité = distance en 'hsr' + 'sprinting'

    Returns
    -------
    DataFrame avec une ligne par joueur et toutes les métriques
    """
    df = load_dynamic_events(match_id)
    if df is None or df.empty:
        return None

    # Garder uniquement les actions des joueurs (pas du ballon/arbitre)
    # et les colonnes physiques qui nous intéressent
    needed_cols = [
        "player_id", "player_name", "player_position",
        "team_id", "team_shortname",
        "distance_covered", "speed_avg", "speed_avg_band",
        "x_start", "y_start", "x_end", "y_end",
        "period", "minute_start", "event_type"
    ]
    available = [c for c in needed_cols if c in df.columns]
    df = df[available].copy()

    # Garder uniquement les lignes avec un joueur identifié
    df = df.dropna(subset=["player_id", "player_name"])

    # Convertir les types numériques
    for col in ["distance_covered", "speed_avg"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    results = []

    for player_id, group in df.groupby("player_id"):
        player_name  = group["player_name"].iloc[0]
        team_name    = group["team_shortname"].iloc[0] if "team_shortname" in group.columns else "?"
        position     = group["player_position"].iloc[0] if "player_position" in group.columns else "?"

        # --- Distance totale (en mètres) ---
        total_dist_m = group["distance_covered"].sum() if "distance_covered" in group.columns else 0

        # --- Vitesse max ---
        max_speed = group["speed_avg"].max() if "speed_avg" in group.columns else 0

        # --- Distance par zone d'intensité (via speed_avg_band SkillCorner) ---
        zone_metrics = {}
        if "speed_avg_band" in group.columns and "distance_covered" in group.columns:
            for zone_fr, zone_skc in SPEED_ZONES_SKC.items():
                mask = group["speed_avg_band"] == zone_skc
                zone_metrics[f"dist_{zone_fr}"] = round(group.loc[mask, "distance_covered"].sum(), 1)
        else:
            # Fallback : calculer depuis speed_avg numérique
            for zone_fr, (low, high) in SPEED_ZONES_KMH.items():
                mask = (group["speed_avg"] >= low) & (group["speed_avg"] < high)
                zone_metrics[f"dist_{zone_fr}"] = round(group.loc[mask, "distance_covered"].sum(), 1)

        # --- Nombre de sprints (actions en zone sprint) ---
        if "speed_avg_band" in group.columns:
            sprint_count = (group["speed_avg_band"] == "sprinting").sum()
        else:
            sprint_count = (group["speed_avg"] >= 23.0).sum()

        # --- Distance haute intensité (hsr + sprinting, norme UEFA > 19 km/h) ---
        # HIR = High Intensity Running = actions en hsr + sprinting (>20 km/h, norme SkillCorner)
        hir_dist = zone_metrics.get("dist_Haute intensité", 0) + zone_metrics.get("dist_Sprint", 0)

        # --- Temps de jeu estimé (minutes observées) ---
        if "minute_start" in group.columns:
            time_obs = group["minute_start"].max() - group["minute_start"].min()
        else:
            time_obs = 90

        results.append({
            "player_id":         player_id,
            "player_name":       player_name,
            "team_name":         team_name,
            "position":          position,
            "total_distance_m":  round(total_dist_m, 0),
            "total_distance_km": round(total_dist_m / 1000, 2),
            "max_speed_kmh":     round(max_speed, 1),
            "sprint_count":      int(sprint_count),
            "hir_distance_m":    round(hir_dist, 0),
            "time_observed_min": round(time_obs, 1),
            **zone_metrics
        })

    if not results:
        return None

    result_df = pd.DataFrame(results)

    # Distance / 90 min normalisée
    result_df["dist_per_90"] = result_df.apply(
        lambda r: round(r["total_distance_km"] / r["time_observed_min"] * 90, 2)
        if r["time_observed_min"] > 0 else 0,
        axis=1
    )

    # Ajouter le label du match
    matches_dict = get_matches_dict()
    result_df["match_label"] = get_match_label(match_id, matches_dict)
    result_df["match_id"]    = match_id

    return result_df.sort_values("total_distance_km", ascending=False).reset_index(drop=True)


def compute_speed_timeline(match_id: int, player_id) -> pd.DataFrame:
    """
    Retourne l'évolution de la vitesse d'un joueur au fil du match.

    On utilise les vitesses BRUTES par action (pas agrégées par minute),
    ce qui permet de voir les vrais pics de sprint sur la courbe.

    Pourquoi c'est important :
      Un sprint dure 2-3 secondes. Si on agrège par minute, la vitesse
      de sprint se noie dans la moyenne et disparaît visuellement —
      alors que le sprint a bien eu lieu et est comptabilisé dans les stats.

    On place chaque action à sa minute de début (minute_start) +
    sa fraction de seconde (second_start/60) pour un positionnement précis.

    Returns
    -------
    DataFrame avec colonnes : minutes, speed_avg, speed_avg_band, period
    """
    df = load_dynamic_events(match_id)
    if df is None or df.empty:
        return pd.DataFrame()

    player_df = df[df["player_id"] == player_id].copy()
    if player_df.empty:
        return pd.DataFrame()

    for col in ["speed_avg", "minute_start", "second_start"]:
        if col in player_df.columns:
            player_df[col] = pd.to_numeric(player_df[col], errors="coerce")

    player_df = player_df.dropna(subset=["speed_avg", "minute_start"])

    # Position précise dans le match : minute + seconde/60
    if "second_start" in player_df.columns:
        player_df["minutes"] = player_df["minute_start"] + player_df["second_start"].fillna(0) / 60
    else:
        player_df["minutes"] = player_df["minute_start"]

    if "period" not in player_df.columns:
        player_df["period"] = player_df["minutes"].apply(lambda m: 1 if m <= 45 else 2)

    cols = ["minutes", "speed_avg", "period"]
    if "speed_avg_band" in player_df.columns:
        cols.append("speed_avg_band")

    return player_df[cols].sort_values("minutes").reset_index(drop=True)


def get_player_positions(match_id: int, player_id) -> pd.DataFrame:
    """
    Retourne toutes les positions (x, y) d'un joueur pour la heatmap.
    Utilise les x_start, y_start des dynamic_events.
    """
    df = load_dynamic_events(match_id)
    if df is None or df.empty:
        return pd.DataFrame()

    player_df = df[df["player_id"] == player_id].copy()

    pos_cols = [c for c in ["x_start", "y_start"] if c in player_df.columns]
    if not pos_cols:
        return pd.DataFrame()

    player_df = player_df[pos_cols + (["period"] if "period" in player_df.columns else [])].copy()
    player_df = player_df.rename(columns={"x_start": "x", "y_start": "y"})
    player_df = player_df.dropna(subset=["x", "y"])

    for col in ["x", "y"]:
        player_df[col] = pd.to_numeric(player_df[col], errors="coerce")

    return player_df.dropna()
