"""
src/data_loader.py
------------------
Ce fichier s'occupe de TÉLÉCHARGER et CHARGER les données SkillCorner.

SkillCorner open data = 10 matchs de la saison 2019/2020 (top 5 ligues européennes).
Les données sont hébergées sur GitHub et téléchargeables gratuitement.

Pour chaque match, il y a 2 fichiers :
  1. match_data.json   → infos du match (équipes, joueurs, score...)
  2. structured_data.json → données de tracking (positions x/y à 10 images/seconde)

Ce qu'est le "broadcast tracking" :
  - SkillCorner extrait les positions des joueurs depuis les images TV
  - Pas besoin de caméras spéciales comme dans les stades pro
  - Avantage : fonctionne sur n'importe quel match diffusé à la TV
  - Limite : quand la caméra zoome ou fait un replay, les données sont manquantes
"""

import json
import requests
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional

# ============================================================
# LISTE DES 10 MATCHS OPEN DATA SKILLCORNER
# ============================================================
# Ces matchs viennent de la saison 2019/2020 dans les top 5 ligues.
# Chaque match a un identifiant numérique unique (le "match_id").

MATCHES_INFO = {
    2417: {"home": "Manchester City",   "away": "Liverpool",      "competition": "Premier League", "date": "2019-11-10"},
    2440: {"home": "Juventus",          "away": "Inter Milan",    "competition": "Serie A",        "date": "2020-03-08"},
    2841: {"home": "Real Madrid",       "away": "Barcelona",      "competition": "La Liga",        "date": "2020-03-01"},
    3442: {"home": "Bayern Munich",     "away": "Borussia Dortmund", "competition": "Bundesliga",  "date": "2020-05-26"},
    3518: {"home": "PSG",               "away": "Lyon",           "competition": "Ligue 1",        "date": "2020-02-09"},
    3749: {"home": "RB Leipzig",        "away": "Tottenham",      "competition": "Champions League","date": "2020-02-19"},
    4039: {"home": "Barcelona",         "away": "Napoli",         "competition": "Champions League","date": "2020-08-08"},
    4040: {"home": "Man City",          "away": "Real Madrid",    "competition": "Champions League","date": "2020-08-07"},
    5065: {"home": "Liverpool",         "away": "Atletico Madrid","competition": "Champions League","date": "2020-03-11"},
    5104: {"home": "Bayern Munich",     "away": "Chelsea",        "competition": "Champions League","date": "2020-03-25"},
}

# URL de base pour télécharger les fichiers depuis GitHub
BASE_URL = "https://raw.githubusercontent.com/SkillCorner/opendata/master/data/matches"


# ============================================================
# FONCTIONS DE CHARGEMENT
# ============================================================

@st.cache_data(show_spinner=False)
def load_match_metadata(match_id: int) -> Optional[dict]:
    """
    Charge les métadonnées d'un match (équipes, joueurs, score).
    
    Parameters
    ----------
    match_id : int
        L'identifiant du match (ex: 2417 pour Man City vs Liverpool)
    
    Returns
    -------
    dict ou None
        Dictionnaire avec toutes les infos du match, ou None si erreur
    """
    url = f"{BASE_URL}/{match_id}/match_data.json"
    try:
        # requests.get() télécharge le contenu de l'URL
        response = requests.get(url, timeout=10)
        # raise_for_status() provoque une erreur si le téléchargement a échoué
        response.raise_for_status()
        # json() transforme le texte JSON en dictionnaire Python
        return response.json()
    except Exception as e:
        st.error(f"Erreur chargement match_data {match_id}: {e}")
        return None


@st.cache_data(show_spinner=False)
def load_tracking_data(match_id: int) -> Optional[list]:
    """
    Charge les données de tracking (positions des joueurs frame par frame).
    
    ATTENTION : Ces fichiers sont volumineux (~50-150 Mo) !
    Le chargement peut prendre 30 secondes à 2 minutes.
    
    Structure d'une frame :
    {
        "frame": 12345,           ← numéro de l'image vidéo
        "timestamp": "12:34.5",   ← moment du match
        "period": 1,              ← 1 = 1ère mi-temps, 2 = 2ème mi-temps
        "data": [                 ← liste de tous les objets trackés
            {
                "trackable_object": 42,   ← ID du joueur ou du ballon
                "x": 25.3,               ← position horizontale (-52.5 à 52.5)
                "y": 10.1,               ← position verticale (-34 à 34)
                "speed": 4.2             ← vitesse en m/s (si disponible)
            }
        ]
    }
    """
    url = f"{BASE_URL}/{match_id}/structured_data.json"
    try:
        response = requests.get(url, timeout=120)  # 120s timeout pour gros fichiers
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur chargement tracking {match_id}: {e}")
        return None


# ============================================================
# TRANSFORMATION DES DONNÉES EN TABLEAU (DataFrame)
# ============================================================

@st.cache_data(show_spinner=False)
def build_player_speeds_df(match_id: int) -> Optional[pd.DataFrame]:
    """
    Construit un DataFrame avec les vitesses de chaque joueur à chaque frame.
    
    C'est la transformation principale : on passe de données brutes JSON
    (listes imbriquées) à un tableau propre utilisable pour l'analyse.
    
    Returns
    -------
    DataFrame avec colonnes : frame, timestamp, period, player_id, x, y, speed
    """
    meta = load_match_metadata(match_id)
    tracking = load_tracking_data(match_id)
    
    if not meta or not tracking:
        return None
    
    # Créer un dictionnaire {trackable_object_id: nom_du_joueur}
    # pour pouvoir nommer les joueurs dans le tableau final
    player_map = {}
    for player in meta.get("players", []):
        obj_id = player.get("trackable_object")
        if obj_id:
            name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
            team_id = player.get("team_id")
            player_map[obj_id] = {
                "name": name,
                "team_id": team_id,
                "number": player.get("number"),
                "position": player.get("player_role", {}).get("name", "Unknown") if player.get("player_role") else "Unknown"
            }
    
    # Identifier les deux équipes
    teams = meta.get("teams", [])
    team_names = {t["id"]: t["name"] for t in teams} if teams else {}
    
    # Parcourir chaque frame et extraire les données joueur par joueur
    rows = []
    for frame_data in tracking:
        frame_num = frame_data.get("frame", 0)
        timestamp = frame_data.get("timestamp", "")
        period = frame_data.get("period", 0)
        
        # Ignorer les frames sans période valide (replays, pauses...)
        if period not in [1, 2]:
            continue
        
        for obj in frame_data.get("data", []):
            obj_id = obj.get("trackable_object")
            
            # Ne garder que les joueurs (pas le ballon)
            if obj_id not in player_map:
                continue
            
            player_info = player_map[obj_id]
            speed_ms = obj.get("speed")  # vitesse en mètres/seconde
            
            rows.append({
                "frame": frame_num,
                "timestamp": timestamp,
                "period": period,
                "player_id": obj_id,
                "player_name": player_info["name"],
                "team_id": player_info["team_id"],
                "team_name": team_names.get(player_info["team_id"], "Unknown"),
                "position": player_info["position"],
                "number": player_info["number"],
                "x": obj.get("x"),
                "y": obj.get("y"),
                # Conversion m/s → km/h : multiplier par 3.6
                "speed_ms": speed_ms,
                "speed_kmh": round(speed_ms * 3.6, 2) if speed_ms is not None else None,
            })
    
    if not rows:
        return None
    
    df = pd.DataFrame(rows)
    
    # Ajouter le nom du match pour référence
    match_info = MATCHES_INFO.get(match_id, {})
    df["match_label"] = f"{match_info.get('home', '')} vs {match_info.get('away', '')}"
    df["competition"] = match_info.get("competition", "")
    df["match_date"] = match_info.get("date", "")
    df["match_id"] = match_id
    
    return df


# ============================================================
# CALCUL DES MÉTRIQUES PHYSIQUES PAR JOUEUR
# ============================================================

# Définition des zones d'intensité (standard dans l'analyse physique foot)
# Source : classification couramment utilisée dans les clubs professionnels
SPEED_ZONES = {
    "Marche":           (0.0, 7.0),    # 0 → 7 km/h
    "Jogging":          (7.0, 14.0),   # 7 → 14 km/h
    "Course modérée":   (14.0, 19.0),  # 14 → 19 km/h (High Intensity Running commence ici)
    "Course intense":   (19.0, 23.0),  # 19 → 23 km/h (High Intensity Running)
    "Sprint":           (23.0, 999.0), # > 23 km/h (Sprinting)
}

# Codes couleur pour chaque zone (du plus calme au plus intense)
ZONE_COLORS = {
    "Marche":           "#4CAF50",  # Vert
    "Jogging":          "#8BC34A",  # Vert clair
    "Course modérée":   "#FFC107",  # Jaune/orange
    "Course intense":   "#FF5722",  # Orange vif
    "Sprint":           "#F44336",  # Rouge
}


def compute_player_metrics(df_speeds: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule les métriques physiques agrégées par joueur sur tout le match.
    
    Les données de tracking sont à 10 fps (10 images par seconde).
    Donc chaque frame = 0.1 seconde.
    
    Métriques calculées :
    - Distance totale (km)
    - Distance par zone d'intensité
    - Nombre de sprints
    - Vitesse max atteinte
    - % du temps passé dans chaque zone
    """
    if df_speeds is None or df_speeds.empty:
        return pd.DataFrame()
    
    # Ignorer les frames sans données de vitesse
    df = df_speeds.dropna(subset=["speed_kmh"]).copy()
    
    # Chaque frame = 0.1 seconde = 1/10 de seconde
    dt = 0.1  # secondes par frame
    
    results = []
    
    for player_id, group in df.groupby("player_id"):
        # Trier par frame pour avoir les données dans l'ordre chronologique
        group = group.sort_values("frame")
        
        # Données de base
        player_name = group["player_name"].iloc[0]
        team_name = group["team_name"].iloc[0]
        position = group["position"].iloc[0]
        number = group["number"].iloc[0]
        
        speeds = group["speed_kmh"].values
        
        # --- Distance totale ---
        # distance = vitesse × temps
        # vitesse en km/h, temps en heures (dt/3600)
        distances_km = speeds * (dt / 3600)
        total_distance_km = distances_km.sum()
        
        # --- Temps total observable (en minutes) ---
        total_time_min = len(group) * dt / 60
        
        # --- Vitesse maximum ---
        max_speed = speeds.max()
        
        # --- Métriques par zone ---
        zone_metrics = {}
        for zone_name, (low, high) in SPEED_ZONES.items():
            mask = (speeds >= low) & (speeds < high)
            zone_frames = mask.sum()
            zone_dist = distances_km[mask].sum()
            
            zone_metrics[f"dist_{zone_name}"] = round(zone_dist * 1000, 1)  # en mètres
            zone_metrics[f"pct_{zone_name}"] = round(zone_frames / len(speeds) * 100, 1)
        
        # --- Nombre de sprints ---
        # Un sprint = entrée dans la zone "> 23 km/h"
        # On détecte chaque nouvelle "entrée" en sprint
        is_sprint = speeds >= 23.0
        # diff() detecte les changements : True→False ou False→True
        sprint_entries = (pd.Series(is_sprint).diff() == 1).sum()
        
        # --- Distance haute intensité (> 19 km/h, norme UEFA) ---
        high_intensity_mask = speeds >= 19.0
        hir_distance = distances_km[high_intensity_mask].sum() * 1000  # en mètres
        
        results.append({
            "player_id": player_id,
            "player_name": player_name,
            "team_name": team_name,
            "position": position,
            "number": number,
            "total_distance_km": round(total_distance_km, 2),
            "total_distance_m": round(total_distance_km * 1000, 0),
            "time_observed_min": round(total_time_min, 1),
            "max_speed_kmh": round(max_speed, 1),
            "sprint_count": int(sprint_entries),
            "hir_distance_m": round(hir_distance, 0),  # High Intensity Running
            **zone_metrics
        })
    
    result_df = pd.DataFrame(results)
    
    # Calcul distance/90min (normalisation standard en foot)
    if "time_observed_min" in result_df.columns:
        result_df["dist_per_90"] = round(
            result_df["total_distance_km"] / result_df["time_observed_min"] * 90, 2
        )
    
    return result_df.sort_values("total_distance_km", ascending=False)


def compute_speed_timeline(df_speeds: pd.DataFrame, player_id: int) -> pd.DataFrame:
    """
    Retourne l'évolution de la vitesse d'un joueur sur toute la durée du match.
    
    Utilisé pour les graphiques "vitesse en fonction du temps".
    
    Parameters
    ----------
    df_speeds : DataFrame issu de build_player_speeds_df()
    player_id : ID du joueur à analyser
    """
    player_df = df_speeds[df_speeds["player_id"] == player_id].copy()
    player_df = player_df.sort_values("frame").dropna(subset=["speed_kmh"])
    
    # Convertir les frames en minutes de jeu
    # Frame 0 = début du match, 10 frames = 1 seconde
    player_df["minutes"] = player_df["frame"] / (10 * 60)
    
    return player_df[["frame", "minutes", "period", "speed_kmh", "x", "y"]]


def get_match_label(match_id: int) -> str:
    """Retourne le label lisible d'un match : 'Man City vs Liverpool (Premier League)'"""
    info = MATCHES_INFO.get(match_id, {})
    if not info:
        return f"Match {match_id}"
    return f"{info['home']} vs {info['away']} — {info['competition']} ({info['date']})"
