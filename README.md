# Pipeline ETL avec Analyse et Visualisation

## Description
Ce projet est un pipeline complet pour l'extraction, le traitement, le stockage, et l'analyse des données académiques provenant de **IEEE Xplore** et **Google Scholar**. Il utilise une combinaison d'outils et technologies modernes pour automatiser le flux de travail, en allant du scraping web jusqu'à la création de tableaux de bord interactifs.

## Architecture du Pipeline

1. **Sources des Données**
   - **IEEE Xplore** et **Google Scholar** : Extraction des publications académiques.
   - **Selenium** : Automatisation du scraping des données.

2. **Stockage Initial**
   - **MongoDB Atlas** : Base NoSQL utilisée pour stocker les données semi-structurées.

3. **Traitement des Données**
   - **PySpark** : Nettoyage, transformation, et préparation des données à grande échelle.

4. **Stockage Structuré**
   - **Azure SQL** : Base relationnelle pour organiser les données traitées.

5. **Analyse Avancée**
   - **Azure Synapse Analytics** : Plateforme utilisée pour les calculs complexes et l'intégration des données pour l'analyse.

6. **Visualisation**
   - **Power BI** : Création de tableaux de bord et rapports interactifs pour les décideurs.

7. **Orchestration**
   - **Apache Airflow** : Automatisation et gestion des différentes étapes du pipeline.

## Fonctionnalités
- Scraping web avec Selenium pour extraire les données depuis des plateformes académiques.
- Stockage flexible des données semi-structurées dans MongoDB Atlas.
- Traitement distribué avec PySpark pour gérer de grands volumes de données.
- Migration des données structurées vers Azure SQL pour des analyses SQL rapides.
- Intégration des données dans Azure Synapse Analytics pour une analyse avancée.
- Création de visualisations interactives avec Power BI.
- Orchestration automatisée avec Apache Airflow.

## Technologies Utilisées
- **Scraping** : Selenium
- **Stockage** : MongoDB Atlas, Azure SQL
- **Traitement des Données** : PySpark
- **Analyse et Visualisation** : Azure Synapse Analytics, Power BI
- **Automatisation** : Apache Airflow

## Installation et Configuration

### Prérequis
- Python 3.x
- Selenium installé via `pip install selenium`
- MongoDB Atlas configuré avec une base accessible
- Azure SQL et Synapse configurés
- Apache Airflow installé et configuré
- Power BI Desktop ou accès au service cloud Power BI

### Étapes d'installation
1. Clonez le dépôt :
   ```bash
   git clone <URL_DU_DEPOT>
   cd <NOM_DU_PROJET>
   ```

2. Installez les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```

3. Configurez MongoDB Atlas et mettez à jour les paramètres de connexion dans le fichier de configuration.

4. Configurez Selenium avec le driver correspondant à votre navigateur (par exemple : ChromeDriver).

5. Lancez Apache Airflow :
   ```bash
   airflow db init
   airflow webserver
   airflow scheduler
   ```

6. Importez les données extraites dans MongoDB avec le script fourni.

7. Configurez les connexions avec Azure SQL et Synapse pour les étapes ultérieures.

8. Créez les visualisations dans Power BI à partir des données intégrées dans Azure Synapse.



## Résultats Attendus
- Une base de données enrichie contenant les publications extraites.
- Analyse approfondie des données avec des insights exploitables.
- Rapports et tableaux de bord interactifs pour la prise de décision.

## Auteurs
- **Votre Nom** : Développeur principal.

## Licence
Ce projet est sous licence [Nom de la Licence].
