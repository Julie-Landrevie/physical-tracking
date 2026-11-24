"""
app.py — Physical Intensity & Tracking Analysis (français / anglais, clair / sombre)
Sources : SkillCorner (actions sur balle) + Metrica Sports (tracking complet)
Charte commune : jl_ui.py et .streamlit/config.toml (graphiques : src/viz.py).
"""

import matplotlib
import streamlit as st

matplotlib.use("Agg")

from jl_ui import footer, fr_num, header, kpi, lang, note, setup, t  # noqa: E402

setup("Physical Tracking — Julie Landrevie", "Physical Tracking — Julie Landrevie", icon="⚡")

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402

from src import viz  # noqa: E402
from src.data_loader import compute_player_metrics, compute_speed_timeline, get_matches_dict, get_player_positions  # noqa: E402
from src.metrica_loader import (METRICA_MATCHES, compute_metrica_metrics, compute_metrica_speed_timeline,  # noqa: E402
                                get_metrica_positions)
from src.viz import (ZONE_COLORS, plot_distance_bars, plot_distance_vs_maxspeed, plot_intensity_zones,  # noqa: E402
                     plot_multi_match_evolution, plot_physical_radar, plot_position_heatmap, plot_speed_timeline,
                     zone_label)

viz.set_lang(lang())
SKC, MET = "skillcorner", "metrica"
ALL = "__all__"


def chart(fig):
    st.plotly_chart(fig, width="stretch", theme="streamlit")


METRIC_LABELS = {"total_distance_km": ("Distance (km)", "Distance (km)"), "max_speed_kmh": ("Vitesse max (km/h)", "Top speed (km/h)"),
                 "sprint_count": ("Sprints", "Sprints"), "hir_distance_m": ("Haute intensité (m)", "High-intensity running (m)"),
                 "dist_per_90": ("Distance par 90 min (km)", "Distance per 90 (km)"),
                 "player_name": ("Joueur", "Player"), "team_name": ("Équipe", "Team")}

header(t("Intensité physique et tracking", "Physical intensity and tracking"),
       t("Données ouvertes SkillCorner et Metrica Sports : distances, vitesses, sprints et zones d’intensité, après "
         "trois filtres de cohérence physique.",
         "SkillCorner and Metrica Sports open data: distances, speeds, sprints and intensity zones, after three "
         "physical-consistency filters."))

# ============================================================
# BARRE LATÉRALE
# ============================================================
with st.sidebar:
    st.markdown("### Physical Tracker")
    source = st.radio(t("Source de données", "Data source"), options=[SKC, MET],
                      format_func=lambda s: "SkillCorner" if s == SKC else "Metrica Sports",
                      captions=[t("Actions sur balle · A-League 2024/25", "On-ball actions · A-League 2024/25"),
                                t("Tracking complet · 2 matchs anonymisés", "Full tracking · 2 anonymised matches")])

    if source == SKC:
        with st.spinner(t("Chargement des matchs…", "Loading matches…")):
            matches_dict = get_matches_dict()
        match_options = {mid: f"{i['home']} vs {i['away']} ({i['date']})" for mid, i in matches_dict.items()}
        selected_match_id = st.selectbox(t("Match", "Match"), options=list(match_options), format_func=lambda x: match_options[x])
        info = matches_dict[selected_match_id]
        st.caption(f"{info['competition']} · {info['date']}  \n"
                   + t("Actions avec ballon uniquement : vitesse, zones, sprints, contexte tactique.",
                       "On-ball actions only: speed, zones, sprints, tactical context."))
        current_id = selected_match_id
    else:
        selected_game_id = st.selectbox(t("Match", "Match"), options=list(METRICA_MATCHES),
                                        format_func=lambda x: f"{METRICA_MATCHES[x]['label']} ({METRICA_MATCHES[x]['duration']})")
        st.caption(t("Joueurs anonymisés · tracking XY complet à 25 images/s : vrai kilométrage, carte de chaleur réelle.",
                     "Anonymised players · full XY tracking at 25 fps: true distance, real heat map."))
        current_id = selected_game_id

    with st.expander(t("Pourquoi deux sources ?", "Why two sources?")):
        st.markdown(t("""
| Indicateur | SkillCorner | Metrica |
|---|:---:|:---:|
| Vrai kilométrage | non | oui |
| Vitesse max | oui | oui |
| Zones d’intensité | oui | oui |
| Carte de chaleur complète | partielle | oui |
| Contexte tactique | oui | non |
| Pressing et passes | oui | non |
""", """
| Metric | SkillCorner | Metrica |
|---|:---:|:---:|
| True distance | no | yes |
| Top speed | yes | yes |
| Intensity zones | yes | yes |
| Full heat map | partial | yes |
| Tactical context | yes | no |
| Pressing and passes | yes | no |
"""))

# ============================================================
# CHARGEMENT
# ============================================================
c1, c2, c3 = st.columns([1, 2, 1])
with c2:
    label = t("Charger les données du match", "Load the match data") if source == SKC else \
        t("Charger le tracking complet (environ 2 min)", "Load the full tracking (about 2 min)")
    if st.button(label, width="stretch", type="primary"):
        st.session_state["data_loaded"] = True
        st.session_state["loaded_source"] = source
        st.session_state["loaded_id"] = current_id

data_ready = (st.session_state.get("data_loaded") and st.session_state.get("loaded_source") == source
              and st.session_state.get("loaded_id") == current_id)

if data_ready:
    if source == SKC:
        with st.spinner(t("Chargement des données SkillCorner…", "Loading SkillCorner data…")):
            metrics_df = compute_player_metrics(selected_match_id)
        data_note = t("Indicateurs calculés sur les <b>actions avec ballon uniquement</b> (événements dynamiques SkillCorner).",
                      "Metrics computed on <b>on-ball actions only</b> (SkillCorner dynamic events).")
    else:
        with st.spinner(t("Chargement du tracking complet (deux équipes)… environ 2 min",
                          "Loading full tracking (both teams)… about 2 min")):
            metrics_df = compute_metrica_metrics(selected_game_id)
        data_note = t("Indicateurs calculés sur le <b>tracking complet</b> (positions XY à 25 images/s, Metrica Sports).",
                      "Metrics computed on <b>full tracking</b> (XY positions at 25 fps, Metrica Sports).")
    if metrics_df is None or metrics_df.empty:
        st.error(t("Chargement impossible. Vérifie ta connexion.", "Could not load. Check your connection."))
        st.stop()

    note(data_note)
    k = st.columns(5)
    kpi(k[0], str(metrics_df["player_name"].nunique()), t("Joueurs", "Players"))
    if source == SKC:
        kpi(k[1], f"{fr_num(metrics_df['total_distance_m'].mean(), 0)} m", t("Distance moyenne sur balle", "Average on-ball distance"))
    else:
        kpi(k[1], f"{fr_num(metrics_df['total_distance_km'].mean(), 2)} km", t("Distance moyenne totale", "Average total distance"))
    fastest = metrics_df.loc[metrics_df["max_speed_kmh"].idxmax(), "player_name"]
    kpi(k[2], f"{fr_num(metrics_df['max_speed_kmh'].max(), 1)} km/h", t(f"Vitesse max ({fastest})", f"Top speed ({fastest})"), accent=True)
    kpi(k[3], str(int(metrics_df["sprint_count"].sum())), t("Sprints au total", "Total sprints"))
    kpi(k[4], f"{fr_num(metrics_df['hir_distance_m'].mean(), 0)} m", t("Haute intensité moyenne (> 20 km/h)", "Average high-intensity running (>20 km/h)"))
    st.write("")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([t("Vue match", "Match view"), t("Profil joueur", "Player profile"),
                                            t("Comparaison", "Comparison"), t("Plusieurs matchs", "Several matches"),
                                            t("Deux sources", "Two sources")])

    # --- VUE MATCH ---
    with tab1:
        top_n = st.slider(t("Nombre de joueurs", "Number of players"), 5, len(metrics_df), min(15, len(metrics_df)))
        chart(plot_distance_bars(metrics_df, top_n=top_n))
        chart(plot_intensity_zones(metrics_df, top_n=top_n))
        chart(plot_distance_vs_maxspeed(metrics_df))
        st.markdown(f"**{t('Tableau complet', 'Full table')}**")
        cols = [c for c in ["player_name", "team_name", "total_distance_km", "max_speed_kmh", "sprint_count",
                            "hir_distance_m", "dist_per_90"] if c in metrics_df.columns]
        sel_team = st.selectbox(t("Équipe", "Team"), [ALL] + list(metrics_df["team_name"].unique()),
                                format_func=lambda v: t("Toutes", "All") if v == ALL else v)
        d = metrics_df if sel_team == ALL else metrics_df[metrics_df["team_name"] == sel_team]
        d = d[cols].rename(columns={c: t(*METRIC_LABELS[c]) for c in cols})
        st.dataframe(d, width="stretch", height=400, hide_index=True,
                     column_config={t(*METRIC_LABELS["total_distance_km"]): st.column_config.ProgressColumn(
                         t(*METRIC_LABELS["total_distance_km"]), format="%.2f", min_value=0,
                         max_value=float(metrics_df["total_distance_km"].max() or 1))})

    # --- PROFIL JOUEUR ---
    with tab2:
        player_options = {r["player_name"]: f"{r['player_name']} ({r['team_name']})" for _, r in metrics_df.iterrows()}
        sel_player = st.selectbox(t("Joueur", "Player"), options=list(player_options), format_func=lambda x: player_options[x])
        if sel_player:
            prow = metrics_df[metrics_df["player_name"] == sel_player].iloc[0]
            p = st.columns(5)
            if source == MET:
                kpi(p[0], f"{fr_num(prow['total_distance_km'], 2)} km", t("Distance", "Distance"))
            else:
                kpi(p[0], f"{fr_num(prow['total_distance_m'], 0)} m", t("Distance sur balle", "On-ball distance"))
            kpi(p[1], f"{fr_num(prow['max_speed_kmh'], 1)} km/h", t("Vitesse max", "Top speed"))
            kpi(p[2], str(int(prow["sprint_count"])), "Sprints")
            kpi(p[3], f"{fr_num(prow['hir_distance_m'], 0)} m", t("Haute intensité", "High intensity"))
            kpi(p[4], f"{fr_num(prow.get('dist_per_90', 0), 2)} km", t("Distance par 90 min", "Distance per 90"))
            st.write("")

            if source == SKC:
                pid = prow["player_id"] if "player_id" in prow.index else None
                timeline = compute_speed_timeline(selected_match_id, pid) if pid else pd.DataFrame()
            else:
                timeline = compute_metrica_speed_timeline(selected_game_id, sel_player, prow["team_name"])
            if not timeline.empty:
                chart(plot_speed_timeline(timeline, sel_player))

            if source == SKC:
                pid = prow.get("player_id")
                pos_df = get_player_positions(selected_match_id, pid) if pid else pd.DataFrame()
            else:
                pos_df = get_metrica_positions(selected_game_id, sel_player, prow["team_name"])
            if not pos_df.empty:
                with st.spinner(t("Carte de chaleur…", "Heat map…")):
                    fig_hm = plot_position_heatmap(pos_df, sel_player)
                if fig_hm:
                    st.pyplot(fig_hm, width="stretch")
            else:
                st.warning(t("Pas assez de données de position.", "Not enough position data."))

            zone_names = list(ZONE_COLORS)
            zone_vals = [prow.get(f"dist_{z}", 0) for z in zone_names]
            fig_z = go.Figure(go.Bar(x=[zone_label(z) for z in zone_names], y=zone_vals,
                                     marker_color=[ZONE_COLORS[z] for z in zone_names],
                                     text=[f"{fr_num(v, 0)} m" for v in zone_vals], textposition="outside"))
            fig_z.update_layout(title=t(f"Zones d’intensité : {sel_player}", f"Intensity zones: {sel_player}"),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                font={"family": viz.FONT}, height=340, yaxis_title=t("Distance (m)", "Distance (m)"))
            chart(fig_z)

    # --- COMPARAISON ---
    with tab3:
        st.caption(t("Choisis 2 à 4 joueurs pour le radar physique.", "Pick 2 to 4 players for the physical radar."))
        names = metrics_df["player_name"].tolist()
        teams_of = dict(zip(metrics_df["player_name"], metrics_df["team_name"]))
        sel_radar = st.multiselect(t("Joueurs", "Players"), options=names, format_func=lambda x: f"{x} ({teams_of[x]})",
                                   max_selections=4, default=names[:2] if len(names) >= 2 else [])
        if len(sel_radar) >= 2:
            temp_df = metrics_df.copy()
            if "player_id" not in temp_df.columns:
                temp_df["player_id"] = temp_df["player_name"]
            ids = [temp_df[temp_df["player_name"] == p]["player_id"].iloc[0] for p in sel_radar]
            chart(plot_physical_radar(temp_df, ids, sel_radar))
            cols = [c for c in ["player_name", "team_name", "total_distance_km", "max_speed_kmh", "sprint_count",
                                "hir_distance_m", "dist_per_90"] if c in metrics_df.columns]
            cdf = metrics_df[metrics_df["player_name"].isin(sel_radar)][cols]
            st.dataframe(cdf.rename(columns={c: t(*METRIC_LABELS[c]) for c in cols}), width="stretch", hide_index=True)

    # --- PLUSIEURS MATCHS ---
    with tab4:
        if source == SKC:
            others = {mid: f"{i['home']} vs {i['away']} ({i['date']})" for mid, i in matches_dict.items() if mid != selected_match_id}
            extra = st.multiselect(t("Ajouter des matchs SkillCorner", "Add SkillCorner matches"), list(others),
                                   format_func=lambda x: others[x], max_selections=4)
            loader, metric_keys = compute_player_metrics, ["total_distance_km", "max_speed_kmh", "sprint_count", "hir_distance_m"]
        else:
            others = {gid: f"{g['label']} ({g['duration']})" for gid, g in METRICA_MATCHES.items() if gid != selected_game_id}
            extra = st.multiselect(t("Ajouter un match Metrica", "Add a Metrica match"), list(others),
                                   format_func=lambda x: others[x], max_selections=1)
            loader, metric_keys = compute_metrica_metrics, ["total_distance_km", "max_speed_kmh", "sprint_count"]
        if extra:
            all_m = [metrics_df.copy()]
            with st.spinner(t("Chargement…", "Loading…")):
                for mid in extra:
                    em = loader(mid)
                    if em is not None:
                        all_m.append(em)
            if len(all_m) >= 2:
                mc = st.selectbox(t("Indicateur", "Metric"), metric_keys, format_func=lambda x: t(*METRIC_LABELS[x]))
                chart(plot_multi_match_evolution(all_m, mc, t(*METRIC_LABELS[mc])))

    # --- DEUX SOURCES ---
    with tab5:
        col_skc, col_met = st.columns(2)
        with col_skc:
            st.markdown(t("""#### SkillCorner
**Tracking issu des images TV** à 10 images/s, limité aux **actions avec ballon**.

**Points forts**
- contexte tactique (possession, passes, pressing)
- vitesse précise sur chaque action
- 10 matchs d’A-League 2024/25 en données ouvertes

**Limites**
- pas de kilométrage total
- carte de chaleur partielle (actions seulement)
- pas de déplacements sans ballon""", """#### SkillCorner
**Broadcast tracking** from TV images at 10 fps, limited to **on-ball actions**.

**Strengths**
- tactical context (possession, passes, pressing)
- precise speed on every action
- 10 A-League 2024/25 matches in open data

**Limits**
- no total distance
- partial heat map (actions only)
- no off-ball movement"""))
        with col_met:
            st.markdown(t("""#### Metrica Sports
**Tracking optique complet** à 25 images/s : la position de **tous les joueurs à chaque image**.

**Points forts**
- vrai kilométrage (8 à 11 km par match)
- carte de chaleur de tout le match
- déplacements sans ballon visibles

**Limites**
- joueurs anonymisés (Player1…)
- seulement 2 matchs disponibles
- pas de contexte tactique ni d’événements""", """#### Metrica Sports
**Full optical tracking** at 25 fps: the position of **every player in every frame**.

**Strengths**
- true distance (8 to 11 km per match)
- heat map of the whole match
- off-ball movement visible

**Limits**
- anonymised players (Player1…)
- only 2 matches available
- no tactical context or events"""))
        note(t("En club, on croise le <b>tracking complet</b> (GPS ou optique) pour la charge physique et les <b>données "
               "d’événements</b> pour le contexte. Cette application reproduit cette logique avec des données ouvertes : "
               "Metrica pour la charge réelle, SkillCorner pour le contexte des actions avec ballon.",
               "In a club, analysts combine <b>full tracking</b> (GPS or optical) for physical load with <b>event data</b> "
               "for context. This app mirrors that with open data: Metrica for true load, SkillCorner for the context of "
               "on-ball actions."))
else:
    note(t("Choisis une source et un match dans la barre latérale, puis clique sur « Charger les données du match ».<br>"
           "<b>SkillCorner</b> : 10 matchs d’A-League 2024/25, actions sur balle. "
           "<b>Metrica Sports</b> : 2 matchs anonymisés, tracking complet.",
           "Pick a source and a match in the sidebar, then click “Load the match data”.<br>"
           "<b>SkillCorner</b>: 10 A-League 2024/25 matches, on-ball actions. "
           "<b>Metrica Sports</b>: 2 anonymised matches, full tracking."))

footer("Données : SkillCorner Open Data · Metrica Sports Open Data", "Data: SkillCorner Open Data · Metrica Sports Open Data")
