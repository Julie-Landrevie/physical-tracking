"""
app.py — Physical Intensity & Tracking Analysis
Sources duales : SkillCorner (actions sur balle) + Metrica (tracking complet)
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")

from src.data_loader import (
    get_matches_dict, load_match_metadata,
    compute_player_metrics, compute_speed_timeline,
    get_player_positions, get_match_label,
    ZONE_COLORS, SPEED_ZONES_SKC,
)
from src.metrica_loader import (
    METRICA_MATCHES, compute_metrica_metrics,
    compute_metrica_speed_timeline, get_metrica_positions,
    ZONE_COLORS as ZONE_COLORS_M,
)
from src.viz import (
    plot_distance_bars, plot_intensity_zones, plot_speed_timeline,
    plot_distance_vs_maxspeed, plot_position_heatmap,
    plot_physical_radar, plot_multi_match_evolution, COLORS,
)

# ============================================================
# CONFIG PAGE
# ============================================================
st.set_page_config(
    page_title="Physical Tracking Analysis",
    page_icon="⚡", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp { background-color: #0A0A0A; color: #E8E8E8; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1628 0%, #0A0A0A 100%);
    border-right: 1px solid #1A1A2E;
}
[data-testid="metric-container"] {
    background: #111; border: 1px solid #00FF87;
    border-radius: 8px; padding: 12px;
}
.stButton > button {
    background: linear-gradient(135deg, #00FF87, #00CC6A);
    color: #0A0A0A; font-weight: bold; border: none; border-radius: 6px;
}
.stTabs [data-baseweb="tab"] {
    background: #111; color: #888; border-radius: 8px 8px 0 0; padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: #1A1A2E; color: #00FF87 !important;
    border-bottom: 2px solid #00FF87;
}
.source-card {
    background: #111; border-radius: 10px; padding: 16px; margin: 6px 0;
}
.source-active { border: 2px solid #00FF87; }
.source-inactive { border: 1px solid #333; opacity: 0.6; }
h1, h2, h3 { color: #E8E8E8; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# HEADER
# ============================================================
st.markdown("""
<div style="text-align:center; padding:20px 0 10px 0;">
    <h1 style="font-size:2.3rem; color:#00FF87; letter-spacing:2px; margin:0;">
        ⚡ Physical Intensity & Tracking Analysis
    </h1>
    <p style="color:#888; font-size:0.95rem; margin:5px 0 0 0;">
        SkillCorner Open Data &nbsp;·&nbsp; Metrica Sports Open Data
    </p>
</div>
<hr style="border-color:#1A1A2E; margin:10px 0 20px 0;">
""", unsafe_allow_html=True)

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; margin-bottom:16px;">
        <span style="font-size:1.8rem;">⚽</span><br>
        <span style="color:#00FF87; font-weight:bold;">Physical Tracker</span>
    </div>
    """, unsafe_allow_html=True)

    # --- SÉLECTION DE LA SOURCE ---
    st.markdown("### 📡 Source de données")

    source = st.radio(
        "Choisir la source",
        options=["SkillCorner", "Metrica Sports"],
        captions=[
            "Actions sur balle · A-League 2024/25",
            "Tracking complet · 2 matchs anonymisés"
        ],
        index=0
    )

    st.markdown("---")

    if source == "SkillCorner":
        # Charger liste des matchs
        with st.spinner("Chargement des matchs..."):
            matches_dict = get_matches_dict()

        match_options = {
            mid: f"{info['home']} vs {info['away']} ({info['date']})"
            for mid, info in matches_dict.items()
        }
        selected_match_id = st.selectbox(
            "Match", options=list(match_options.keys()),
            format_func=lambda x: match_options[x]
        )
        info = matches_dict[selected_match_id]
        st.markdown(f"""
        <div class="source-card source-active">
            <div style="color:#00FF87; font-weight:bold; font-size:0.95rem;">
                {info['home']} vs {info['away']}
            </div>
            <div style="color:#888; font-size:0.8rem;">🏆 {info['competition']}</div>
            <div style="color:#888; font-size:0.8rem;">📅 {info['date']}</div>
            <div style="color:#555; font-size:0.75rem; margin-top:8px;">
                ⚽ Actions sur balle uniquement<br>
                Vitesse · Zones · Sprints · Contexte tactique
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:  # Metrica
        selected_game_id = st.selectbox(
            "Match", options=list(METRICA_MATCHES.keys()),
            format_func=lambda x: f"{METRICA_MATCHES[x]['label']} ({METRICA_MATCHES[x]['duration']})"
        )
        ginfo = METRICA_MATCHES[selected_game_id]
        st.markdown(f"""
        <div class="source-card source-active">
            <div style="color:#3A7BD5; font-weight:bold; font-size:0.95rem;">
                {ginfo['label']}
            </div>
            <div style="color:#888; font-size:0.8rem;">👤 Joueurs anonymisés</div>
            <div style="color:#888; font-size:0.8rem;">⏱️ {ginfo['duration']}</div>
            <div style="color:#555; font-size:0.75rem; margin-top:8px;">
                📍 Tracking XY complet à 25 fps<br>
                Vrai kilométrage · Heatmap réelle · Pressing
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- COMPARAISON SOURCE ---
    with st.expander("ℹ️ Pourquoi deux sources ?"):
        st.markdown("""
        **SkillCorner** et **Metrica** sont complémentaires :

        | Métrique | SKC | Metrica |
        |---|:---:|:---:|
        | Vrai kilométrage | ❌ | ✅ |
        | Vitesse max | ✅ | ✅ |
        | Zones d'intensité | ✅ | ✅ |
        | Heatmap complète | ⚠️ | ✅ |
        | Contexte tactique | ✅ | ❌ |
        | Pressing / passes | ✅ | ❌ |
        """)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#444; text-align:center;">
        <b style="color:#666;">Julie Landrevie</b><br>
        Football Data & Video Analyst
    </div>
    """, unsafe_allow_html=True)

# ============================================================
# BOUTON DE CHARGEMENT
# ============================================================
load_col1, load_col2, load_col3 = st.columns([1, 2, 1])
with load_col2:
    btn_label = "🚀 Charger les données du match"
    if source == "Metrica":
        btn_label = "🚀 Charger le tracking complet (~2 min)"
    if st.button(btn_label, use_container_width=True):
        st.session_state["data_loaded"] = True
        st.session_state["loaded_source"] = source
        st.session_state["loaded_id"] = selected_match_id if source == "SkillCorner" else selected_game_id

if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False

current_id = selected_match_id if source == "SkillCorner" else selected_game_id
data_ready = (
    st.session_state.get("data_loaded") and
    st.session_state.get("loaded_source") == source and
    st.session_state.get("loaded_id") == current_id
)

# ============================================================
# CHARGEMENT & AFFICHAGE
# ============================================================
if data_ready:

    # --- CHARGEMENT SELON LA SOURCE ---
    if source == "SkillCorner":
        with st.spinner("⏳ Chargement des données SkillCorner..."):
            metrics_df = compute_player_metrics(selected_match_id)
        
        if metrics_df is None or metrics_df.empty:
            st.error("❌ Impossible de charger. Vérifie ta connexion.")
            st.stop()

        zone_colors = ZONE_COLORS
        data_note = "⚽ Métriques sur **actions avec ballon uniquement** (SkillCorner dynamic events)"

    else:  # Metrica
        with st.spinner("⏳ Chargement du tracking complet (Home + Away)... ~2 min"):
            metrics_df = compute_metrica_metrics(selected_game_id)

        if metrics_df is None or metrics_df.empty:
            st.error("❌ Impossible de charger. Vérifie ta connexion.")
            st.stop()

        zone_colors = ZONE_COLORS_M
        data_note = "📍 Métriques sur **tracking complet** (positions XY à 25 fps · Metrica Sports)"

    # --- BADGE SOURCE ---
    if source == "SkillCorner":
        badge = '<span style="background:#00FF87;color:#000;padding:3px 10px;border-radius:12px;font-size:0.8rem;font-weight:bold;">⚽ SkillCorner</span>'
    else:
        badge = '<span style="background:#3A7BD5;color:#fff;padding:3px 10px;border-radius:12px;font-size:0.8rem;font-weight:bold;">📍 Metrica Sports</span>'

    st.markdown(f"### 📊 Vue d'ensemble &nbsp; {badge}", unsafe_allow_html=True)
    st.caption(data_note)

    # --- KPIs ---
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    with kpi1:
        st.metric("👥 Joueurs", metrics_df["player_name"].nunique())
    with kpi2:
        if source == "SkillCorner":
            st.metric("🏃 Distance moy. (sur balle)",
                      f"{metrics_df['total_distance_m'].mean():.0f} m")
        else:
            st.metric("🏃 Distance moy. (totale)",
                      f"{metrics_df['total_distance_km'].mean():.2f} km")
    with kpi3:
        max_speed = metrics_df["max_speed_kmh"].max()
        fastest = metrics_df.loc[metrics_df["max_speed_kmh"].idxmax(), "player_name"]
        st.metric("⚡ Vitesse max", f"{max_speed:.1f} km/h", help=f"Par {fastest}")
    with kpi4:
        st.metric("🚀 Total sprints", int(metrics_df["sprint_count"].sum()))
    with kpi5:
        st.metric("🔥 HIR moy.", f"{metrics_df['hir_distance_m'].mean():.0f} m",
                  help="High Intensity Running (>20 km/h)")

    st.markdown("---")

    # ============================================================
    # ONGLETS
    # ============================================================
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏟️ Vue match", "👤 Profil joueur",
        "⚔️ Comparaison", "📈 Multi-matchs", "🔄 Sources combinées"
    ])

    # --- ONGLET 1 : VUE MATCH ---
    with tab1:
        col_l, col_r = st.columns([3, 1])
        with col_r:
            top_n = st.slider("Nb joueurs", 5, len(metrics_df), 15)

        st.markdown("#### 🏃 Distances parcourues")
        st.plotly_chart(plot_distance_bars(metrics_df, top_n=top_n), use_container_width=True)

        st.markdown("#### ⚡ Zones d'intensité")
        st.plotly_chart(plot_intensity_zones(metrics_df, top_n=top_n), use_container_width=True)

        st.markdown("#### 🔍 Profils physiques")
        st.plotly_chart(plot_distance_vs_maxspeed(metrics_df), use_container_width=True)

        st.markdown("#### 📋 Tableau complet")
        display_cols = ["player_name", "team_name", "total_distance_km",
                        "max_speed_kmh", "sprint_count", "hir_distance_m", "dist_per_90"]
        avail = [c for c in display_cols if c in metrics_df.columns]
        rename = {
            "player_name": "Joueur", "team_name": "Équipe",
            "total_distance_km": "Dist. (km)", "max_speed_kmh": "V.max (km/h)",
            "sprint_count": "Sprints", "hir_distance_m": "HIR (m)", "dist_per_90": "Dist/90"
        }
        display_df = metrics_df[avail].rename(columns=rename)
        teams_f = ["Toutes"] + list(metrics_df["team_name"].unique())
        sel_team = st.selectbox("Filtrer par équipe", teams_f)
        if sel_team != "Toutes":
            display_df = display_df[display_df["Équipe"] == sel_team]
        st.dataframe(
            display_df.style.background_gradient(subset=["Dist. (km)"], cmap="YlOrRd"),
            use_container_width=True, height=400
        )

    # --- ONGLET 2 : PROFIL JOUEUR ---
    with tab2:
        st.markdown("#### 👤 Profil physique d'un joueur")

        player_options = {
            row["player_name"]: f"{row['player_name']} ({row['team_name']})"
            for _, row in metrics_df.iterrows()
        }
        sel_player = st.selectbox("Choisir un joueur",
                                  options=list(player_options.keys()),
                                  format_func=lambda x: player_options[x])

        if sel_player:
            prow = metrics_df[metrics_df["player_name"] == sel_player].iloc[0]

            p1, p2, p3, p4, p5 = st.columns(5)
            dist_label = "Dist. (km)" if source == "Metrica" else "Dist. sur balle"
            dist_val = f"{prow['total_distance_km']:.2f} km" if source == "Metrica" else f"{prow['total_distance_m']:.0f} m"
            with p1: st.metric(dist_label, dist_val)
            with p2: st.metric("V.max", f"{prow['max_speed_kmh']:.1f} km/h")
            with p3: st.metric("Sprints", int(prow['sprint_count']))
            with p4: st.metric("HIR", f"{prow['hir_distance_m']:.0f} m")
            with p5: st.metric("Dist/90", f"{prow.get('dist_per_90', 0):.2f} km")

            # Timeline vitesse
            if source == "SkillCorner":
                pid = prow["player_id"] if "player_id" in prow.index else None
                if pid:
                    timeline = compute_speed_timeline(selected_match_id, pid)
                    if not timeline.empty:
                        st.plotly_chart(plot_speed_timeline(timeline, sel_player),
                                        use_container_width=True)
            else:
                team = prow["team_name"]
                timeline = compute_metrica_speed_timeline(selected_game_id, sel_player, team)
                if not timeline.empty:
                    st.plotly_chart(plot_speed_timeline(timeline, sel_player),
                                    use_container_width=True)

            # Heatmap
            st.markdown("##### 🌡️ Carte de chaleur")
            if source == "SkillCorner":
                pid = prow.get("player_id")
                pos_df = get_player_positions(selected_match_id, pid) if pid else pd.DataFrame()
            else:
                pos_df = get_metrica_positions(selected_game_id, sel_player, prow["team_name"])

            if not pos_df.empty:
                with st.spinner("Génération heatmap..."):
                    fig_hm = plot_position_heatmap(pos_df, sel_player)
                if fig_hm:
                    st.pyplot(fig_hm, use_container_width=True)
            else:
                st.warning("Pas assez de données de position.")

            # Zones d'intensité
            import plotly.graph_objects as go
            st.markdown("##### ⚡ Zones d'intensité")
            zone_names = list(zone_colors.keys())
            zone_vals = [prow.get(f"dist_{z}", 0) for z in zone_names]
            fig_z = go.Figure(go.Bar(
                x=zone_names, y=zone_vals,
                marker_color=[zone_colors[z] for z in zone_names],
                text=[f"{v:.0f}m" for v in zone_vals], textposition="outside"
            ))
            fig_z.update_layout(
                title=f"Zones — {sel_player}",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,10,10,0.8)",
                font={"color": "#E8E8E8"}, height=320
            )
            st.plotly_chart(fig_z, use_container_width=True)

    # --- ONGLET 3 : COMPARAISON ---
    with tab3:
        st.markdown("#### ⚔️ Radar comparatif")
        st.info("Sélectionne 2 à 4 joueurs pour le radar physique.")

        player_list = [(r["player_name"], f"{r['player_name']} ({r['team_name']})")
                       for _, r in metrics_df.iterrows()]
        sel_radar = st.multiselect(
            "Joueurs", options=[p[0] for p in player_list],
            format_func=lambda x: next(n for pid, n in player_list if pid == x),
            max_selections=4,
            default=[player_list[0][0], player_list[1][0]] if len(player_list) >= 2 else []
        )

        if len(sel_radar) >= 2:
            radar_ids = sel_radar
            radar_names = sel_radar
            # Le radar attend player_id — on crée un index temporaire si besoin
            temp_df = metrics_df.copy()
            if "player_id" not in temp_df.columns:
                temp_df["player_id"] = temp_df["player_name"]
            radar_ids_mapped = [temp_df[temp_df["player_name"] == p]["player_id"].iloc[0]
                                 for p in sel_radar]
            st.plotly_chart(plot_physical_radar(temp_df, radar_ids_mapped, radar_names),
                            use_container_width=True)

            compare_cols = ["player_name", "team_name", "total_distance_km",
                            "max_speed_kmh", "sprint_count", "hir_distance_m", "dist_per_90"]
            avail_c = [c for c in compare_cols if c in metrics_df.columns]
            cdf = metrics_df[metrics_df["player_name"].isin(sel_radar)][avail_c].rename(columns={
                "player_name": "Joueur", "team_name": "Équipe",
                "total_distance_km": "Dist. (km)", "max_speed_kmh": "V.max",
                "sprint_count": "Sprints", "hir_distance_m": "HIR (m)", "dist_per_90": "Dist/90"
            })
            st.dataframe(cdf.set_index("Joueur"), use_container_width=True)

    # --- ONGLET 4 : MULTI-MATCHS ---
    with tab4:
        st.markdown("#### 📈 Évolution sur plusieurs matchs")

        if source == "SkillCorner":
            other_matches = {mid: f"{info['home']} vs {info['away']} ({info['date']})"
                             for mid, info in matches_dict.items() if mid != selected_match_id}
            extra = st.multiselect("Ajouter des matchs SKC", list(other_matches.keys()),
                                   format_func=lambda x: other_matches[x], max_selections=4)
            if extra:
                all_m = [metrics_df.copy()]
                prog = st.progress(0)
                for i, mid in enumerate(extra):
                    with st.spinner(f"Chargement..."):
                        em = compute_player_metrics(mid)
                        if em is not None:
                            all_m.append(em)
                    prog.progress((i+1)/len(extra))
                prog.empty()
                if len(all_m) >= 2:
                    mc = st.selectbox("Métrique", ["total_distance_km","max_speed_kmh","sprint_count","hir_distance_m"],
                                      format_func=lambda x: {"total_distance_km":"Dist.(km)","max_speed_kmh":"V.max","sprint_count":"Sprints","hir_distance_m":"HIR(m)"}.get(x,x))
                    st.plotly_chart(plot_multi_match_evolution(all_m, mc, mc), use_container_width=True)
        else:
            other_games = {gid: f"{ginfo['label']} ({ginfo['duration']})"
                           for gid, ginfo in METRICA_MATCHES.items() if gid != selected_game_id}
            extra = st.multiselect("Ajouter des matchs Metrica", list(other_games.keys()),
                                   format_func=lambda x: other_games[x], max_selections=1)
            if extra:
                all_m = [metrics_df.copy()]
                for gid in extra:
                    with st.spinner(f"Chargement Game {gid}..."):
                        em = compute_metrica_metrics(gid)
                        if em is not None:
                            all_m.append(em)
                if len(all_m) >= 2:
                    mc = st.selectbox("Métrique", ["total_distance_km","max_speed_kmh","sprint_count"],
                                      format_func=lambda x: {"total_distance_km":"Distance (km)","max_speed_kmh":"V.max","sprint_count":"Sprints"}.get(x,x))
                    st.plotly_chart(plot_multi_match_evolution(all_m, mc, mc), use_container_width=True)

    # --- ONGLET 5 : SOURCES COMBINÉES ---
    with tab5:
        st.markdown("#### 🔄 Pourquoi combiner SkillCorner et Metrica ?")

        col_skc, col_met = st.columns(2)

        with col_skc:
            st.markdown("""
            <div style="background:#0A1A0A; border:1px solid #00FF87; border-radius:10px; padding:16px;">
                <h4 style="color:#00FF87; margin:0 0 10px 0;">⚽ SkillCorner</h4>
                <p style="color:#aaa; font-size:0.85rem;">
                    <b>Broadcast tracking</b> extrait des images TV à 10 fps.
                    Contient uniquement les <b>actions avec ballon</b>.
                </p>
                <p style="color:#888; font-size:0.8rem; margin-top:12px;"><b style="color:#00FF87">✅ Points forts</b></p>
                <ul style="color:#888; font-size:0.8rem; margin:4px 0;">
                    <li>Contexte tactique (possession, passes, pressing)</li>
                    <li>Vitesse précise sur chaque action</li>
                    <li>Matchs réels top 5 ligues</li>
                    <li>10 matchs A-League 2024/25 en open data</li>
                </ul>
                <p style="color:#888; font-size:0.8rem; margin-top:10px;"><b style="color:#FF5722">❌ Limites</b></p>
                <ul style="color:#888; font-size:0.8rem; margin:4px 0;">
                    <li>Pas de kilométrage total</li>
                    <li>Heatmap partielle (que les actions)</li>
                    <li>Pas de données de déplacement sans ballon</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        with col_met:
            st.markdown("""
            <div style="background:#0A0A1A; border:1px solid #3A7BD5; border-radius:10px; padding:16px;">
                <h4 style="color:#3A7BD5; margin:0 0 10px 0;">📍 Metrica Sports</h4>
                <p style="color:#aaa; font-size:0.85rem;">
                    <b>Tracking optique complet</b> à 25 fps.
                    Enregistre la position de <b>tous les joueurs à chaque frame</b>.
                </p>
                <p style="color:#888; font-size:0.8rem; margin-top:12px;"><b style="color:#3A7BD5">✅ Points forts</b></p>
                <ul style="color:#888; font-size:0.8rem; margin:4px 0;">
                    <li>Vrai kilométrage (8-11 km/match)</li>
                    <li>Heatmap complète de tout le match</li>
                    <li>Déplacements hors ballon visibles</li>
                    <li>25 fps = granularité maximale</li>
                </ul>
                <p style="color:#888; font-size:0.8rem; margin-top:10px;"><b style="color:#FF5722">❌ Limites</b></p>
                <ul style="color:#888; font-size:0.8rem; margin:4px 0;">
                    <li>Joueurs anonymisés (Player1...)</li>
                    <li>Seulement 2 matchs disponibles</li>
                    <li>Pas de contexte tactique/événements</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("""
        #### 💡 Ce que les deux sources ensemble permettent d'analyser

        Dans un club professionnel, les analystes combinent typiquement :
        - Le **tracking complet** (GPS ou optique) pour les métriques physiques brutes
        - Les **données d'événements** (passes, tirs, duels) pour le contexte tactique

        Cette app reproduit cette logique avec des données open source :
        **Metrica** pour la charge physique réelle, **SkillCorner** pour le contexte tactique
        et les patterns de jeu avec ballon.
        """)

else:
    # État initial
    st.markdown("""
    <div style="text-align:center; padding:50px 20px;">
        <div style="font-size:3.5rem; margin-bottom:16px;">⚡</div>
        <h3 style="color:#888;">Sélectionne une source et un match dans la sidebar</h3>
        <p style="color:#555; font-size:0.9rem; margin-top:8px;">
            puis clique sur "Charger les données"
        </p>
        <div style="display:flex; justify-content:center; gap:16px; margin-top:32px; flex-wrap:wrap;">
            <div style="background:#0A1A0A; border:1px solid #00FF87; border-radius:10px; padding:16px; max-width:200px;">
                <div style="color:#00FF87; font-size:1.3rem; font-weight:bold;">SkillCorner</div>
                <div style="color:#888; font-size:0.8rem; margin-top:6px;">
                    10 matchs · A-League 2024/25<br>Actions sur balle · Vitesse · Zones
                </div>
            </div>
            <div style="background:#0A0A1A; border:1px solid #3A7BD5; border-radius:10px; padding:16px; max-width:200px;">
                <div style="color:#3A7BD5; font-size:1.3rem; font-weight:bold;">Metrica Sports</div>
                <div style="color:#888; font-size:0.8rem; margin-top:6px;">
                    2 matchs anonymisés<br>Tracking complet · Vrai kilométrage
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
