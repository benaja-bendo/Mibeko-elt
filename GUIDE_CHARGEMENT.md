# Guide de Chargement des Données Mibeko

Ce guide explique comment charger les données extraites (fichiers JSON) dans la base de données PostgreSQL.

## Prérequis

1.  **Base de données PostgreSQL**
    - Assurez-vous d'avoir une instance PostgreSQL en cours d'exécution.
    - Créez la base de données et les tables en utilisant le script `database/schema_postgres.sql`.

2.  **Environnement Python**
    - Installez les dépendances nécessaires :
      ```bash
      pip install -r requirements.txt
      ```

## Configuration

Le script de chargement utilise des variables d'environnement pour la connexion à la base de données. Vous pouvez les définir avant de lancer le script ou modifier les valeurs par défaut dans `load_json_to_postgres.py`.

Variables par défaut :
- `DB_HOST`: localhost
- `DB_PORT`: 5432
- `DB_NAME`: mibeko
- `DB_USER`: postgres
- `DB_PASSWORD`: password

## Utilisation

### 1. Générer les fichiers JSON
Si ce n'est pas déjà fait, convertissez vos fichiers Markdown en JSON :
```bash
python3 md_to_json_converter.py
```
Cela créera les fichiers JSON dans le dossier de sortie (par défaut `data/out/json`).

### 2. Charger les données dans PostgreSQL
Utilisez le script `load_json_to_postgres.py` en lui indiquant le dossier contenant les fichiers JSON ou un fichier spécifique.

**Pour charger un dossier entier :**
```bash
python3 load_json_to_postgres.py data/out/json
```

**Pour charger un seul fichier :**
```bash
python3 load_json_to_postgres.py data/out/json/congo-jo-2025-26.json
```

## Vérification
Après le chargement, vous pouvez vérifier les données dans votre base PostgreSQL :
```sql
SELECT count(*) FROM textes;
SELECT * FROM publications;
```
