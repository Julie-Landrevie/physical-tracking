# ⚽ xG & Shooting Profile Analysis

> Analyse de la qualité des tirs et des profils de finisseurs en football  
> à partir des données **StatsBomb Open Data**

**Julie Landrevie — Football Data Analyst**  
*Certifiée Sports Analytics (University of Michigan) · Analyse Vidéo & Data dans le Sport (Université de Lorraine)*

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://xg-shooting-analysis.streamlit.app)

---

## 📌 Présentation du projet

Ce projet analyse la **qualité des tirs** en football à travers le prisme du **xG (expected goals)** — une métrique qui quantifie la probabilité qu'un tir se transforme en but, en fonction de critères comme la position, la technique, ou le contexte du tir.

L'objectif est double :
- **Identifier les finisseurs efficaces** : qui surperforme ou sous-performe par rapport à son xG ?
- **Comprendre les patterns de tir** : d'où viennent les occasions les plus dangereuses, à quel moment du match, avec quelle technique ?

### Pourquoi le xG ?

La conversion brute (buts / tirs) est trop sensible à la variance sur un petit échantillon. Le xG permet de **séparer la qualité des occasions créées de l'efficacité du finisseur**, et d'évaluer les joueurs sur ce qui dépend vraiment d'eux.

🌐 **App en ligne :** [xg-shooting-analysis.streamlit.app](https://xg-shooting-analysis.streamlit.app)

---

## ⚠️ Limites des données StatsBomb Open Data

StatsBomb publie gratuitement une **sélection de matchs** par compétition — pas la saison entière.  
Pour La Liga par exemple, seuls les matchs de **Barcelona** sont couverts (~34-35 matchs sur 380).

| Compétition | Matchs disponibles | Remarque |
|-------------|-------------------|----------|
| La Liga 2020/21 | ~35 matchs | Matchs Barcelona uniquement |
| La Liga 2019/20 | ~33 matchs | Matchs Barcelona uniquement |
| Champions League | ~120 matchs | Plusieurs équipes couvertes |
| WSL 2020/21 | ~130 matchs | Couverture plus large |
| EURO 2020 | ~51 matchs | Tournoi complet |
| Coupe du Monde 2022 | ~64 matchs | Tournoi complet |

> **Conséquence pratique :** Les classements "top tireurs" de La Liga reflètent l'échantillon disponible, pas le championnat entier. Pour des analyses inter-équipes représentatives, préférer les tournois complets (EURO, Coupe du Monde) ou la WSL. L'app affiche automatiquement le nombre de matchs couverts.

---

## 🎯 Fonctionnalités

### 📊 Dashboard Streamlit interactif

| Onglet | Description |
|--------|-------------|
| **Vue d'ensemble** | KPIs globaux, top tireurs, répartition par résultat et partie du corps |
| **Shot Map** | Tirs positionnés sur le terrain — taille = xG, couleur = résultat |
| **Profil tireur** | xG vs buts réels par joueur, tri dynamique, tableau complet |
| **Overperformance** | Lollipop chart buts − xG, podiums sur/sous-performants |
| **Zones** | Heatmap xG par zone du terrain + statistiques détaillées |
| **Distribution** | Histogramme de qualité des occasions créées |
| **Timeline** | Accumulation xG minute par minute sur un match choisi |
| **Comparaison** | Face-à-face deux joueurs : métriques + shot maps côte à côte |

**3 filtres sidebar :** Compétition → Équipe → Joueur (tout interconnecté)

### 📓 Notebook analytique

Analyse complète en 12 sections sur la **La Liga 2020/2021** :
- Exploration des données et validation
- Shot maps (Barcelona, Atlético Madrid, etc.)
- Profils tireurs : top xG, top finisseurs, top sélecteurs de tir
- Overperformance sur la saison entière
- Heatmaps et zones de danger
- Timeline El Clásico
- Deep dive Messi
- Insights et conclusions

---

## 🗂️ Structure du projet

```
xg-shooting-analysis/
│
├── src/
│   ├── data_loader.py        # Chargement & nettoyage données StatsBomb
│   ├── metrics.py            # Calcul des métriques xG
│   └── viz.py                # Visualisations + dictionnaire 264 noms connus
│
├── notebooks/
│   └── 01_xg_shooting_analysis.ipynb   # Analyse complète La Liga 2020/21
│
├── data/
│   └── cache/                # Données mises en cache (auto-généré)
│
├── app.py                    # Dashboard Streamlit
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation & Lancement

```bash
git clone https://github.com/Julie-Landrevie/xg-shooting-analysis.git
cd xg-shooting-analysis
pip install -r requirements.txt
streamlit run app.py
```

> **Note :** Le premier chargement télécharge les données StatsBomb (~1-2 min). Mises en cache ensuite.

```bash
jupyter notebook notebooks/01_xg_shooting_analysis.ipynb
```

---

## 📦 Stack technique

| Catégorie | Outils |
|-----------|--------|
| **Données** | [statsbombpy](https://github.com/statsbomb/statsbombpy) — StatsBomb Open Data |
| **Manipulation** | pandas · numpy |
| **Visualisation terrain** | [mplsoccer](https://mplsoccer.readthedocs.io/) |
| **Graphiques** | matplotlib |
| **Dashboard** | Streamlit |
| **Notebook** | Jupyter · nbformat |

---

## 📐 Métriques calculées

| Métrique | Définition |
|----------|-----------|
| `xg` | xG total — somme des probabilités de but de chaque tir |
| `xg_per_shot` | xG moyen par tir — qualité de sélection des occasions |
| `overperformance` | Buts − xG — mesure l'efficacité nette du finisseur |
| `on_target_rate` | % de tirs cadrés (Goal ou Saved) |
| `big_chances` | Nombre d'occasions à xG ≥ 0.30 |
| `conversion_rate` | Taux de conversion réel (buts / tirs) |
| `xg_per_match` | xG moyen par match — intensité offensive régulière |

---

## 💡 Insights clés — La Liga 2020/2021 (matchs Barcelona)

*(Données partielles — matchs Barcelona uniquement)*

- **Lionel Messi** domine avec 195 tirs et ~23 xG — meilleur créateur d'occasions de loin
- **Arturo Vidal** affiche la meilleure overperformance (+3.68) — très efficace sur peu d'occasions
- **Martin Braithwaite** est le plus malchanceux (−1.82) — crée des occasions de qualité sans les convertir
- La **surface centrale** concentre le plus de tirs, mais la zone **penalty / but vide** a le xG moyen le plus élevé
- La **dernière demi-heure** (60–90') est la tranche la plus dangereuse en xG cumulé

---

## 🚀 Extensions prévues

- [ ] Intégration des **key passes** pour analyser les assistants (xA)
- [ ] Comparaison multi-saisons — évolution d'un joueur dans le temps
- [ ] Analyse des tirs **sous pression** vs tirs libres
- [ ] Intégration **SkillCorner tracking data**
- [ ] Export PDF des profils joueurs

---

## 📁 Projets liés

| Projet | Description | Lien |
|--------|-------------|------|
| **Tactical Dashboard** | Pass Network, xG, Pressing, Heatmaps | [→ Repo](https://github.com/Julie-Landrevie/tactical-dashboard-football) · [→ App](https://tactical-dashboard-football.streamlit.app) |
| **MPG Optimizer** | Fantasy football analytics | [→ Repo](https://github.com/Julie-Landrevie/mpg-optimizer) · [→ App](https://mpg-optimizer.streamlit.app) |

---

## 📧 Contact

**Julie Landrevie**  
📩 julie.landrevie@free.fr  
🎓 Sports Analytics — University of Michigan (Coursera)  
🎓 Analyse Vidéo & Data dans le Sport — Université de Lorraine  
🎓 Dartfish Certified Analyst

---

*Données : [StatsBomb Open Data](https://github.com/statsbomb/open-data) — utilisées conformément à la licence open data StatsBomb.*
