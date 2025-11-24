# Guide d'utilisation rapide

## 🚀 Conversion MD → JSON

### Convertir tous les fichiers
```bash
python3 md_to_json_converter.py
```

### Convertir un fichier spécifique
```bash
python3 md_to_json_converter.py --file congo-jo-1959-02.md
```

### Personnaliser les répertoires
```bash
python3 md_to_json_converter.py \
  --input data/processed \
  --output data/json
```

## 🔍 Explorer les fichiers JSON

### Lister toutes les publications
```bash
python3 explore_json.py list
```

### Rechercher par type de texte
```bash
python3 explore_json.py search --type LOI
python3 explore_json.py search --type DECRET
python3 explore_json.py search --type LOI_CONSTITUTIONNELLE
```

### Rechercher par année
```bash
python3 explore_json.py search --year 1959
```

### Rechercher par mot-clé
```bash
python3 explore_json.py search --keyword "République"
python3 explore_json.py search --keyword "ministre"
```

### Afficher un texte complet
```bash
python3 explore_json.py show congo-jo-1959-02-loi-3-58
```

### Voir les statistiques
```bash
python3 explore_json.py stats
```

## 📊 Exemples de requêtes

```bash
# Toutes les lois constitutionnelles
python3 explore_json.py search --type LOI_CONSTITUTIONNELLE

# Tous les textes de 1958
python3 explore_json.py search --year 1958

# Rechercher "budget"
python3 explore_json.py search --keyword budget

# Rechercher "nomination"
python3 explore_json.py search --keyword nomination
```

## 📁 Structure des fichiers générés

```
data/json/
├── congo-jo-1958-01.json          # Journal Officiel n°01/1958
├── congo-jo-1959-02.json          # Journal Officiel n°02/1959
├── ...
└── _conversion_stats.json         # Statistiques de conversion
```

## 🔗 Utilisation dans votre application

### Python

```python
import json

# Charger un fichier JSON
with open('data/json/congo-jo-1959-02.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Parcourir les textes
for texte in data['textes']:
    print(f"{texte['type_texte']}: {texte['titre']}")
    
    # Afficher les articles
    for article in texte['articles']:
        print(f"  Article {article['numero']}: {article['contenu'][:100]}...")
```

### JavaScript / Node.js

```javascript
const fs = require('fs');

// Charger un fichier JSON
const data = JSON.parse(
  fs.readFileSync('data/json/congo-jo-1959-02.json', 'utf8')
);

// Parcourir les textes
data.textes.forEach(texte => {
  console.log(`${texte.type_texte}: ${texte.titre}`);
  
  // Afficher les articles
  texte.articles.forEach(article => {
    console.log(`  Article ${article.numero}: ${article.contenu.substring(0, 100)}...`);
  });
});
```

### React Native / Flutter

Les fichiers JSON peuvent être :
- Embarqués dans l'app
- Servis via une API
- Stockés localement pour consultation offline

## 🎯 Prochaines étapes

1. **Base de données** : Importer les JSON dans SQLite/PostgreSQL
2. **API REST** : Créer une API pour servir les données
3. **Application mobile** : Interface de consultation
4. **Recherche full-text** : Indexation pour recherche rapide
5. **Export PDF** : Générer des PDFs formatés

## 💡 Astuces

### Compter les textes par type
```bash
python3 -c "
import json
stats = json.load(open('data/json/_conversion_stats.json'))
for t, c in sorted(stats['types_textes'].items(), key=lambda x: -x[1]):
    print(f'{t:25s}: {c:4d}')
"
```

### Extraire tous les titres de lois
```bash
python3 -c "
import json
from pathlib import Path

for f in Path('data/json').glob('*.json'):
    if f.name.startswith('_'): continue
    data = json.load(open(f))
    for t in data['textes']:
        if t['type_texte'] == 'LOI':
            print(f'{t['numero']}: {t['titre'][:60]}...')
"
```

## 🐛 Dépannage

### Problème: "Command not found: python"
**Solution**: Utiliser `python3` au lieu de `python`

### Problème: Erreur d'encodage
**Solution**: Vérifier que les fichiers MD sont en UTF-8

### Problème: Pas de textes extraits
**Solution**: Vérifier que les fichiers MD sont dans `data/processed/`
