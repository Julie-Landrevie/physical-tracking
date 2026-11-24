"""
src/viz.py
----------
Ce fichier crée tous les graphiques du dashboard, dans la charte de Julie Landrevie
(même charte que le site et les visuels LinkedIn).

On utilise :
  - matplotlib / mplsoccer → graphiques sur terrain de foot (heatmaps)
  - plotly → graphiques interactifs (barres, courbes, radar)

Couleurs : vert d'eau (#0d8f84) pour les données, rouille (#cc4a12) pour la seule mise en avant
(sprint, 2e équipe), gris (#c9c0b1) pour la comparaison. Les graphiques plotly ont un fond
transparent : affichés avec theme="streamlit", ils suivent le thème clair ou sombre.
Les libellés sont en français ou en anglais : set_lang("en").
"""

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from matplotlib.colors import LinearSegmentedColormap
from mplsoccer import Pitch

from src.data_loader import SPEED_ZONES_KMH as SPEED_ZONES

# ============================================================
# COULEURS, LANGUE
# ============================================================

COLORS = {
    "primary":   "#0d8f84",   # vert d'eau
    "accent":    "#cc4a12",   # rouille (une seule mise en avant)
    "compare":   "#c9c0b1",   # gris de comparaison
    "ink2":      "#57534e",
    "bg":        "#f6f1e7",   # fond crème des figures matplotlib
    "grid":      "rgba(138,133,128,0.25)",
}
TEAM_COLORS = [COLORS["primary"], COLORS["accent"], COLORS["compare"], COLORS["ink2"]]
# Zones d'intensité : du plus clair au plus foncé, sprint en rouille
ZONE_COLORS = {"Jogging": "#c6e4df", "Running": "#77c1b8", "Haute intensité": "#0d8f84", "Sprint": "#cc4a12"}
ZONE_EN = {"Jogging": "Jogging", "Running": "Running", "Haute intensité": "High intensity", "Sprint": "Sprint"}
FONT = "Lato, 'Helvetica Neue', Arial, sans-serif"

LANG = "fr"


def set_lang(lang: str) -> None:
    global LANG
    LANG = "en" if str(lang).lower().startswith("en") else "fr"


def _t(fr: str, en: str) -> str:
    return en if LANG == "en" else fr


def zone_label(z: str) -> str:
    return _t(z, ZONE_EN.get(z, z))


def _sep():
    return "," if LANG == "fr" else "."


def _layout(fig: go.Figure, title: str, height: int = None, **kw) -> go.Figure:
    """Mise en forme commune : police, fond transparent (le thème Streamlit fait le reste)."""
    fig.update_layout(title={"text": title, "font": {"size": 17}}, font={"family": FONT},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      separators=_sep() + " ", margin=dict(l=10, r=10, t=50, b=10), **kw)
    fig.update_xaxes(gridcolor=COLORS["grid"], zeroline=False)
    fig.update_yaxes(gridcolor=COLORS["grid"], zeroline=False)
    if height:
        fig.update_layout(height=height)
    return fig


def _num(x: float, dec: int = 2) -> str:
    s = f"{x:,.{dec}f}"
    return s if LANG == "en" else s.replace(",", " ").replace(".", ",")


# ============================================================
# 1. BARRES — DISTANCES PAR JOUEUR
# ============================================================

def plot_distance_bars(metrics_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Barres horizontales : distance totale parcourue par joueur (couleur = équipe)."""
    df = metrics_df.head(top_n).copy()
    df["label"] = df["player_name"] + " (" + df["team_name"] + ")"
    teams = list(df["team_name"].unique())
    fig = go.Figure()
    for i, team in enumerate(teams):
        team_df = df[df["team_name"] == team]
        fig.add_trace(go.Bar(
            y=team_df["label"], x=team_df["total_distance_km"], orientation="h", name=team,
            marker_color=TEAM_COLORS[i % len(TEAM_COLORS)],
            text=[f"{_num(d)} km" for d in team_df["total_distance_km"]], textposition="outside",
            hovertemplate="<b>%{y}</b><br>Distance : %{x:.2f} km<extra></extra>"))
    _layout(fig, _t(f"Distance totale : top {top_n}", f"Total distance: top {top_n}"), height=max(400, top_n * 35),
            xaxis_title=_t("Distance parcourue (km)", "Distance covered (km)"), barmode="overlay",
            legend={"orientation": "h", "y": -0.12})
    fig.update_yaxes(categoryorder="total ascending")
    fig.update_xaxes(range=[0, float(df["total_distance_km"].max() or 1) * 1.15])
    return fig


# ============================================================
# 2. ZONES D'INTENSITÉ — BARRES EMPILÉES
# ============================================================

def plot_intensity_zones(metrics_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Barres empilées : répartition des distances par zone d'intensité."""
    df = metrics_df.head(top_n).copy()
    df["label"] = df["player_name"] + " (" + df["team_name"] + ")"
    fig = go.Figure()
    for zone_name in SPEED_ZONES.keys():
        col = f"dist_{zone_name}"
        if col not in df.columns:
            continue
        fig.add_trace(go.Bar(
            y=df["label"], x=df[col], orientation="h", name=zone_label(zone_name),
            marker_color=ZONE_COLORS.get(zone_name, COLORS["compare"]),
            hovertemplate=f"<b>%{{y}}</b><br>{zone_label(zone_name)}{_t(' :', ':')} %{{x:.0f}} m<extra></extra>"))
    _layout(fig, _t("Répartition par zone d’intensité", "Split by intensity zone"), height=max(400, top_n * 35),
            xaxis_title=_t("Distance (mètres)", "Distance (metres)"), barmode="stack",
            legend={"title": "", "orientation": "h", "y": -0.12})
    fig.update_yaxes(categoryorder="total ascending")
    return fig


# ============================================================
# 3. COURBE DE VITESSE
# ============================================================

def plot_speed_timeline(timeline_df: pd.DataFrame, player_name: str) -> go.Figure:
    """Vitesse d'un joueur au fil du match ; étoiles rouille = actions en sprint (≥ 25 km/h)."""
    if timeline_df.empty:
        return go.Figure()
    timeline_df = timeline_df.copy()
    timeline_df["speed_smooth"] = timeline_df["speed_avg"].rolling(window=3, center=True, min_periods=1).mean()
    fig = go.Figure()
    for period, label, color in [(1, _t("1re mi-temps", "1st half"), COLORS["primary"]),
                                 (2, _t("2e mi-temps", "2nd half"), COLORS["compare"])]:
        pdf = timeline_df[timeline_df["period"] == period]
        if pdf.empty:
            continue
        fig.add_trace(go.Scatter(x=pdf["minutes"], y=pdf["speed_smooth"], mode="lines", name=label,
                                 line={"color": color, "width": 1.8}, fill="tozeroy", opacity=0.75))
    if "speed_avg_band" in timeline_df.columns:
        sprints = timeline_df[timeline_df["speed_avg_band"] == "sprinting"]
    else:
        sprints = timeline_df[timeline_df["speed_avg"] >= 25]
    if not sprints.empty:
        fig.add_trace(go.Scatter(
            x=sprints["minutes"], y=sprints["speed_avg"], mode="markers", name="Sprint",
            marker={"color": COLORS["accent"], "size": 11, "symbol": "star", "line": {"width": 1, "color": COLORS["bg"]}},
            hovertemplate=_t("<b>Sprint</b><br>Minute : %{x:.1f}'<br>Vitesse : %{y:.1f} km/h<extra></extra>",
                             "<b>Sprint</b><br>Minute: %{x:.1f}'<br>Speed: %{y:.1f} km/h<extra></extra>")))
    fig.add_hline(y=25, line_dash="dot", line_color=COLORS["accent"],
                  annotation_text=_t("Seuil de sprint SkillCorner (25 km/h)", "SkillCorner sprint threshold (25 km/h)"),
                  annotation_position="top right")
    _layout(fig, _t(f"Profil de vitesse : {player_name}", f"Speed profile: {player_name}"),
            xaxis={"title": _t("Temps de jeu (minutes)", "Playing time (minutes)"),
                   "range": [0, timeline_df["minutes"].max() + 1]},
            yaxis={"title": _t("Vitesse (km/h)", "Speed (km/h)")})
    return fig


# ============================================================
# 4. NUAGE — DISTANCE vs VITESSE MAX
# ============================================================

def plot_distance_vs_maxspeed(metrics_df: pd.DataFrame) -> go.Figure:
    """Distance totale et vitesse maximum ; taille du point = nombre de sprints."""
    df = metrics_df.copy()
    smax = df["sprint_count"].max()
    fig = go.Figure()
    for i, team in enumerate(df["team_name"].unique()):
        team_df = df[df["team_name"] == team]
        sizes = [6 + (s / smax) * 14 if smax > 0 else 10 for s in team_df["sprint_count"]]
        fig.add_trace(go.Scatter(
            x=team_df["total_distance_km"], y=team_df["max_speed_kmh"], mode="markers+text", name=team,
            marker={"size": sizes, "color": TEAM_COLORS[i % len(TEAM_COLORS)], "line": {"width": 1, "color": COLORS["bg"]}},
            text=team_df["player_name"].str.split().str[-1], textposition="top center", textfont={"size": 9},
            hovertemplate=_t("<b>%{customdata[0]}</b><br>Distance : %{x:.2f} km<br>Vitesse max : %{y:.1f} km/h<br>"
                             "Sprints : %{customdata[1]}<extra></extra>",
                             "<b>%{customdata[0]}</b><br>Distance: %{x:.2f} km<br>Top speed: %{y:.1f} km/h<br>"
                             "Sprints: %{customdata[1]}<extra></extra>"),
            customdata=list(zip(team_df["player_name"], team_df["sprint_count"]))))
    return _layout(fig, _t("Profils physiques : distance et vitesse maximum", "Physical profiles: distance and top speed"),
                   xaxis_title=_t("Distance totale (km)", "Total distance (km)"),
                   yaxis_title=_t("Vitesse maximum (km/h)", "Top speed (km/h)"),
                   legend={"orientation": "h", "y": -0.15})


# ============================================================
# 5. CARTE DE CHALEUR (mplsoccer) — fond crème dans les deux thèmes
# ============================================================

def plot_position_heatmap(pos_df: pd.DataFrame, player_name: str):
    """Carte de chaleur des positions d'un joueur (coordonnées SkillCorner : x ±52,5 m, y ±34 m)."""
    player_df = pos_df.dropna(subset=["x", "y"]).copy()
    if player_df.empty:
        return None
    pitch = Pitch(pitch_type="skillcorner", pitch_length=105, pitch_width=68, pitch_color=COLORS["bg"],
                  line_color=COLORS["compare"], linewidth=1.5, goal_type="box", line_zorder=3)
    fig, ax = plt.subplots(figsize=(12, 8), facecolor=COLORS["bg"])
    pitch.draw(ax=ax)
    cmap = LinearSegmentedColormap.from_list("jl_teal", [COLORS["bg"], "#9fd3cc", COLORS["primary"], "#08645c"])
    pitch.kdeplot(player_df["x"], player_df["y"], ax=ax, cmap=cmap, fill=True, alpha=0.85, levels=50,
                  bw_adjust=0.5, zorder=2)
    ax.set_title(_t(f"Carte de chaleur : {player_name}", f"Heat map: {player_name}"),
                 color="#1c1917", fontsize=16, pad=15)
    plt.tight_layout()
    return fig


# ============================================================
# 6. RADAR — PROFIL PHYSIQUE
# ============================================================

def plot_physical_radar(metrics_df: pd.DataFrame, player_ids: list, player_names: list) -> go.Figure:
    """Radar sur 5 métriques normalisées en rang centile (0-100) au sein du match."""
    if metrics_df.empty or not player_ids:
        return go.Figure()
    radar_metrics = {"total_distance_km": _t("Volume", "Volume"), "sprint_count": "Sprints",
                     "hir_distance_m": _t("Haute intensité", "High intensity"),
                     "max_speed_kmh": _t("Vitesse max", "Top speed"), "dist_per_90": _t("Distance/90", "Distance/90")}
    categories = list(radar_metrics.values())
    normalized = metrics_df.copy()
    for col in radar_metrics:
        if col in normalized.columns:
            normalized[f"pct_{col}"] = normalized[col].rank(pct=True) * 100
    fig = go.Figure()
    for i, (player_id, player_name) in enumerate(zip(player_ids, player_names)):
        row = normalized[normalized["player_id"] == player_id]
        if row.empty:
            continue
        row = row.iloc[0]
        values = [row.get(f"pct_{col}", 50) for col in radar_metrics]
        color = TEAM_COLORS[i % len(TEAM_COLORS)]
        fig.add_trace(go.Scatterpolar(r=values + [values[0]], theta=categories + [categories[0]], fill="toself",
                                      name=player_name, line={"color": color, "width": 2.2}, opacity=0.85))
    _layout(fig, _t("Radar physique comparé (rang centile dans le match)", "Physical radar (percentile rank in the match)"),
            height=450, polar={"radialaxis": {"visible": True, "range": [0, 100]}, "bgcolor": "rgba(0,0,0,0)"},
            showlegend=True)
    return fig


# ============================================================
# 7. ÉVOLUTION SUR PLUSIEURS MATCHS
# ============================================================

def plot_multi_match_evolution(all_metrics: list, metric_col: str, metric_label: str) -> go.Figure:
    """Une ligne par joueur présent dans au moins deux matchs."""
    if not all_metrics:
        return go.Figure()
    combined = pd.concat(all_metrics, ignore_index=True)
    if metric_col not in combined.columns:
        return go.Figure()
    fig = go.Figure()
    for player_name, group in combined.groupby("player_name"):
        if len(group) < 2:
            continue
        fig.add_trace(go.Scatter(
            x=group["match_label"] if "match_label" in group.columns else group.index, y=group[metric_col],
            mode="lines+markers", name=player_name, line={"width": 2}, marker={"size": 8},
            hovertemplate=f"<b>%{{x}}</b><br>{metric_label}{_t(' :', ':')} %{{y:.2f}}<extra>{player_name}</extra>"))
    return _layout(fig, _t(f"Évolution : {metric_label}", f"Trend: {metric_label}"),
                   xaxis={"title": _t("Match", "Match"), "tickangle": -30}, yaxis={"title": metric_label},
                   colorway=TEAM_COLORS + ["#8a8580", "#9fd3cc", "#e7a481"])
