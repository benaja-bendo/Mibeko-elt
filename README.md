# ETL - Journaux Officiels du Congo-Brazzaville

Ce projet permet de convertir les textes de loi du Congo-Brazzaville depuis des fichiers Markdown (extraits de PDFs scannés) vers un format JSON structuré et facilement consultable sur mobile.

## 🎯 Objectif

Rendre accessible les textes juridiques (Constitution, Journal Officiel, Codes, Décrets) du Congo-Brazzaville qui sont souvent stockés au format papier ou dans des PDFs non consultables.

## 📁 Structure du projet

```
etl/
├── data/
│   ├── raw/              # PDFs originaux (si disponibles)
│   ├── processed/        # Fichiers .md convertis
│   └── json/             # Fichiers .json générés (sortie)
├── md_to_json_converter.py   # Script principal de conversion
└── README.md             # Ce fichier
```

## 🚀 Installation

### Prérequis

- Python 3.8 ou supérieur
- Aucune dépendance externe requise (utilise uniquement la bibliothèque standard Python)

### Installation rapide

```bash
# Cloner ou télécharger le projet
git clone https://github.com/benaja-bendo/Mibeko-etl.git

cd Mibeko-etl
# Le script est prêt à l'emploi, aucune installation nécessaire!
```

## 💻 Utilisation

### Conversion de tous les fichiers

```bash
python3 md_to_json_converter.py
```

Cela convertira tous les fichiers `.md` de `data/processed/` vers `data/json/`

### Conversion d'un fichier spécifique

```bash
python3 md_to_json_converter.py --file congo-jo-1959-02.md
```

### Options disponibles

```bash
# Spécifier le répertoire d'entrée
python3 md_to_json_converter.py --input data/processed

# Spécifier le répertoire de sortie
python3 md_to_json_converter.py --output data/json

# Aide complète
python3 md_to_json_converter.py --help
```

## 📊 Structure des données JSON

### Format de sortie

Chaque fichier JSON généré contient :

```json
{
  "id": "congo-jo-1959-02",
  "numero_parution": "02",
  "date_parution": null,
  "annee": 1959,
  "titre": "JOURNAL OFFICIEL DE LA RÉPUBLIQUE DU CONGO",
  "textes": [
    {
      "id": "congo-jo-1959-02-loi-3-58",
      "type_texte": "LOI",
      "numero": "3/58",
      "date": "1958-12-29",
      "titre": "LOI N° 3/58 DU 29 DECEMBRE 1958",
      "contenu": "Texte complet...",
      "articles": [
        {
          "numero": "1er",
          "contenu": "Les alineas 3 et 4 de l'article 3..."
        },
        {
          "numero": "2",
          "contenu": "Pendant la durée des sessions..."
        }
      ],
      "references": [
        {
          "type_texte": "Vu",
          "reference": "la loi constitutionnelle n° 1 du 28 novembre 1958"
        }
      ],
      "signataires": [
        {
          "nom": "Abbe F. Youlou",
          "fonction": "Premier Ministre",
          "pour": "Par le Premier Ministre"
        }
      ]
    }
  ]
}
```

### Types de textes extraits

Le convertisseur identifie et extrait les types suivants :

- **LOI** : Lois ordinaires
- **LOI_CONSTITUTIONNELLE** : Lois constitutionnelles
- **DECRET** : Décrets
- **ARRETE** : Arrêtés
- **CONVENTION** : Conventions internationales
- **DELIBERATION** : Délibérations
- **DECISION** : Décisions
- **INSTRUCTION** : Instructions
- **ORDONNANCE** : Ordonnances
- **PROCLAMATION** : Proclamations
- **DISCOURS** : Discours officiels

## 🔍 Fonctionnalités d'extraction

Le script extrait automatiquement :

### 1. Métadonnées du texte
- Type de texte (LOI, DECRET, etc.)
- Numéro du texte
- Date de signature
- Titre complet

### 2. Structure du texte
- **Articles** : Tous les articles avec leur numéro et contenu
- **Références** : Textes cités (Vu la loi..., Vu le décret...)
- **Signataires** : Personnes ayant signé le texte avec leurs fonctions

### 3. Normalisation des données
- Dates converties au format ISO (YYYY-MM-DD)
- Numéros standardisés
- IDs uniques générés automatiquement

## 📈 Statistiques de conversion

Après chaque conversion complète, un fichier `_conversion_stats.json` est généré dans le répertoire de sortie avec :

- Nombre total de fichiers traités
- Nombre total de textes extraits
- Répartition par type de texte
- Liste des fichiers traités

Exemple :
```json
{
  "total_fichiers": 7,
  "total_textes": 156,
  "types_textes": {
    "LOI": 45,
    "DECRET": 67,
    "ARRETE": 34,
    "CONVENTION": 10
  },
  "fichiers_traites": ["congo-jo-1958-01.md", ...]
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

### Patterns d'extraction

Le script utilise des expressions régulières sophistiquées pour détecter :

```python
# Exemples de patterns
'loi': r'LOI\s+(?:N°|n°|No)\s*([\d/-]+)\s+(?:DU|du)\s+([^\n]+)'
'article': r'^(?:Art\.|ART\.|Article)\s*(\d+(?:er|ème|°)?)\s*\.?'
'date': r'(\d{1,2})\s+(janvier|février|...|décembre)\s+(\d{4})'
```

## 🎨 Améliorations futures

- [ ] Extraction des tableaux (tarifs, budgets)
- [ ] Détection des annexes
- [ ] Extraction des préambules
- [x] OCR intégré pour les PDFs scannés
- [ ] Interface web de consultation
- [ ] API REST pour accès mobile
- [ ] Base de données SQLite(mobile)/PostgreSQL(web)
- [ ] Moteur de recherche full-text

## 📱 Utilisation mobile

Les fichiers JSON générés peuvent être :

1. **Intégrés dans une app mobile** (React Native, Flutter)
2. **Servis via une API REST**
3. **Stockés localement** pour consultation hors-ligne
4. **Indexés** pour recherche rapide

## 🤝 Contribution

Ce projet vise à améliorer l'accès à la justice au Congo-Brazzaville. Toute contribution est bienvenue :

- Amélioration des regex d'extraction
- Ajout de nouveaux types de documents
- Correction des erreurs d'extraction
- Interface utilisateur
- Documentation

## 📄 Licence

Ce projet est destiné à servir l'intérêt public en facilitant l'accès aux textes de loi.

## 📞 Contact

Pour toute question ou suggestion d'amélioration, n'hésitez pas à contribuer!

---

**Fait avec ❤️ pour rendre la justice accessible à tous les Congolais**
