# Architecture du système ETL

## 📊 Vue d'ensemble

```
┌──────────────┐
│ PDFs scannés │
│  (papier)    │
└──────┬───────┘
       │
       │ OCR / MinerU
       ▼
┌──────────────┐
│ Fichiers .md │  ◄── Vous êtes ici
│ (processed)  │
└──────┬───────┘
       │
       │ md_to_json_converter.py
       ▼
┌──────────────┐
│ Fichiers    │
│   .json     │
└──────┬───────┘
       │
       ├─────► Base de données (PostgreSQL)
       │
       ├─────► API REST
       │
       ├─────► Application Mobile
       │
       └─────► Interface Web
```

## 🔄 Flux de transformation

### 1. Extraction (E)
```
Fichier MD → Parser Markdown → Sections
```

### 2. Transformation (T)
```
Sections → Détection type texte → TexteLegal
         → Extraction articles
         → Extraction références  
         → Extraction signataires
         → Normalisation dates
```

### 3. Load (L)
```
TexteLegal → JSON structuré → Fichier .json
```

## 🏗️ Structure des données

### Hiérarchie
```
Publication (Journal Officiel)
  ├── Métadonnées
  │   ├── ID
  │   ├── Numéro
  │   ├── Année
  │   └── Date
  │
  └── Textes [] (Array)
      ├── TexteLegal 1
      │   ├── Type (LOI, DECRET, etc.)
      │   ├── Numéro
      │   ├── Date
      │   ├── Titre
      │   ├── Contenu
      │   ├── Articles []
      │   ├── Références []
      │   └── Signataires []
      │
      ├── TexteLegal 2
      └── ...
```

### Modèle de données

```python
@dataclass
class Article:
    numero: str          # "1er", "2", "3"
    contenu: str         # Texte de l'article

@dataclass
class Reference:
    type_texte: str      # "Vu", "Conformément à"
    reference: str       # Texte de référence

@dataclass
class Signataire:
    nom: str            # "Abbé Fulbert Youlou"
    fonction: str       # "Premier Ministre"
    pour: str           # "Par le Premier Ministre"

@dataclass
class TexteLegal:
    id: str             # Unique identifier
    type_texte: str     # LOI, DECRET, ARRETE...
    numero: str         # "3/58", "59-191"
    date: str           # "1959-12-29" (ISO)
    titre: str
    contenu: str
    articles: List[Article]
    references: List[Reference]
    signataires: List[Signataire]

@dataclass
class Publication:
    id: str             # "congo-jo-1959-02"
    numero_parution: str # "02"
    annee: int          # 1959
    textes: List[TexteLegal]
```

## 🎯 Étapes suivantes (Roadmap)

### Phase 1: Base de données ✅
```sql
CREATE TABLE publications (
    id TEXT PRIMARY KEY,
    numero_parution TEXT,
    annee INTEGER,
    date_parution DATE
);

CREATE TABLE textes (
    id TEXT PRIMARY KEY,
    publication_id TEXT,
    type_texte TEXT,
    numero TEXT,
    date DATE,
    titre TEXT,
    contenu TEXT,
    FOREIGN KEY (publication_id) REFERENCES publications(id)
);

CREATE TABLE articles (
    id INTEGER PRIMARY KEY,
    texte_id TEXT,
    numero TEXT,
    contenu TEXT,
    FOREIGN KEY (texte_id) REFERENCES textes(id)
);
```

### Phase 2: API REST
```
GET /api/publications           # Liste des publications
GET /api/publications/:id       # Une publication
GET /api/textes                 # Tous les textes
GET /api/textes/:id            # Un texte
GET /api/search?q=keyword      # Recherche
GET /api/stats                  # Statistiques
```

### Phase 3: Application Mobile
```
- Interface de navigation
- Recherche full-text
- Favoris / Bookmarks
- Mode offline
- Partage de textes
```

## 📈 Métriques actuelles

- **7 publications** converties
- **264 textes** extraits
- **Types identifiés**: 11 types différents
- **Articles**: Centaines d'articles structurés
- **Références**: Centaines de références croisées

## 🔍 Qualité des données

### ✅ Bien extrait
- Types de textes (LOI, DECRET, etc.)
- Numéros et dates
- Articles numérotés
- Références "Vu"
- Structure hiérarchique

### ⚠️ À améliorer
- Extraction des signataires (parsing plus sophistiqué)
- Détection des tableaux
- Extraction des préambules
- Normalisation des dates (quelques formats à ajouter)
- Détection des annexes

## 🛠️ Technologies

### Backend
- Python 3.8+
- Bibliothèque standard (pas de dépendances)
- Regex pour parsing
- JSON pour stockage

### Frontend (futur)
- React / React Native pour mobile
- Node.js pour API
- SQLite/PostgreSQL pour base de données
- Elasticsearch pour recherche full-text

## 📝 Notes d'implémentation

### Patterns de détection optimisés
```python
# Détection robuste des types
'loi': r'LOI\s+(?:N°|n°|No)\s*([\d/-]+)\s+(?:DU|du)\s+([^\n]+)'

# Articles avec variations
'article': r'^(?:Art\.|ART\.|Article)\s*(\d+(?:er|ème|°)?)\s*\.?'

# Dates en français
'date': r'(\d{1,2})\s+(janvier|février|...|décembre)\s+(\d{4})'
```

### Normalisation des données
- Dates → ISO 8601 (YYYY-MM-DD)
- IDs → Format standardisé
- Types → Énumération stricte
- Structure → Hiérarchique cohérente

## 🎓 Apprentissages

1. **Regex complexes** pour textes juridiques
2. **Structure de données** adaptée au domaine
3. **Normalisation** essentielle pour exploitation
4. **Extraction hiérarchique** (Publication → Texte → Article)
5. **Métadonnées riches** pour recherche efficace
