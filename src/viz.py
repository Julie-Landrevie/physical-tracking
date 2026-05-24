"""
src/viz.py
----------
Ce fichier crée tous les graphiques du dashboard.

On utilise :
  - matplotlib / mplsoccer → graphiques sur terrain de foot (heatmaps, trajectoires)
  - plotly → graphiques interactifs (barres, courbes, radar)

Pourquoi deux librairies ?
  - mplsoccer est spécialisé football (il sait dessiner un terrain proprement)
  - plotly permet d'avoir des graphiques interactifs (hover, zoom) dans Streamlit
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from mplsoccer import Pitch, VerticalPitch
import streamlit as st
from src.data_loader import SPEED_ZONES_KMH as SPEED_ZONES, ZONE_COLORS

# ============================================================
# COULEURS ET THÈME DU DASHBOARD
# ============================================================

COLORS = {
    "primary":    "#00FF87",   # vert néon SkillCorner
    "secondary":  "#0A0A0A",   # fond noir
    "accent":     "#FF6B35",   # orange vif
    "neutral":    "#1A1A2E",   # bleu nuit
    "text":       "#E8E8E8",   # gris clair
    "grid":       "#2A2A2A",   # gris très sombre
}

# Thème plotly sombre custom
PLOTLY_THEME = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor":  "rgba(10,10,10,0.8)",
    "font":          {"color": COLORS["text"], "family": "Inter, sans-serif"},
    "xaxis":         {"gridcolor": COLORS["grid"], "linecolor": COLORS["grid"]},
    "yaxis":         {"gridcolor": COLORS["grid"], "linecolor": COLORS["grid"]},
}


# ============================================================
# 1. GRAPHIQUE EN BARRES — DISTANCES PAR JOUEUR
# ============================================================

def plot_distance_bars(metrics_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """
    Barres horizontales : distance totale parcourue par joueur.
    
    C'est le premier graphique qu'on regarde dans une analyse physique :
    qui a le plus couru dans ce match ?
    
    Parameters
    ----------
    metrics_df : DataFrame issu de compute_player_metrics()
    top_n : nombre de joueurs à afficher (les N qui ont le plus couru)
    """
    # Prendre les top_n joueurs par distance totale
    df = metrics_df.head(top_n).copy()
    
    # Créer les labels "Prénom Nom (équipe)"
    df["label"] = df["player_name"] + " (" + df["team_name"] + ")"
    
    # Couleurs différentes par équipe
    teams = df["team_name"].unique()
    team_colors = {team: px.colors.qualitative.Set2[i % 8] for i, team in enumerate(teams)}
    df["color"] = df["team_name"].map(team_colors)
    
    fig = go.Figure()
    
    for team in teams:
        team_df = df[df["team_name"] == team]
        fig.add_trace(go.Bar(
            y=team_df["label"],
            x=team_df["total_distance_km"],
            orientation="h",
            name=team,
            marker_color=team_colors[team],
            text=[f"{d:.2f} km" for d in team_df["total_distance_km"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Distance: %{x:.2f} km<extra></extra>"
        ))
    
    theme = {k: v for k, v in PLOTLY_THEME.items() if k != "yaxis"}
    fig.update_layout(
        title={"text": f"🏃 Distance totale — Top {top_n} joueurs", "font": {"size": 18}},
        xaxis_title="Distance parcourue (km)",
        yaxis={"categoryorder": "total ascending", "gridcolor": COLORS["grid"], "linecolor": COLORS["grid"]},
        barmode="overlay",
        height=max(400, top_n * 35),
        showlegend=True,
        **theme
    )
    
    return fig


# ============================================================
# 2. GRAPHIQUE ZONES D'INTENSITÉ — STACKED BAR
# ============================================================

def plot_intensity_zones(metrics_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """
    Barres empilées (stacked) : répartition des distances par zone d'intensité.
    
    Ce graphique répond à la question : dans quelles zones les joueurs
    ont-ils passé leur temps ? C'est crucial pour comparer les profils
    physiques (joueur explosif vs joueur endurant).
    
    Les zones sont : Jogging / Running / Haute intensité (hsr) / Sprint
    """
    df = metrics_df.head(top_n).copy()
    df["label"] = df["player_name"] + " (" + df["team_name"] + ")"
    
    fig = go.Figure()
    
    # Ajouter une barre par zone (dans l'ordre croissant d'intensité)
    for zone_name in SPEED_ZONES.keys():
        col = f"dist_{zone_name}"
        if col not in df.columns:
            continue
        
        fig.add_trace(go.Bar(
            y=df["label"],
            x=df[col],
            orientation="h",
            name=zone_name,
            marker_color=ZONE_COLORS[zone_name],
            hovertemplate=f"<b>%{{y}}</b><br>{zone_name}: %{{x:.0f}} m<extra></extra>"
        ))
    
    theme = {k: v for k, v in PLOTLY_THEME.items() if k != "yaxis"}
    fig.update_layout(
        title={"text": "⚡ Répartition par zones d'intensité", "font": {"size": 18}},
        xaxis_title="Distance (mètres)",
        yaxis={"categoryorder": "total ascending", "gridcolor": COLORS["grid"], "linecolor": COLORS["grid"]},
        barmode="stack",
        height=max(400, top_n * 35),
        legend={"title": "Zone d'intensité", "orientation": "h", "y": -0.15},
        **theme
    )
    
    return fig


# ============================================================
# 3. COURBE DE VITESSE — ÉVOLUTION SUR LE MATCH
# ============================================================

def plot_speed_timeline(timeline_df: pd.DataFrame, player_name: str) -> go.Figure:
    """
    Courbe de vitesse brute d'un joueur — une valeur par action (pas agrégée).

    Chaque point = une action avec ballon et sa vitesse réelle.
    Les pics au-dessus de 25 km/h = sprints effectifs.
    Le lissage (rolling) est léger pour ne pas écraser les pics.

    Zones colorées :
      - Fond vert  : 1ère mi-temps
      - Fond orange : 2ème mi-temps
      - Points rouges : actions en sprint (speed_avg_band == "sprinting")
    """
    if timeline_df.empty:
        return go.Figure()

    timeline_df = timeline_df.copy()
    # Lissage léger (window=3) pour lisser sans écraser les pics de sprint
    timeline_df["speed_smooth"] = timeline_df["speed_avg"].rolling(window=3, center=True, min_periods=1).mean()

    p1 = timeline_df[timeline_df["period"] == 1]
    p2 = timeline_df[timeline_df["period"] == 2]

    fig = go.Figure()

    # Courbe principale par mi-temps
    for period_df, period_label, color in [
        (p1, "1ère mi-temps", COLORS["primary"]),
        (p2, "2ème mi-temps", COLORS["accent"])
    ]:
        if period_df.empty:
            continue
        fig.add_trace(go.Scatter(
            x=period_df["minutes"],
            y=period_df["speed_smooth"],
            mode="lines",
            name=period_label,
            line={"color": color, "width": 1.5},
            fill="tozeroy",
            opacity=0.7,
        ))

    # Marqueurs rouges sur les actions en sprint
    if "speed_avg_band" in timeline_df.columns:
        sprints = timeline_df[timeline_df["speed_avg_band"] == "sprinting"]
    else:
        sprints = timeline_df[timeline_df["speed_avg"] >= 25]

    if not sprints.empty:
        fig.add_trace(go.Scatter(
            x=sprints["minutes"],
            y=sprints["speed_avg"],
            mode="markers",
            name="Sprint",
            marker={"color": "#FF4444", "size": 10, "symbol": "star",
                    "line": {"width": 1, "color": "white"}},
            hovertemplate="<b>Sprint</b><br>Minute: %{x:.1f}'<br>Vitesse: %{y:.1f} km/h<extra></extra>"
        ))

    # Ligne seuil sprint (25 km/h = seuil réel SkillCorner)
    fig.add_hline(
        y=25,
        line_dash="dot",
        line_color="#FF4444",
        annotation_text="Seuil sprint SkillCorner (25 km/h)",
        annotation_position="top right",
        annotation_font_color="#FF4444"
    )

    theme = {k: v for k, v in PLOTLY_THEME.items() if k not in ("xaxis", "yaxis")}
    fig.update_layout(
        title={"text": f"📈 Profil de vitesse — {player_name}", "font": {"size": 18}},
        xaxis={"title": "Temps de jeu (minutes)", "range": [0, timeline_df["minutes"].max() + 1], "gridcolor": "#2A2A2A"},
        yaxis={"title": "Vitesse (km/h)", "gridcolor": "#2A2A2A"},
        **theme
    )

    return fig


# ============================================================
# 4. SCATTER COMPARAISON — DISTANCE vs VITESSE MAX
# ============================================================

def plot_distance_vs_maxspeed(metrics_df: pd.DataFrame) -> go.Figure:
    """
    Nuage de points : Distance totale vs Vitesse maximum.
    
    Ce graphique permet d'identifier les profils physiques :
    - En haut à droite : joueur très complet (fort volume + explosive)
    - En haut à gauche : joueur rapide mais économe
    - En bas à droite : joueur travailleur mais pas explosif
    
    Chaque point = un joueur. La taille = nombre de sprints.
    """
    df = metrics_df.copy()
    df["label"] = df["player_name"] + "<br>" + df["team_name"]
    
    # Normaliser la taille des points entre 6 et 20
    if df["sprint_count"].max() > 0:
        sizes = 6 + (df["sprint_count"] / df["sprint_count"].max()) * 14
    else:
        sizes = [10] * len(df)
    
    teams = df["team_name"].unique()
    team_colors_list = px.colors.qualitative.Pastel
    team_color_map = {team: team_colors_list[i % len(team_colors_list)] for i, team in enumerate(teams)}
    
    fig = go.Figure()
    
    for team in teams:
        team_df = df[df["team_name"] == team]
        team_sizes = [
            6 + (row["sprint_count"] / df["sprint_count"].max()) * 14 
            if df["sprint_count"].max() > 0 else 10
            for _, row in team_df.iterrows()
        ]
        
        fig.add_trace(go.Scatter(
            x=team_df["total_distance_km"],
            y=team_df["max_speed_kmh"],
            mode="markers+text",
            name=team,
            marker={
                "size": team_sizes,
                "color": team_color_map[team],
                "line": {"width": 1, "color": "white"}
            },
            text=team_df["player_name"].str.split().str[-1],  # juste le nom de famille
            textposition="top center",
            textfont={"size": 9},
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Distance: %{x:.2f} km<br>"
                "Vitesse max: %{y:.1f} km/h<br>"
                "Sprints: %{customdata[1]}<extra></extra>"
            ),
            customdata=list(zip(team_df["player_name"], team_df["sprint_count"]))
        ))
    
    fig.update_layout(
        title={"text": "🔍 Profils physiques : Distance vs Vitesse max", "font": {"size": 18}},
        xaxis_title="Distance totale (km)",
        yaxis_title="Vitesse maximum (km/h)",
        **PLOTLY_THEME
    )
    
    return fig


# ============================================================
# 5. HEATMAP DE PRÉSENCE SUR LE TERRAIN (mplsoccer)
# ============================================================

def plot_position_heatmap(pos_df: pd.DataFrame, player_name: str):
    """
    Heatmap des positions d'un joueur sur le terrain.
    
    Reçoit un DataFrame déjà filtré (issu de get_player_positions())
    avec colonnes x, y (et optionnellement period).
    
    SkillCorner utilise un système de coordonnées :
      - x : -52.5 (but gauche) → +52.5 (but droit)
      - y : -34 (ligne gauche) → +34 (ligne droite)
    """
    player_df = pos_df.dropna(subset=["x", "y"]).copy()
    
    if player_df.empty:
        return None
    
    # Créer un terrain de foot avec mplsoccer
    # pitch_color="black" pour le fond sombre
    pitch = Pitch(
        pitch_type="skillcorner",
        pitch_length=105,
        pitch_width=68,
        pitch_color="#0A1628",
        line_color="#3A7BD5",
        linewidth=1.5,
        goal_type="box"
    )
    
    fig, ax = plt.subplots(figsize=(12, 8), facecolor="#0A0A0A")
    pitch.draw(ax=ax)
    
    # Heatmap KDE (Kernel Density Estimation)
    # = estimation de densité en chaque point du terrain
    pitch.kdeplot(
        player_df["x"], player_df["y"],
        ax=ax,
        cmap="hot",           # palette chaud/froid
        fill=True,
        alpha=0.7,
        levels=50,
        bw_adjust=0.5,        # lissage (plus grand = plus lisse)
        zorder=2
    )
    
    ax.set_title(
        f"🗺️ Carte de chaleur — {player_name}",
        color="white", fontsize=16, fontweight="bold", pad=15
    )
    
    plt.tight_layout()
    return fig


# ============================================================
# 6. RADAR CHART — PROFIL PHYSIQUE COMPLET
# ============================================================

def plot_physical_radar(metrics_df: pd.DataFrame, player_ids: list, player_names: list) -> go.Figure:
    """
    Graphique radar (toile d'araignée) pour comparer 2-3 joueurs sur 5 métriques.
    
    Chaque axe = une métrique physique normalisée entre 0 et 100.
    La normalisation (percentile) permet de comparer des joueurs de profils différents.
    
    Métriques radar :
    - Volume     → distance totale (km)
    - Sprint     → nombre de sprints
    - Intensité  → distance haute intensité
    - Vitesse    → vitesse maximum
    - Endurance  → distance/90min
    """
    if metrics_df.empty or not player_ids:
        return go.Figure()
    
    # Les 5 métriques et leurs labels affichés
    radar_metrics = {
        "total_distance_km": "Volume",
        "sprint_count":      "Sprints",
        "hir_distance_m":    "Haute intensité",
        "max_speed_kmh":     "Vitesse max",
        "dist_per_90":       "Distance/90"
    }
    
    categories = list(radar_metrics.values())
    
    # Normaliser chaque métrique : percentile rank 0-100
    # (un joueur à 80 = meilleur que 80% des joueurs du dataset)
    normalized = metrics_df.copy()
    for col in radar_metrics.keys():
        if col in normalized.columns:
            normalized[f"pct_{col}"] = normalized[col].rank(pct=True) * 100
    
    colors_radar = [COLORS["primary"], COLORS["accent"], "#3A7BD5", "#9B59B6"]

    def hex_to_rgba(hex_color: str, alpha: float = 0.15) -> str:
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    fig = go.Figure()

    for i, (player_id, player_name) in enumerate(zip(player_ids, player_names)):
        row = normalized[normalized["player_id"] == player_id]
        if row.empty:
            continue
        row = row.iloc[0]

        values = [
            row.get(f"pct_{col}", 50)
            for col in radar_metrics.keys()
        ]
        values_closed = values + [values[0]]
        cats_closed = categories + [categories[0]]
        color = colors_radar[i % len(colors_radar)]

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=cats_closed,
            fill="toself",
            name=player_name,
            line={"color": color, "width": 2},
            fillcolor=hex_to_rgba(color, 0.15),
            opacity=0.9,
        ))
    
    fig.update_layout(
        title={"text": "🕸️ Radar physique comparatif", "font": {"size": 18}},
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 100],
                "ticksuffix": "%",
                "gridcolor": COLORS["grid"],
                "linecolor": COLORS["grid"],
            },
            "angularaxis": {"gridcolor": COLORS["grid"]},
            "bgcolor": "rgba(10,10,10,0.5)",
        },
        showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["text"]},
        height=450
    )
    
    return fig


# ============================================================
# 7. ÉVOLUTION SUR PLUSIEURS MATCHS
# ============================================================

def plot_multi_match_evolution(all_metrics: list, metric_col: str, metric_label: str) -> go.Figure:
    """
    Graphique linéaire d'évolution d'une métrique sur plusieurs matchs.
    
    Permet de voir la progression (ou la fatigue) d'un joueur au fil des matchs.
    
    Parameters
    ----------
    all_metrics : liste de DataFrames metrics (un par match)
    metric_col  : colonne à analyser (ex: "total_distance_km")
    metric_label : label affiché (ex: "Distance totale (km)")
    """
    if not all_metrics:
        return go.Figure()
    
    # Fusionner tous les matchs en un seul DataFrame
    combined = pd.concat(all_metrics, ignore_index=True)
    
    if metric_col not in combined.columns:
        return go.Figure()
    
    fig = go.Figure()
    
    # Une ligne par joueur
    for player_name, group in combined.groupby("player_name"):
        if len(group) < 2:  # au moins 2 matchs pour tracer une ligne
            continue
        
        fig.add_trace(go.Scatter(
            x=group["match_label"] if "match_label" in group.columns else group.index,
            y=group[metric_col],
            mode="lines+markers",
            name=player_name,
            line={"width": 2},
            marker={"size": 8},
            hovertemplate=f"<b>%{{x}}</b><br>{metric_label}: %{{y:.2f}}<extra>{player_name}</extra>"
        ))
    
    theme = {k: v for k, v in PLOTLY_THEME.items() if k not in ("xaxis", "yaxis")}
    fig.update_layout(
        title={"text": f"📊 Évolution — {metric_label}", "font": {"size": 18}},
        xaxis={"title": "Match", "tickangle": -30, "gridcolor": "#2A2A2A"},
        yaxis={"title": metric_label, "gridcolor": "#2A2A2A"},
        **theme
    )
    
    return fig
