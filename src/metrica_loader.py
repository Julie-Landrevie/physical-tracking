"""
src/metrica_loader.py
---------------------
Chargement et traitement des données Metrica Sports Open Data.

Metrica = tracking XY complet frame par frame à 25 fps.
Contrairement à SkillCorner (actions sur balle uniquement),
Metrica enregistre la position de TOUS les joueurs à CHAQUE frame
→ on peut calculer le vrai kilométrage total du match.

3 matchs disponibles, joueurs anonymisés :
  - Sample_Game_1 : ~96 min
  - Sample_Game_2 : ~93 min
  - Sample_Game_3 : ~90 min (format légèrement différent)

Structure des fichiers :
  - RawTrackingData_Home_Team.csv : positions équipe domicile frame par frame
  - RawTrackingData_Away_Team.csv : positions équipe extérieur frame par frame
  - RawEventsData.csv             : événements (passes, tirs, duels...)

Coordonnées normalisées 0→1 (% du terrain).
On les convertit en mètres : x × 105, y × 68 (terrain standard FIFA).

FPS = 25 → chaque frame = 1/25 = 0.04 seconde
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
from io import StringIO
from typing import Optional

# ============================================================
# CONSTANTES
# ============================================================

BASE_URL = "https://raw.githubusercontent.com/metrica-sports/sample-data/master/data"

# Dimensions terrain standard (mètres)
PITCH_LENGTH = 105.0  # x
PITCH_WIDTH  = 68.0   # y

FPS = 25  # frames par seconde
DT  = 1 / FPS  # durée d'une frame en secondes

METRICA_MATCHES = {
    1: {"label": "Sample Game 1", "home": "Home", "away": "Away", "duration": "~96 min"},
    2: {"label": "Sample Game 2", "home": "Home", "away": "Away", "duration": "~93 min"},
}

# Zones d'intensité standard (mêmes seuils que SkillCorner pour comparaison)
SPEED_ZONES_M = {
    "Jogging":         (0.0,  15.0),
    "Running":         (15.0, 20.0),
    "Haute intensité": (20.0, 25.0),
    "Sprint":          (25.0, 999.0),
}

ZONE_COLORS = {
    "Jogging":         "#8BC34A",
    "Running":         "#FFC107",
    "Haute intensité": "#FF5722",
    "Sprint":          "#F44336",
}


# ============================================================
# CHARGEMENT DU TRACKING BRUT
# ============================================================

@st.cache_data(show_spinner=False)
def load_tracking_raw(game_id: int, team: str) -> Optional[pd.DataFrame]:
    """
    Charge le fichier CSV de tracking Metrica pour une équipe.

    Format du CSV :
      - Ligne 0 : nom de l'équipe ("Home" ou "Away")
      - Ligne 1 : numéro de maillot de chaque joueur
      - Ligne 2 : noms de colonnes (Period, Frame, Time [s], PlayerX, ...)
      - Lignes 3+ : données frame par frame

    Chaque joueur occupe 2 colonnes : x et y (coordonnées 0→1).

    Parameters
    ----------
    game_id : 1, 2
    team    : "Home" ou "Away"
    """
    fname = f"Sample_Game_{game_id}/Sample_Game_{game_id}_RawTrackingData_{team}_Team.csv"
    url = f"{BASE_URL}/{fname}"

    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()

        # Les 2 premières lignes contiennent les métadonnées d'équipe/numéro
        # On les lit séparément pour récupérer les numéros de maillot
        lines = r.text.split('\n')

        # Ligne 0 : équipe (Home/Away répété)
        # Ligne 1 : numéros de maillot
        jersey_numbers = lines[1].split(',')

        # Lire les données à partir de la ligne 2
        df = pd.read_csv(StringIO(r.text), skiprows=2, low_memory=False)

        # Renommer les colonnes "Unnamed:X" en "_y" pour clarté
        # Les colonnes vont par paires : PlayerX (=x), Unnamed:N (=y)
        new_cols = []
        for i, col in enumerate(df.columns):
            if col.startswith("Unnamed:") or col.startswith("Unnamed: "):
                # La colonne y suit toujours la colonne x du même joueur
                prev = df.columns[i - 1] if i > 0 else "Unknown"
                new_cols.append(f"{prev}_y")
            else:
                new_cols.append(col)
        df.columns = new_cols

        # Convertir en numérique
        for col in df.columns:
            if col not in ["Period", "Frame"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Garder uniquement les frames de jeu réelles (period 1 ou 2)
        df = df[df["Period"].isin([1, 2])].copy()

        return df

    except Exception as e:
        st.error(f"Erreur chargement Metrica {team} Game {game_id}: {e}")
        return None


# ============================================================
# TRANSFORMATION EN FORMAT LONG (un joueur par ligne)
# ============================================================

@st.cache_data(show_spinner=False)
def build_player_tracking_df(game_id: int, team: str) -> Optional[pd.DataFrame]:
    """
    Transforme le tracking wide (une ligne par frame, tous les joueurs)
    en format long (une ligne par frame × joueur).

    Calcule aussi la vitesse à chaque frame en km/h :
      distance_frame = √((Δx)² + (Δy)²)   en mètres
      speed_kmh = distance_frame / DT × 3.6

    Returns
    -------
    DataFrame avec colonnes :
      period, frame, time_s, minutes, player, x, y, speed_kmh
    """
    df_wide = load_tracking_raw(game_id, team)
    if df_wide is None:
        return None

    # Identifier les colonnes joueurs (tout sauf Period, Frame, Time, Ball)
    player_x_cols = [c for c in df_wide.columns
                     if c not in ["Period", "Frame", "Time [s]", "Ball", "Ball_y"]
                     and not c.endswith("_y")]

    rows = []

    for player_col in player_x_cols:
        y_col = f"{player_col}_y"
        if y_col not in df_wide.columns:
            continue

        player_df = df_wide[["Period", "Frame", "Time [s]", player_col, y_col]].copy()
        player_df = player_df.rename(columns={
            player_col: "x_norm",
            y_col: "y_norm"
        })
        player_df["player"] = player_col
        player_df["team"] = team

        # Convertir coordonnées normalisées → mètres
        player_df["x"] = player_df["x_norm"] * PITCH_LENGTH
        player_df["y"] = player_df["y_norm"] * PITCH_WIDTH

        # Garder uniquement les frames où le joueur est visible
        player_df = player_df.dropna(subset=["x", "y"])

        # Calcul de la vitesse frame par frame
        # dx et dy en mètres entre deux frames consécutives
        player_df = player_df.sort_values("Frame")
        dx = player_df["x"].diff()
        dy = player_df["y"].diff()

        # distance en mètres, convertie en km/h
        # Si un joueur disparaît plusieurs frames (hors caméra), le diff
        # donnerait une vitesse aberrante — on la plafonne à 40 km/h
        dist_m = np.sqrt(dx**2 + dy**2)
        speed_ms = dist_m / DT  # mètres/seconde
        speed_kmh = speed_ms * 3.6

        # Plafonnement à 40 km/h (vitesse max humaine ~44 km/h)
        player_df["speed_kmh"] = speed_kmh.clip(0, 40)
        player_df["distance_m_frame"] = dist_m.clip(0, 5)  # max 5m par frame à 25fps

        rows.append(player_df)

    if not rows:
        return None

    result = pd.concat(rows, ignore_index=True)
    result["minutes"] = result["Time [s]"] / 60
    result = result.rename(columns={"Period": "period", "Frame": "frame", "Time [s]": "time_s"})

    return result[["period", "frame", "time_s", "minutes", "player", "team",
                   "x", "y", "speed_kmh", "distance_m_frame"]]


# ============================================================
# CALCUL DES MÉTRIQUES PAR JOUEUR
# ============================================================

@st.cache_data(show_spinner=False)
def compute_metrica_metrics(game_id: int) -> Optional[pd.DataFrame]:
    """
    Calcule les métriques physiques complètes par joueur
    en combinant Home + Away.

    Métriques disponibles (vraies valeurs sur tout le match) :
      - Distance totale en km  (vrai kilométrage)
      - Vitesse max en km/h
      - Nombre de sprints
      - Distance HIR (>20 km/h)
      - Distance par zone d'intensité
      - Distance/90min
    """
    results = []

    for team in ["Home", "Away"]:
        with st.spinner(f"Chargement tracking {team}..."):
            df = build_player_tracking_df(game_id, team)

        if df is None or df.empty:
            continue

        for player, group in df.groupby("player"):
            group = group.sort_values("frame")

            # Distance totale = somme des distances frame par frame
            total_dist_m = group["distance_m_frame"].sum()

            # Vitesse max (lisser d'abord sur 5 frames pour éviter les artefacts)
            speed_smooth = group["speed_kmh"].rolling(5, center=True, min_periods=1).mean()
            max_speed = speed_smooth.max()

            # Temps de jeu observable (minutes avec données)
            time_obs_min = (group["frame"].nunique() * DT) / 60

            # Zones d'intensité
            zone_metrics = {}
            for zone_name, (low, high) in SPEED_ZONES_M.items():
                mask = (group["speed_kmh"] >= low) & (group["speed_kmh"] < high)
                zone_dist = group.loc[mask, "distance_m_frame"].sum()
                zone_time = mask.sum() * DT / 60  # minutes dans cette zone
                zone_metrics[f"dist_{zone_name}"] = round(zone_dist, 1)
                zone_metrics[f"min_{zone_name}"] = round(zone_time, 2)

            # Sprints : séquences continues au-dessus de 25 km/h (min 1 seconde = 25 frames)
            is_sprint = group["speed_kmh"] >= 25.0
            # Détecter les nouvelles entrées en sprint
            sprint_entries = (is_sprint & ~is_sprint.shift(1, fill_value=False)).sum()

            # HIR : distance à >20 km/h
            hir_mask = group["speed_kmh"] >= 20.0
            hir_dist = group.loc[hir_mask, "distance_m_frame"].sum()

            results.append({
                "player":            player,
                "team_name":         team,
                "total_distance_m":  round(total_dist_m, 0),
                "total_distance_km": round(total_dist_m / 1000, 2),
                "max_speed_kmh":     round(max_speed, 1),
                "sprint_count":      int(sprint_entries),
                "hir_distance_m":    round(hir_dist, 0),
                "time_observed_min": round(time_obs_min, 1),
                **zone_metrics
            })

    if not results:
        return None

    df_out = pd.DataFrame(results)
    df_out["dist_per_90"] = df_out.apply(
        lambda r: round(r["total_distance_km"] / r["time_observed_min"] * 90, 2)
        if r["time_observed_min"] > 0 else 0, axis=1
    )
    df_out["player_name"] = df_out["player"]  # alias pour compatibilité avec viz.py
    df_out["match_label"] = f"Sample Game {game_id}"
    df_out["match_id"] = game_id

    return df_out.sort_values("total_distance_km", ascending=False).reset_index(drop=True)


def compute_metrica_speed_timeline(game_id: int, player: str, team: str) -> pd.DataFrame:
    """
    Retourne le profil de vitesse lissé d'un joueur Metrica.

    On réduit à 1 point toutes les 25 frames (= 1 seconde)
    pour alléger le graphique sans perdre les pics de sprint.
    """
    df = build_player_tracking_df(game_id, team)
    if df is None or df.empty:
        return pd.DataFrame()

    player_df = df[df["player"] == player].copy().sort_values("frame")

    # Lissage sur 5 frames (0.2 seconde) pour éliminer le bruit
    player_df["speed_smooth"] = player_df["speed_kmh"].rolling(5, center=True, min_periods=1).mean()

    # Sous-échantillonnage : 1 point par seconde (25 frames)
    player_df = player_df[player_df["frame"] % 25 == 0].copy()

    return player_df[["minutes", "speed_smooth", "speed_kmh", "period"]].rename(
        columns={"speed_smooth": "speed_avg"}
    )


def get_metrica_positions(game_id: int, player: str, team: str) -> pd.DataFrame:
    """Retourne toutes les positions XY d'un joueur pour la heatmap."""
    df = build_player_tracking_df(game_id, team)
    if df is None or df.empty:
        return pd.DataFrame()

    player_df = df[df["player"] == player][["x", "y", "period"]].dropna()
    # Sous-échantillonner (1 frame sur 5) pour la heatmap
    return player_df.iloc[::5].copy()
