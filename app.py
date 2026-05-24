"""
app.py
------
Application principale Streamlit — Physical Intensity & Tracking Analysis
Données : SkillCorner Open Data (10 matchs, saison 2019/2020)

Pour lancer l'application :
    streamlit run app.py

Structure de l'app :
    - Sidebar    : sélection du match et du mode d'analyse
    - Onglet 1   : Vue d'ensemble physique du match
    - Onglet 2   : Profil individuel d'un joueur
    - Onglet 3   : Comparaison entre joueurs
    - Onglet 4   : Évolution multi-matchs
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # mode non-interactif (nécessaire dans Streamlit)

from src.data_loader import (
    MATCHES_INFO,
    load_match_metadata,
    build_player_speeds_df,
    compute_player_metrics,
    compute_speed_timeline,
    get_match_label,
    SPEED_ZONES,
    ZONE_COLORS,
)
from src.viz import (
    plot_distance_bars,
    plot_intensity_zones,
    plot_speed_timeline,
    plot_distance_vs_maxspeed,
    plot_position_heatmap,
    plot_physical_radar,
    plot_multi_match_evolution,
    COLORS,
)

# ============================================================
# CONFIGURATION DE LA PAGE
# ============================================================

st.set_page_config(
    page_title="Physical Tracking Analysis | SkillCorner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour le style du dashboard
st.markdown("""
<style>
/* Fond général sombre */
.stApp {
    background-color: #0A0A0A;
    color: #E8E8E8;
}
/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0A1628 0%, #0A0A0A 100%);
    border-right: 1px solid #1A1A2E;
}
/* Métriques (cartes de stats) */
[data-testid="metric-container"] {
    background: #111111;
    border: 1px solid #00FF87;
    border-radius: 8px;
    padding: 12px;
}
/* Boutons */
.stButton > button {
    background: linear-gradient(135deg, #00FF87, #00CC6A);
    color: #0A0A0A;
    font-weight: bold;
    border: none;
    border-radius: 6px;
}
/* Onglets */
.stTabs [data-baseweb="tab"] {
    background: #111111;
    color: #888;
    border-radius: 8px 8px 0 0;
    padding: 8px 20px;
}
.stTabs [aria-selected="true"] {
    background: #1A1A2E;
    color: #00FF87 !important;
    border-bottom: 2px solid #00FF87;
}
/* Titres */
h1, h2, h3 {
    color: #E8E8E8;
}
/* Selectbox */
.stSelectbox > div > div {
    background: #111111;
    color: #E8E8E8;
    border: 1px solid #333;
}
/* Spinner de chargement */
.stSpinner > div {
    border-top-color: #00FF87 !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# HEADER
# ============================================================

st.markdown("""
<div style="text-align:center; padding: 20px 0 10px 0;">
    <h1 style="font-size:2.5rem; color:#00FF87; letter-spacing:2px; margin:0;">
        ⚡ Physical Intensity & Tracking Analysis
    </h1>
    <p style="color:#888; font-size:1rem; margin:5px 0 0 0;">
        Broadcast Tracking Data · SkillCorner Open Data · Saison 2019/2020
    </p>
</div>
<hr style="border-color:#1A1A2E; margin:10px 0 25px 0;">
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR — NAVIGATION & SÉLECTION
# ============================================================

with st.sidebar:
    st.markdown("""
    <div style="text-align:center; margin-bottom:20px;">
        <span style="font-size:2rem;">⚽</span>
        <br>
        <span style="color:#00FF87; font-weight:bold; font-size:1.1rem;">
            SkillCorner Tracker
        </span>
    </div>
    """, unsafe_allow_html=True)
    
    # Sélection du match
    st.subheader("📋 Sélection du match")
    match_options = {
        match_id: f"{info['home']} vs {info['away']} ({info['competition']})"
        for match_id, info in MATCHES_INFO.items()
    }
    
    selected_match_id = st.selectbox(
        "Choisir un match",
        options=list(match_options.keys()),
        format_func=lambda x: match_options[x],
        index=0
    )
    
    match_info = MATCHES_INFO[selected_match_id]
    
    # Affichage des infos du match sélectionné
    st.markdown(f"""
    <div style="background:#111; border:1px solid #1A1A2E; border-radius:8px; padding:12px; margin:10px 0;">
        <div style="color:#00FF87; font-weight:bold; font-size:1rem;">
            {match_info['home']} vs {match_info['away']}
        </div>
        <div style="color:#888; font-size:0.85rem;">🏆 {match_info['competition']}</div>
        <div style="color:#888; font-size:0.85rem;">📅 {match_info['date']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Info sur les données
    st.markdown("""
    <div style="font-size:0.8rem; color:#555; padding:8px; border:1px solid #222; border-radius:6px;">
        <b style="color:#888;">ℹ️ À propos des données</b><br>
        Broadcast tracking 10 fps<br>
        ~97% précision identification<br>
        Source : SkillCorner Open Data
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem; color:#444; text-align:center;">
        Built by <b style="color:#666;">Julie Landrevie</b><br>
        Football Data & Video Analyst
    </div>
    """, unsafe_allow_html=True)


# ============================================================
# CHARGEMENT DES DONNÉES (avec indicateur de progression)
# ============================================================

@st.cache_data(show_spinner=False)
def get_all_data(match_id: int):
    """Charge et calcule toutes les métriques pour un match donné."""
    df_speeds = build_player_speeds_df(match_id)
    if df_speeds is None:
        return None, None, None
    metrics = compute_player_metrics(df_speeds)
    meta = load_match_metadata(match_id)
    return df_speeds, metrics, meta


# Bouton de chargement
load_col1, load_col2, load_col3 = st.columns([1, 2, 1])
with load_col2:
    if st.button("🚀 Charger les données du match", use_container_width=True):
        st.session_state["data_loaded"] = True
        st.session_state["loaded_match_id"] = selected_match_id

# Charger si déjà en session (pour éviter de recharger à chaque interaction)
if "data_loaded" not in st.session_state:
    st.session_state["data_loaded"] = False

if st.session_state.get("data_loaded") and st.session_state.get("loaded_match_id") == selected_match_id:
    
    with st.spinner(f"⏳ Chargement des données tracking... (peut prendre 1-2 min)"):
        df_speeds, metrics_df, meta = get_all_data(selected_match_id)
    
    if df_speeds is None or metrics_df is None or metrics_df.empty:
        st.error("❌ Impossible de charger les données. Vérifie ta connexion internet.")
        st.stop()
    
    # ============================================================
    # MÉTRIQUES CLÉS EN HAUT DE PAGE
    # ============================================================
    
    st.markdown("### 📊 Vue d'ensemble du match")
    
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    with kpi1:
        n_players = metrics_df["player_name"].nunique()
        st.metric("👥 Joueurs trackés", n_players)
    
    with kpi2:
        avg_dist = metrics_df["total_distance_km"].mean()
        st.metric("🏃 Distance moy.", f"{avg_dist:.2f} km")
    
    with kpi3:
        max_speed_overall = metrics_df["max_speed_kmh"].max()
        fastest_player = metrics_df.loc[metrics_df["max_speed_kmh"].idxmax(), "player_name"]
        st.metric("⚡ Vitesse max", f"{max_speed_overall:.1f} km/h", help=f"Par {fastest_player}")
    
    with kpi4:
        total_sprints = metrics_df["sprint_count"].sum()
        st.metric("🚀 Total sprints", int(total_sprints))
    
    with kpi5:
        avg_hir = metrics_df["hir_distance_m"].mean()
        st.metric("🔥 HIR moy.", f"{avg_hir:.0f} m", help="High Intensity Running (>19 km/h)")
    
    st.markdown("---")
    
    # ============================================================
    # ONGLETS PRINCIPAUX
    # ============================================================
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏟️ Vue match",
        "👤 Profil joueur",
        "⚔️ Comparaison",
        "📈 Multi-matchs"
    ])
    
    # ----------------------------------------------------------
    # ONGLET 1 — VUE D'ENSEMBLE DU MATCH
    # ----------------------------------------------------------
    with tab1:
        st.markdown("#### 🏃 Distances parcourues")
        
        col_left, col_right = st.columns([3, 1])
        with col_right:
            top_n = st.slider("Nombre de joueurs", 5, len(metrics_df), 15)
        
        st.plotly_chart(
            plot_distance_bars(metrics_df, top_n=top_n),
            use_container_width=True
        )
        
        st.markdown("#### ⚡ Zones d'intensité")
        st.plotly_chart(
            plot_intensity_zones(metrics_df, top_n=top_n),
            use_container_width=True
        )
        
        st.markdown("#### 🔍 Profils physiques : Distance vs Vitesse max")
        st.caption("Taille des bulles = nombre de sprints")
        st.plotly_chart(
            plot_distance_vs_maxspeed(metrics_df),
            use_container_width=True
        )
        
        st.markdown("#### 📋 Tableau complet des métriques")
        
        # Colonnes à afficher (les plus importantes)
        display_cols = [
            "player_name", "team_name", "position",
            "total_distance_km", "max_speed_kmh", "sprint_count",
            "hir_distance_m", "dist_per_90", "time_observed_min"
        ]
        available_cols = [c for c in display_cols if c in metrics_df.columns]
        
        # Renommer pour l'affichage
        rename_map = {
            "player_name": "Joueur",
            "team_name": "Équipe",
            "position": "Poste",
            "total_distance_km": "Distance (km)",
            "max_speed_kmh": "Vitesse max (km/h)",
            "sprint_count": "Sprints",
            "hir_distance_m": "HIR (m)",
            "dist_per_90": "Dist/90 (km)",
            "time_observed_min": "Temps obs. (min)"
        }
        
        display_df = metrics_df[available_cols].rename(columns=rename_map)
        
        # Filtrer par équipe
        teams_in_match = ["Toutes les équipes"] + list(metrics_df["team_name"].unique())
        selected_team = st.selectbox("Filtrer par équipe", teams_in_match)
        
        if selected_team != "Toutes les équipes":
            display_df = display_df[display_df["Équipe"] == selected_team]
        
        st.dataframe(
            display_df.style.background_gradient(
                subset=["Distance (km)"], cmap="YlOrRd"
            ),
            use_container_width=True,
            height=400
        )
    
    # ----------------------------------------------------------
    # ONGLET 2 — PROFIL INDIVIDUEL
    # ----------------------------------------------------------
    with tab2:
        st.markdown("#### 👤 Profil physique d'un joueur")
        
        # Sélection du joueur
        player_options = {
            row["player_id"]: f"{row['player_name']} ({row['team_name']})"
            for _, row in metrics_df.iterrows()
        }
        
        selected_player_id = st.selectbox(
            "Choisir un joueur",
            options=list(player_options.keys()),
            format_func=lambda x: player_options[x]
        )
        
        if selected_player_id:
            player_row = metrics_df[metrics_df["player_id"] == selected_player_id].iloc[0]
            player_name = player_row["player_name"]
            
            # Carte de stats individuelles
            st.markdown(f"##### Stats de {player_name}")
            
            p1, p2, p3, p4, p5 = st.columns(5)
            with p1:
                st.metric("Distance", f"{player_row['total_distance_km']:.2f} km")
            with p2:
                st.metric("Vitesse max", f"{player_row['max_speed_kmh']:.1f} km/h")
            with p3:
                st.metric("Sprints", int(player_row['sprint_count']))
            with p4:
                st.metric("HIR", f"{player_row['hir_distance_m']:.0f} m")
            with p5:
                st.metric("Dist/90", f"{player_row.get('dist_per_90', 0):.2f} km")
            
            # Courbe de vitesse
            timeline = compute_speed_timeline(df_speeds, selected_player_id)
            if not timeline.empty:
                st.plotly_chart(
                    plot_speed_timeline(timeline, player_name),
                    use_container_width=True
                )
            
            # Heatmap de présence
            st.markdown("##### 🗺️ Carte de chaleur — zones de présence")
            with st.spinner("Génération de la heatmap..."):
                fig_heatmap = plot_position_heatmap(df_speeds, selected_player_id, player_name)
            
            if fig_heatmap:
                st.pyplot(fig_heatmap, use_container_width=True)
            else:
                st.warning("Pas assez de données de position pour ce joueur.")
            
            # Zones d'intensité pour ce joueur
            st.markdown("##### ⚡ Répartition par zones d'intensité")
            
            zone_data = []
            for zone_name in SPEED_ZONES.keys():
                col = f"dist_{zone_name}"
                pct_col = f"pct_{zone_name}"
                if col in player_row.index:
                    zone_data.append({
                        "Zone": zone_name,
                        "Distance (m)": player_row[col],
                        "% du temps": player_row.get(pct_col, 0)
                    })
            
            if zone_data:
                zone_df = pd.DataFrame(zone_data)
                
                import plotly.graph_objects as go
                fig_zones = go.Figure(go.Bar(
                    x=zone_df["Zone"],
                    y=zone_df["Distance (m)"],
                    marker_color=[ZONE_COLORS[z] for z in zone_df["Zone"]],
                    text=[f"{d:.0f}m ({p:.1f}%)" for d, p in
                          zip(zone_df["Distance (m)"], zone_df["% du temps"])],
                    textposition="outside",
                    hovertemplate="<b>%{x}</b><br>Distance: %{y:.0f} m<extra></extra>"
                ))
                fig_zones.update_layout(
                    title=f"Zones d'intensité — {player_name}",
                    xaxis_title="Zone",
                    yaxis_title="Distance (mètres)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(10,10,10,0.8)",
                    font={"color": "#E8E8E8"},
                    height=350
                )
                st.plotly_chart(fig_zones, use_container_width=True)
    
    # ----------------------------------------------------------
    # ONGLET 3 — COMPARAISON
    # ----------------------------------------------------------
    with tab3:
        st.markdown("#### ⚔️ Comparer plusieurs joueurs")
        
        st.info("Sélectionne 2 à 4 joueurs pour les comparer sur le radar physique.")
        
        # Multi-sélection
        player_list = [
            (row["player_id"], f"{row['player_name']} ({row['team_name']})")
            for _, row in metrics_df.iterrows()
        ]
        
        selected_for_radar = st.multiselect(
            "Choisir les joueurs à comparer",
            options=[p[0] for p in player_list],
            format_func=lambda x: next(name for pid, name in player_list if pid == x),
            max_selections=4,
            default=[player_list[0][0], player_list[1][0]] if len(player_list) >= 2 else []
        )
        
        if len(selected_for_radar) >= 2:
            selected_names = [
                next(name for pid, name in player_list if pid == pid_sel)
                for pid_sel in selected_for_radar
            ]
            selected_names_clean = [n.split(" (")[0] for n in selected_names]
            
            st.plotly_chart(
                plot_physical_radar(metrics_df, selected_for_radar, selected_names_clean),
                use_container_width=True
            )
            
            # Tableau comparatif côte-à-côte
            st.markdown("##### 📊 Comparaison détaillée")
            
            compare_cols = [
                "player_name", "team_name", "total_distance_km",
                "max_speed_kmh", "sprint_count", "hir_distance_m", "dist_per_90"
            ]
            available = [c for c in compare_cols if c in metrics_df.columns]
            compare_df = metrics_df[metrics_df["player_id"].isin(selected_for_radar)][available]
            compare_df = compare_df.rename(columns={
                "player_name": "Joueur",
                "team_name": "Équipe",
                "total_distance_km": "Dist. (km)",
                "max_speed_kmh": "V.max (km/h)",
                "sprint_count": "Sprints",
                "hir_distance_m": "HIR (m)",
                "dist_per_90": "Dist/90"
            })
            st.dataframe(compare_df.set_index("Joueur"), use_container_width=True)
        
        elif len(selected_for_radar) == 1:
            st.warning("Ajoute au moins un deuxième joueur pour la comparaison.")
    
    # ----------------------------------------------------------
    # ONGLET 4 — MULTI-MATCHS
    # ----------------------------------------------------------
    with tab4:
        st.markdown("#### 📈 Évolution physique sur plusieurs matchs")
        
        st.info("""
        Cet onglet permet d'analyser un joueur ou une équipe sur **plusieurs matchs**.
        Charge d'abord le match actuel, puis ajoute d'autres matchs pour voir l'évolution.
        """)
        
        # Sélection des matchs supplémentaires
        other_matches = {
            mid: match_options[mid] 
            for mid in MATCHES_INFO.keys() 
            if mid != selected_match_id
        }
        
        extra_matches = st.multiselect(
            "Ajouter d'autres matchs à analyser",
            options=list(other_matches.keys()),
            format_func=lambda x: other_matches[x],
            max_selections=4
        )
        
        if extra_matches:
            all_metrics_list = [metrics_df.assign(match_label=get_match_label(selected_match_id))]
            
            progress_bar = st.progress(0)
            for i, mid in enumerate(extra_matches):
                with st.spinner(f"Chargement {match_options[mid]}..."):
                    _, extra_metrics, _ = get_all_data(mid)
                    if extra_metrics is not None:
                        all_metrics_list.append(
                            extra_metrics.assign(match_label=get_match_label(mid))
                        )
                progress_bar.progress((i + 1) / len(extra_matches))
            
            progress_bar.empty()
            
            if len(all_metrics_list) >= 2:
                metric_choice = st.selectbox(
                    "Métrique à analyser",
                    options=["total_distance_km", "max_speed_kmh", "sprint_count", "hir_distance_m"],
                    format_func=lambda x: {
                        "total_distance_km": "Distance totale (km)",
                        "max_speed_kmh":     "Vitesse max (km/h)",
                        "sprint_count":      "Nombre de sprints",
                        "hir_distance_m":    "Distance HIR (m)"
                    }.get(x, x)
                )
                
                metric_labels = {
                    "total_distance_km": "Distance totale (km)",
                    "max_speed_kmh":     "Vitesse max (km/h)",
                    "sprint_count":      "Nombre de sprints",
                    "hir_distance_m":    "Distance HIR (m)"
                }
                
                st.plotly_chart(
                    plot_multi_match_evolution(
                        all_metrics_list,
                        metric_choice,
                        metric_labels.get(metric_choice, metric_choice)
                    ),
                    use_container_width=True
                )
        else:
            st.markdown("""
            <div style="text-align:center; color:#555; padding:40px;">
                Ajoute des matchs ci-dessus pour voir l'évolution 📈
            </div>
            """, unsafe_allow_html=True)

else:
    # État initial — avant chargement
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:#555;">
        <div style="font-size:4rem; margin-bottom:16px;">⚡</div>
        <h3 style="color:#888;">Sélectionne un match et clique sur "Charger les données"</h3>
        <p style="color:#555; font-size:0.9rem;">
            Les données de tracking peuvent prendre 1-2 minutes à charger<br>
            (fichiers volumineux depuis GitHub)
        </p>
        <br>
        <div style="display:flex; justify-content:center; gap:20px; flex-wrap:wrap;">
            <div style="background:#111; border:1px solid #00FF87; border-radius:8px; padding:16px; max-width:180px;">
                <div style="color:#00FF87; font-size:1.5rem;">10</div>
                <div style="color:#888; font-size:0.8rem;">matchs disponibles</div>
            </div>
            <div style="background:#111; border:1px solid #FF6B35; border-radius:8px; padding:16px; max-width:180px;">
                <div style="color:#FF6B35; font-size:1.5rem;">10 fps</div>
                <div style="color:#888; font-size:0.8rem;">broadcast tracking</div>
            </div>
            <div style="background:#111; border:1px solid #3A7BD5; border-radius:8px; padding:16px; max-width:180px;">
                <div style="color:#3A7BD5; font-size:1.5rem;">Top 5</div>
                <div style="color:#888; font-size:0.8rem;">ligues européennes</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
