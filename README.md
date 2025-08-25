# Navitrends-Local-Web-Radar
Navitrends Local Web Radar : détection automatique de sites web obsolètes pour la prospection commerciale
Objectif général
Développer un outil intelligent qui scanne automatiquement des listes de sites web dans une zone géographique ou un secteur donné (France, UK, Arabie Saoudite, etc.) afin d’identifier ceux présentant des signes de vétusté ou de mauvaise performance, dans le but de générer des leads qualifiés pour les offres de refonte, maintenance ou SEO de Navitrends.
## ✨ Fonctionnalités Principales

###  Audit Technique Complet
- **Vérification HTTPS/SSL** et sécurité
- **Analyse SEO avancée** : balises title, meta description, headings
- **Optimisation images** : détection des alt text manquants
- **Analyse des liens** : internes vs externes
- **Performance** : mesure du temps de chargement

###  Détection Intelligente
- **Reconnaissance automatique du pays** par TLD et contenu
- **Identification du secteur d'activité** par analyse sémantique
- **Filtres avancés** par pays et secteur d'activité

###  Reporting Professionnel
- **Rapports HTML** avec design moderne et responsive
- **Exports multiples** : CSV, JSON,pdf
- **Statistiques détaillées** et tableaux de bord
- **Interface graphique** native avec Tkinter

### 🗄 Gestion des Données
- **Base SQLite intégrée** pour le stockage
- **Historique complet** des analyses
- **Métriques et tendances** temporelles
- **Fonctions d'export/import**

## Installation Rapide

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de packages Python)

### Installation en 3 étapes
```bash
# 1. Cloner le repository
git clone https://github.com/JEBALIMalak/Navitrends-Local-Web-Radar.git
cd Navitrends-Local-Web-Radar

# 2. Créer et activer l'environnement virtuel
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Installer les dépendances
pip install -r requirements.txt

