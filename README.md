# ⚡ Physical Intensity & Tracking Analysis

> Analyse physique dual-source — SkillCorner Open Data · Metrica Sports Open Data

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)
[![SkillCorner](https://img.shields.io/badge/SkillCorner-Open_Data-00FF87?style=flat-square)](https://github.com/SkillCorner/opendata)
[![Metrica](https://img.shields.io/badge/Metrica_Sports-Open_Data-3A7BD5?style=flat-square)](https://github.com/metrica-sports/sample-data)
[![Status](https://img.shields.io/badge/Status-Live-success?style=flat-square)](.)

---

## 🎯 Objectif du projet

Ce projet analyse les **données de tracking football** pour extraire des métriques physiques clés sur les joueurs. Il combine deux sources de données open source **complémentaires** pour couvrir l'ensemble des besoins d'une analyse physique complète.

**Question centrale : comment les joueurs se déplacent-ils vraiment sur un match de haut niveau ?**

---

## 📡 Deux sources de données

L'app propose deux modes sélectionnables dans la sidebar. Chaque source apporte des informations différentes et complémentaires.

### ⚽ SkillCorner Open Data

**Broadcast tracking** extrait des images TV. Contient uniquement les **actions avec ballon** (possessions, passes, dribbles, courses balle au pied).

| Info | Détail |
|---|---|
| **Matchs** | 10 matchs — A-League 2024/2025 |
| **Format** | `{id}_dynamic_events.csv` — une ligne par action |
| **Fréquence** | Variable (par action, pas frame par frame) |
| **Joueurs** | Identifiés (noms réels) |
| **Coordonnées** | x/y en mètres sur le terrain |

**Ce qu'on peut calculer :**
- Distance parcourue **sur les actions avec ballon** (~1 000-1 500 m/match)
- Vitesse moyenne et vitesse max par action
- Zones d'intensité (Jogging / Running / Haute intensité / Sprint)
- Nombre de sprints
- Contexte tactique : possession, phase de jeu, pressing

> ⚠️ Les dynamic_events ne contiennent **pas** les déplacements sans ballon. Le vrai kilométrage total d'un match (~8-11 km) n'est pas accessible dans l'open data public — il nécessite un accès au tracking XY brut (compte SkillCorner Pro).

---

### 📍 Metrica Sports Open Data

**Tracking optique complet** à 25 fps. Enregistre la position de **tous les joueurs à chaque frame**, avec et sans ballon.

| Info | Détail |
|---|---|
| **Matchs** | 2 matchs anonymisés (Sample Game 1 & 2) |
| **Format** | `RawTrackingData_Home/Away_Team.csv` — une ligne par frame |
| **Fréquence** | 25 fps (~145 000 frames/match) |
| **Joueurs** | Anonymisés (Player1, Player2...) |
| **Coordonnées** | Normalisées 0→1, converties en mètres (105×68m) |

**Ce qu'on peut calculer :**
- **Vrai kilométrage total** (~9-11 km/match, cohérent avec les normes pro)
- Vitesse max réelle (filtrée, plafonnée à 36 km/h)
- Heatmap complète sur tout le match (y compris hors possession)
- Déplacements sans ballon, pressing, repositionnement

**Filtre de cohérence physique appliqué :**
Les données brutes contiennent des artefacts (mauvaise identification du joueur par l'algo de tracking). Trois règles filtrent ces erreurs :
1. **Téléportations** : gap de frames → vitesse mise à 0
2. **Vitesses impossibles** : > 36 km/h → supprimées (record Mbappé ~35.7 km/h en match)
3. **Pics isolés** : pic > 25 km/h non confirmé par les frames adjacentes → supprimé

---

## 🔄 Pourquoi combiner les deux sources ?

Dans un club professionnel, les analystes combinent toujours :
- Le **tracking complet** (GPS ou optique) → charge physique brute
- Les **données d'événements** → contexte tactique

Cette app reproduit cette logique avec des données open source :

| Métrique | SkillCorner | Metrica |
|---|:---:|:---:|
| Vrai kilométrage (~8-11 km) | ❌ | ✅ |
| Vitesse max | ✅ | ✅ |
| Zones d'intensité | ✅ | ✅ |
| Nombre de sprints | ✅ | ✅ |
| Heatmap complète | ⚠️ partielle | ✅ |
| Contexte tactique | ✅ | ❌ |
| Pressing / passes / possession | ✅ | ❌ |
| Joueurs identifiés | ✅ | ❌ |

---

## 📊 Fonctionnalités de l'app

| Onglet | Contenu |
|---|---|
| **🏟️ Vue match** | Distances, zones d'intensité, scatter profils, tableau complet |
| **👤 Profil joueur** | Courbe de vitesse brute, carte de chaleur, zones individuelles |
| **⚔️ Comparaison** | Radar comparatif multi-joueurs (jusqu'à 4), tableau côte-à-côte |
| **📈 Multi-matchs** | Évolution d'une métrique sur plusieurs matchs |
| **🔄 Sources combinées** | Explication de la complémentarité des deux sources |

---

## 🗂️ Structure du projet

```
physical-tracking/
│
├── app.py                          # Application Streamlit — dual-source
├── requirements.txt
├── README.md
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py              # SkillCorner — dynamic_events
│   ├── metrica_loader.py           # Metrica — tracking XY 25fps
│   └── viz.py                      # Visualisations partagées (les deux sources)
│
└── notebooks/
    └── 01_physical_tracking_exploration.ipynb
```

---

## 📐 Métriques calculées

| Métrique | Définition | Source |
|---|---|---|
| **Distance (sur balle)** | Cumul des distances sur actions avec ballon | SKC |
| **Distance totale** | Vrai kilométrage sur tout le match | Metrica |
| **Distance/90** | Distance normalisée sur 90 minutes | Les deux |
| **Vitesse max** | Pic de vitesse atteint | Les deux |
| **Sprints** | Actions/séquences à > 25 km/h | Les deux |
| **HIR Distance** | Distance à > 20 km/h (norme standard) | Les deux |
| **Zones d'intensité** | Jogging / Running / Haute intensité / Sprint | Les deux |

### Zones d'intensité

| Zone | Seuil km/h | Couleur |
|---|---|---|
| 🟢 Jogging | 0 → 15 km/h | |
| 🟡 Running | 15 → 20 km/h | |
| 🔴 Haute intensité | 20 → 25 km/h | |
| 🚨 Sprint | > 25 km/h | |

---

## 📦 Installation & lancement

```bash
# 1. Cloner le repo
git clone https://github.com/Julie-Landrevie/physical-tracking.git
cd physical-tracking

# 2. Environnement virtuel
python3 -m venv venv
source venv/bin/activate   # Mac/Linux

# 3. Dépendances
pip install -r requirements.txt

# 4. Lancer
streamlit run app.py
```

> ⚠️ Le chargement Metrica prend ~2 minutes (145 000 frames téléchargées et traitées depuis GitHub). Après le premier chargement, tout est mis en cache par Streamlit.

---

## 🛠️ Stack technique

| Outil | Rôle |
|---|---|
| [Python 3.10+](https://www.python.org) | Langage principal |
| [Streamlit](https://streamlit.io) | Interface web interactive |
| [pandas](https://pandas.pydata.org) | Manipulation des données |
| [numpy](https://numpy.org) | Calculs numériques (vitesses, distances) |
| [mplsoccer](https://mplsoccer.readthedocs.io) | Terrain de foot + heatmaps |
| [Plotly](https://plotly.com) | Graphiques interactifs |
| [requests](https://requests.readthedocs.io) | Téléchargement des données GitHub |

---

## 🔜 Extensions prévues

- [ ] Intégration StatsBomb events (synchronisation tracking + événements sur Metrica)
- [ ] Analyse de pressing : intensité collective défensive
- [ ] Physical Report PDF exportable par joueur
- [ ] Corrélation distance HIR / efficacité offensive (xG)

---

## 🔗 Projets liés

- [MPG Optimizer](https://github.com/Julie-Landrevie/mpg-analytics) — Fantasy football analytics
- [xG & Shooting Profile Analysis](https://github.com/Julie-Landrevie/xg-shooting-analysis) — StatsBomb Open Data
- [Pass Network & Team Structure](https://github.com/Julie-Landrevie/pass-network) — À venir

---

## 👤 Auteure

**Julie Landrevie** — Football Data & Video Analyst

Certifiée Sports Analytics (University of Michigan) · Analyse Vidéo et Data dans le Sport (Université de Lorraine) · Dartfish Certified Analyst

📧 julie.landrevie@free.fr · [LinkedIn](https://www.linkedin.com/in/julie-landrevie) · [GitHub](https://github.com/Julie-Landrevie)
