# ETL - Journaux Officiels du Congo-Brazzaville

Ce projet permet de convertir les textes de loi du Congo-Brazzaville depuis des fichiers Markdown (extraits de PDFs scannés) vers un format JSON structuré et facilement consultable sur mobile.

## 🎯 Objectif

Rendre accessible les textes juridiques (Constitution, Journal Officiel, Codes, Décrets) du Congo-Brazzaville qui sont souvent stockés au format papier ou dans des PDFs non consultables.

## 📁 Structure du projet

```text
├── data/
│   ├── raw/              # PDFs originaux
│   ├── processed/        # Fichiers .md extraits des PDFs (après OCR)
│   └── out/
│       ├── json/         # Sortie du convertisseur basique
│       ├── quarantine/   # Fichiers JSON invalides (ne respectant pas le schéma)
│       └── *.json        # Fichiers JSON valides prêts pour l'import
│
├── schemas/
│   └── journal_officiel.schema.json  # Schéma JSON strict avec support des alinéas, énumérations et références
│
├── convert_jo_structured.py          # Convertisseur structuré : granulation des articles, extraction des références, sanitisation OCR et validation JSON
├── md_to_json_converter.py          # Convertisseur basique (format libre)
├── load_json_to_postgres.py         # Script de chargement en base de données
└── README.md
```

## 🔧 Workflow Principal

### 1. Conversion (`convert_jo_structured.py`)

Convertit les fichiers Markdown en JSON structuré conforme au schéma `schemas/journal_officiel.schema.json`.

**Flux par défaut** :
- **Entrée** : `data/processed/*.md`
- **Sortie** : `data/out/*.json`
- **Quarantaine** : `data/out/quarantine/`

**Commandes** :
```bash
# Convertir tous les fichiers du dossier par défaut (data/processed)
python3 convert_jo_structured.py

# Convertir un fichier spécifique
python3 convert_jo_structured.py --input data/processed/congo-jo-2025-26.md
```

**Gestion des erreurs (Quarantaine)** :
Les fichiers JSON générés sont validés contre le schéma JSON. Si un fichier est invalide (structure incorrecte, champs manquants), il est automatiquement déplacé dans le dossier `data/out/quarantine/` pour inspection manuelle. Cela garantit que seules les données valides sont disponibles pour le chargement.

### 2. Chargement en Base de Données (`load_json_to_postgres.py`)

Charge les fichiers JSON valides dans la base de données PostgreSQL. Supporte la hiérarchie complète (`ltree`) et le versioning des articles.

**Flux par défaut** :
- **Entrée** : `data/out/*.json`

**Commandes** :
```bash
# Charger tous les fichiers JSON du dossier par défaut (data/out)
python3 load_json_to_postgres.py
```

## 🚀 Installation

### Prérequis

- Python 3.8 ou supérieur
- PostgreSQL avec extension `ltree` (et optionnellement `vector`)
- Dépendances : `pip install -r requirements.txt`

### Installation rapide

```bash
# Cloner ou télécharger le projet
git clone https://github.com/benaja-bendo/Mibeko-etl.git
cd Mibeko-etl
pip install -r requirements.txt
```

## 💻 Utilisation Complète

### 1. Initialisation de la Base de Données

```bash
# Attention: Supprime les données existantes et recrée les tables
python3 apply_schema.py
```

### 2. Conversion (Markdown -> JSON)

```bash
python3 convert_jo_structured.py
```

### 3. Chargement (JSON -> PostgreSQL)

```bash
python3 load_json_to_postgres.py
```

### 4. Vérification

```bash
python3 verify_data.py
```

## 📊 Structure des données JSON

### Format de sortie

```json
{
  "id": "congo-jo-2025-26",
  "source_file": "congo-jo-2025-26.md",
  "textes": [
    {
      "numero_texte": "Loi n° 10-2025",
      "date_publication": "2025-05-28",
      "intitule_long": "...",
      "contenu": [
        {
          "type": "Titre",
          "intitule": "TITRE I : ...",
          "elements": [...]
        }
      ],
      "signatures": ["..."]
    }
  ]
}
```

## 🛠️ Architecture technique

### Classes principales

#### `TexteLegal`
Représente un texte juridique avec tous ses attributs :
- Métadonnées (type, numéro, date)
- Contenu structuré (articles, références)
- Signataires

#### `Publication`
Représente un numéro du Journal Officiel :
- Informations de publication
- Collection de textes légaux

#### `MarkdownToJsonConverter`
Moteur de conversion avec :
- Détection intelligente des types de textes
- Extraction par regex des structures
- Normalisation des données

## 🎨 Améliorations futures

- [ ] Extraction des tableaux (tarifs, budgets)
- [ ] Détection des annexes
- [ ] Extraction des préambules
- [x] OCR intégré pour les PDFs scannés
- [ ] Interface web de consultation
- [ ] API REST pour accès mobile
- [ ] Base de données SQLite(mobile)/PostgreSQL(web)
- [ ] Moteur de recherche full-text

## 🤝 Contribution

Ce projet vise à améliorer l'accès à la justice au Congo-Brazzaville. Toute contribution est bienvenue.

## 📄 Licence

Ce projet est destiné à servir l'intérêt public en facilitant l'accès aux textes de loi.

---

**Fait avec ❤️ pour rendre la justice accessible à tous les Congolais**
