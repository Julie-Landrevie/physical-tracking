# ⚡ Physical Intensity & Tracking Analysis

> Analyse physique et de tracking broadcast — SkillCorner Open Data · Saison 2019/2020

[![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)](https://www.python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)
[![SkillCorner](https://img.shields.io/badge/Data-SkillCorner_Open_Data-00FF87?style=flat-square)](https://github.com/SkillCorner/opendata)
[![Status](https://img.shields.io/badge/Status-Live-success?style=flat-square)](.)

---

## 🎯 Objectif du projet

Ce projet analyse les **données de tracking broadcast** de SkillCorner pour extraire des métriques physiques clés sur les joueurs de football.

La question centrale : **Comment les joueurs se déplacent-ils vraiment sur un match de haut niveau ?**

À travers 10 matchs des meilleures équipes européennes (Man City vs Liverpool, Barça vs Real Madrid, Bayern vs Dortmund...), on répond à des questions concrètes :
- Qui a couru le plus dans le Classique ?
- Quel joueur a atteint la plus haute vitesse dans ce choc européen ?
- Comment évolue l'intensité physique entre la 1ère et la 2ème mi-temps ?

---

## 📊 Fonctionnalités

| Onglet | Ce qu'il montre |
|---|---|
| **🏟️ Vue match** | Distance totale, zones d'intensité, scatter profils physiques, tableau complet |
| **👤 Profil joueur** | Courbe de vitesse sur 90min, heatmap de présence, répartition par zones |
| **⚔️ Comparaison** | Radar comparatif multi-joueurs (jusqu'à 4), tableau côte-à-côte |
| **📈 Multi-matchs** | Évolution d'une métrique sur plusieurs matchs (chargement dynamique) |

---

## 🗂️ Structure du projet

```
physical-tracking/
│
├── app.py                                        # Application Streamlit principale
├── requirements.txt                              # Dépendances Python
├── README.md
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py                            # Chargement & calcul des métriques
│   └── viz.py                                    # Toutes les visualisations
│
└── notebooks/
    └── 01_physical_tracking_exploration.ipynb   # Exploration interactive
```

---

## 📐 Métriques calculées

| Métrique | Définition | Unité |
|---|---|---|
| **Distance totale** | Cumul des distances parcourues | km |
| **Distance/90** | Distance normalisée sur 90 minutes | km/90 |
| **Vitesse max** | Pic de vitesse atteint sur le match | km/h |
| **Sprints** | Nombre d'entrées dans la zone > 23 km/h | count |
| **HIR Distance** | Distance parcourue à > 19 km/h (norme UEFA) | mètres |
| **Zones d'intensité** | Répartition : Marche / Jogging / Course modérée / Intense / Sprint | m + % |

### Zones d'intensité (standard clubs pro)

| Zone | Seuil vitesse |
|---|---|
| 🟢 Marche | 0 → 7 km/h |
| 🟡 Jogging | 7 → 14 km/h |
| 🟠 Course modérée | 14 → 19 km/h |
| 🔴 Course intense | 19 → 23 km/h |
| 🚨 Sprint | > 23 km/h |

---

## 📦 Installation & lancement

```bash
# 1. Cloner le repo
git clone https://github.com/Julie-Landrevie/physical-tracking.git
cd physical-tracking

# 2. Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate   # Mac/Linux

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
streamlit run app.py
```

L'app s'ouvre automatiquement sur `http://localhost:8501`

> ⚠️ **Note** : Le premier chargement d'un match peut prendre 1-2 minutes — les fichiers de tracking sont volumineux (~50-150 Mo) et téléchargés depuis GitHub. Ensuite, tout est mis en cache.

---

## 🛠️ Stack technique

| Outil | Rôle |
|---|---|
| [Python 3.10+](https://www.python.org) | Langage principal |
| [Streamlit](https://streamlit.io) | Interface web interactive |
| [pandas](https://pandas.pydata.org) | Manipulation des données |
| [numpy](https://numpy.org) | Calculs numériques |
| [mplsoccer](https://mplsoccer.readthedocs.io) | Visualisations football (heatmaps, terrain) |
| [Plotly](https://plotly.com) | Graphiques interactifs |
| [requests](https://requests.readthedocs.io) | Téléchargement des données GitHub |

---

## 📡 Données

**Source** : [SkillCorner Open Data](https://github.com/SkillCorner/opendata) — 10 matchs, saison 2019/2020

Le **broadcast tracking** de SkillCorner extrait les positions des joueurs depuis les images TV (10 fps), sans caméras dédiées. Il couvre l'ensemble du match avec ~97% de précision sur l'identification des joueurs.

| Match | Compétition | Date |
|---|---|---|
| Manchester City vs Liverpool | Premier League | 10/11/2019 |
| Juventus vs Inter Milan | Serie A | 08/03/2020 |
| Real Madrid vs Barcelona | La Liga | 01/03/2020 |
| Bayern Munich vs Borussia Dortmund | Bundesliga | 26/05/2020 |
| PSG vs Lyon | Ligue 1 | 09/02/2020 |
| RB Leipzig vs Tottenham | Champions League | 19/02/2020 |
| Barcelona vs Napoli | Champions League | 08/08/2020 |
| Man City vs Real Madrid | Champions League | 07/08/2020 |
| Liverpool vs Atletico Madrid | Champions League | 11/03/2020 |
| Bayern Munich vs Chelsea | Champions League | 25/03/2020 |

*Data credit : [SkillCorner](https://skillcorner.com) — please credit SkillCorner if you use this data.*

---

## 🔜 Extensions prévues

- [ ] Intégration avec les données d'événements StatsBomb (synchronisation tracking + événements)
- [ ] Analyse de pressing : intensité collective défensive
- [ ] Physical Report PDF exportable par joueur
- [ ] Comparaison tracking vs xG (corrélation intensité / efficacité)

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
