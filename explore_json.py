#!/usr/bin/env python3
"""
Utilitaire pour explorer les fichiers JSON générés
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import sys


class JsonExplorer:
    """Explorateur de fichiers JSON des textes de loi"""
    
    def __init__(self, json_dir: str = 'data/json'):
        self.json_dir = Path(json_dir)
        
    def list_publications(self) -> List[Dict[str, Any]]:
        """Liste toutes les publications disponibles"""
        publications = []
        
        for json_file in self.json_dir.glob('*.json'):
            if json_file.name.startswith('_'):
                continue
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                publications.append({
                    'fichier': json_file.name,
                    'id': data['id'],
                    'numero': data['numero_parution'],
                    'annee': data['annee'],
                    'nb_textes': len(data['textes'])
                })
        
        return sorted(publications, key=lambda x: (x['annee'], int(x['numero'])))
    
    def search_by_type(self, type_texte: str) -> List[Dict[str, Any]]:
        """Recherche tous les textes d'un type donné"""
        results = []
        
        for json_file in self.json_dir.glob('*.json'):
            if json_file.name.startswith('_'):
                continue
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for texte in data['textes']:
                    if texte['type_texte'].upper() == type_texte.upper():
                        results.append({
                            'publication': data['id'],
                            'id': texte['id'],
                            'type': texte['type_texte'],
                            'numero': texte['numero'],
                            'date': texte['date'],
                            'titre': texte['titre'][:100] + '...' if len(texte['titre']) > 100 else texte['titre']
                        })
        
        return results
    
    def search_by_year(self, year: int) -> List[Dict[str, Any]]:
        """Recherche tous les textes d'une année donnée"""
        results = []
        
        for json_file in self.json_dir.glob(f'*{year}*.json'):
            if json_file.name.startswith('_'):
                continue
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for texte in data['textes']:
                    results.append({
                        'publication': data['id'],
                        'id': texte['id'],
                        'type': texte['type_texte'],
                        'numero': texte['numero'],
                        'date': texte['date'],
                        'titre': texte['titre'][:80] + '...' if len(texte['titre']) > 80 else texte['titre']
                    })
        
        return results
    
    def search_by_keyword(self, keyword: str) -> List[Dict[str, Any]]:
        """Recherche par mot-clé dans les titres et contenus"""
        results = []
        keyword_lower = keyword.lower()
        
        for json_file in self.json_dir.glob('*.json'):
            if json_file.name.startswith('_'):
                continue
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for texte in data['textes']:
                    # Chercher dans le titre
                    if keyword_lower in texte['titre'].lower():
                        results.append({
                            'publication': data['id'],
                            'id': texte['id'],
                            'type': texte['type_texte'],
                            'numero': texte['numero'],
                            'date': texte['date'],
                            'titre': texte['titre'][:80] + '...',
                            'match': 'titre'
                        })
                    # Chercher dans le contenu
                    elif keyword_lower in texte['contenu'].lower():
                        results.append({
                            'publication': data['id'],
                            'id': texte['id'],
                            'type': texte['type_texte'],
                            'numero': texte['numero'],
                            'date': texte['date'],
                            'titre': texte['titre'][:80] + '...',
                            'match': 'contenu'
                        })
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtient les statistiques globales"""
        stats_file = self.json_dir / '_conversion_stats.json'
        
        if stats_file.exists():
            with open(stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return {}
    
    def display_texte(self, texte_id: str):
        """Affiche un texte complet par son ID"""
        for json_file in self.json_dir.glob('*.json'):
            if json_file.name.startswith('_'):
                continue
            
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                for texte in data['textes']:
                    if texte['id'] == texte_id:
                        self.print_texte(texte)
                        return
        
        print(f"❌ Texte non trouvé: {texte_id}")
    
    def print_texte(self, texte: Dict[str, Any]):
        """Affiche un texte formaté"""
        print("\n" + "="*80)
        print(f"TYPE: {texte['type_texte']}")
        if texte['numero']:
            print(f"NUMÉRO: {texte['numero']}")
        if texte['date']:
            print(f"DATE: {texte['date']}")
        print(f"\nTITRE: {texte['titre']}")
        print("="*80)
        
        # Références
        if texte['references']:
            print("\n📚 RÉFÉRENCES:")
            for ref in texte['references']:
                print(f"  • {ref['type_texte']}: {ref['reference']}")
        
        # Articles
        if texte['articles']:
            print(f"\n📋 ARTICLES ({len(texte['articles'])}):")
            for art in texte['articles']:
                print(f"\n  Article {art['numero']}:")
                content = art['contenu'][:200] + '...' if len(art['contenu']) > 200 else art['contenu']
                for line in content.split('\n'):
                    print(f"    {line}")
        
        # Signataires
        if texte['signataires']:
            print("\n✍️  SIGNATAIRES:")
            for sig in texte['signataires']:
                print(f"  • {sig['nom']}")
                if sig['fonction']:
                    print(f"    {sig['fonction']}")
        
        print("\n" + "="*80 + "\n")


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Explorateur de textes de loi du Congo-Brazzaville"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')
    
    # Commande: list
    list_parser = subparsers.add_parser('list', help='Liste toutes les publications')
    
    # Commande: search
    search_parser = subparsers.add_parser('search', help='Recherche de textes')
    search_parser.add_argument('--type', help='Type de texte (LOI, DECRET, etc.)')
    search_parser.add_argument('--year', type=int, help='Année')
    search_parser.add_argument('--keyword', help='Mot-clé')
    
    # Commande: show
    show_parser = subparsers.add_parser('show', help='Affiche un texte complet')
    show_parser.add_argument('texte_id', help='ID du texte')
    
    # Commande: stats
    stats_parser = subparsers.add_parser('stats', help='Affiche les statistiques')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    explorer = JsonExplorer()
    
    if args.command == 'list':
        publications = explorer.list_publications()
        print(f"\n📚 {len(publications)} publications disponibles:\n")
        print(f"{'Année':<6} {'N°':<4} {'Textes':<8} {'Fichier'}")
        print("-" * 60)
        for pub in publications:
            print(f"{pub['annee']:<6} {pub['numero']:<4} {pub['nb_textes']:<8} {pub['fichier']}")
        print()
    
    elif args.command == 'search':
        if args.type:
            results = explorer.search_by_type(args.type)
            print(f"\n🔍 {len(results)} textes de type '{args.type}' trouvés:\n")
        elif args.year:
            results = explorer.search_by_year(args.year)
            print(f"\n🔍 {len(results)} textes de l'année {args.year} trouvés:\n")
        elif args.keyword:
            results = explorer.search_by_keyword(args.keyword)
            print(f"\n🔍 {len(results)} textes contenant '{args.keyword}' trouvés:\n")
        else:
            print("❌ Veuillez spécifier --type, --year ou --keyword")
            return
        
        if results:
            for i, result in enumerate(results, 1):
                print(f"{i}. [{result['type']}] {result['numero'] or 'N/A'} - {result['date'] or 'N/A'}")
                print(f"   {result['titre']}")
                print(f"   ID: {result['id']}\n")
    
    elif args.command == 'show':
        explorer.display_texte(args.texte_id)
    
    elif args.command == 'stats':
        stats = explorer.get_statistics()
        if stats:
            print("\n" + "="*60)
            print("📊 STATISTIQUES")
            print("="*60)
            print(f"Fichiers traités: {stats['total_fichiers']}")
            print(f"Textes extraits:  {stats['total_textes']}")
            print(f"\nRépartition par type:")
            for type_texte, count in sorted(stats['types_textes'].items(), key=lambda x: -x[1]):
                print(f"  • {type_texte:25s}: {count:4d}")
            print("="*60 + "\n")
        else:
            print("❌ Fichier de statistiques non trouvé")


if __name__ == '__main__':
    main()
