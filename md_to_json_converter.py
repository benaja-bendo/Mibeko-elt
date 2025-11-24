#!/usr/bin/env python3
"""
Convertisseur de fichiers Markdown (Journaux Officiels) vers JSON
Ce script extrait les textes de loi, décrets, arrêtés et autres documents
des fichiers MD et les structure en JSON pour faciliter l'accès mobile.
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import sys


@dataclass
class Article:
    """Représente un article d'un texte de loi"""
    numero: str
    contenu: str
    
    
@dataclass
class Signataire:
    """Représente un signataire d'un texte"""
    nom: str
    fonction: Optional[str] = None
    pour: Optional[str] = None  # "Pour le Premier Ministre", etc.


@dataclass
class Reference:
    """Représente une référence à un autre texte"""
    type_texte: str  # "Vu", "Conformément à", etc.
    reference: str
    

@dataclass
class TexteLegal:
    """Représente un texte légal (loi, décret, arrêté, etc.)"""
    id: str  # Identifiant unique généré
    type_texte: str  # LOI, DECRET, ARRETE, CONVENTION, etc.
    numero: Optional[str] = None
    date: Optional[str] = None
    titre: str = ""
    contenu: str = ""
    articles: List[Article] = None
    references: List[Reference] = None
    signataires: List[Signataire] = None
    preambule: Optional[str] = None
    page_debut: Optional[int] = None
    
    def __post_init__(self):
        if self.articles is None:
            self.articles = []
        if self.references is None:
            self.references = []
        if self.signataires is None:
            self.signataires = []


@dataclass
class Publication:
    """Représente une publication du Journal Officiel"""
    id: str  # Ex: "congo-jo-1959-02"
    numero_parution: str
    date_parution: Optional[str] = None
    annee: Optional[int] = None
    titre: str = "JOURNAL OFFICIEL DE LA RÉPUBLIQUE DU CONGO"
    textes: List[TexteLegal] = None
    
    def __post_init__(self):
        if self.textes is None:
            self.textes = []


class MarkdownToJsonConverter:
    """Convertisseur de fichiers MD vers JSON"""
    
    # Patterns regex pour l'extraction
    PATTERNS = {
        'loi': r'LOI\s+(?:N°|n°|No)\s*([\d/-]+)\s+(?:DU|du)\s+([^\n]+)',
        'decret': r'DECRET\s+(?:N°|n°|No)\s*([\d/-]+)\s+(?:DU|du)\s+([^\n]+)',
        'arrete': r'ARRETE\s+(?:N°|n°|No)\s*([\d/-]+)\s+(?:DU|du)\s+([^\n]+)',
        'convention': r'Convention\s+([^\n]+)',
        'deliberation': r'DELIBERATION\s+(?:N°|n°|No)\s*([\d/-]+)',
        'article': r'^(?:Art\.|ART\.|Article)\s*(\d+(?:er|ème|°)?)\s*\.?\s*[—–-]?\s*(.+?)(?=(?:^(?:Art\.|ART\.|Article)\s*\d+|$))',
        'reference': r'^(?:Vu|VU)\s+(.+?)(?:;|,|\n)',
        'date': r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})',
    }
    
    def __init__(self, input_dir: Path, output_dir: Path):
        """
        Initialise le convertisseur
        
        Args:
            input_dir: Répertoire contenant les fichiers .md
            output_dir: Répertoire de sortie pour les fichiers .json
        """
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def extract_publication_info(self, filename: str, content: str) -> Dict[str, Any]:
        """Extrait les informations de base de la publication"""
        # Pattern du nom de fichier: congo-jo-YYYY-NN.md
        match = re.match(r'congo-jo-(\d{4})-(\d+)\.md', filename)
        if match:
            annee, numero = match.groups()
            return {
                'id': filename.replace('.md', ''),
                'numero_parution': numero,
                'annee': int(annee),
                'date_parution': None  # À extraire du contenu si disponible
            }
        return {
            'id': filename.replace('.md', ''),
            'numero_parution': 'inconnu',
            'annee': None
        }
    
    def detect_texte_type(self, section: str) -> Optional[str]:
        """Détecte le type de texte (LOI, DECRET, ARRETE, etc.)"""
        section_upper = section.upper()
        
        # Ordre d'importance pour la détection
        types = [
            ('LOI CONSTITUTIONNELLE', 'LOI_CONSTITUTIONNELLE'),
            ('LOI', 'LOI'),
            ('DECRET', 'DECRET'),
            ('ARRETE', 'ARRETE'),
            ('CONVENTION', 'CONVENTION'),
            ('DELIBERATION', 'DELIBERATION'),
            ('DECISION', 'DECISION'),
            ('INSTRUCTION', 'INSTRUCTION'),
            ('ORDONNANCE', 'ORDONNANCE'),
            ('PROCLAMATION', 'PROCLAMATION'),
            ('DISCOURS', 'DISCOURS'),
        ]
        
        for keyword, type_name in types:
            if keyword in section_upper:
                return type_name
        
        return None
    
    def extract_numero_date(self, text: str, type_texte: str) -> tuple[Optional[str], Optional[str]]:
        """Extrait le numéro et la date d'un texte"""
        numero = None
        date = None
        
        # Pattern pour numéro
        if type_texte in ['LOI', 'LOI_CONSTITUTIONNELLE']:
            match = re.search(self.PATTERNS['loi'], text, re.IGNORECASE)
        elif type_texte == 'DECRET':
            match = re.search(self.PATTERNS['decret'], text, re.IGNORECASE)
        elif type_texte == 'ARRETE':
            match = re.search(self.PATTERNS['arrete'], text, re.IGNORECASE)
        else:
            match = None
            
        if match:
            numero = match.group(1).strip()
            date_str = match.group(2).strip() if len(match.groups()) > 1 else None
            
            # Nettoyer et standardiser la date
            if date_str:
                date = self.normalize_date(date_str)
        
        return numero, date
    
    def normalize_date(self, date_str: str) -> Optional[str]:
        """Normalise les dates au format ISO (YYYY-MM-DD)"""
        # Pattern: "20 décembre 1958" ou "20 DECEMBRE 1958"
        mois_mapping = {
            'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
            'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
            'août': '08', 'aout': '08', 'septembre': '09', 'octobre': '10',
            'novembre': '11', 'décembre': '12', 'decembre': '12'
        }
        
        match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str, re.IGNORECASE)
        if match:
            jour, mois, annee = match.groups()
            mois_lower = mois.lower()
            if mois_lower in mois_mapping:
                return f"{annee}-{mois_mapping[mois_lower]}-{jour.zfill(2)}"
        
        return date_str
    
    def extract_articles(self, text: str) -> List[Article]:
        """Extrait les articles d'un texte"""
        articles = []
        
        # Split par lignes pour chercher les articles
        lines = text.split('\n')
        current_article = None
        current_content = []
        
        for line in lines:
            # Vérifier si c'est un nouvel article
            article_match = re.match(
                r'^\s*(?:Art\.|ART\.|Article)\s*(\d+(?:er|ème|°|re)?)\s*\.?\s*[—–-]?\s*(.*)$',
                line,
                re.IGNORECASE
            )
            
            if article_match:
                # Sauvegarder l'article précédent
                if current_article:
                    articles.append(Article(
                        numero=current_article,
                        contenu='\n'.join(current_content).strip()
                    ))
                
                # Démarrer un nouvel article
                current_article = article_match.group(1)
                current_content = [article_match.group(2)] if article_match.group(2) else []
            elif current_article:
                # Continuer l'article en cours
                current_content.append(line)
        
        # Ajouter le dernier article
        if current_article:
            articles.append(Article(
                numero=current_article,
                contenu='\n'.join(current_content).strip()
            ))
        
        return articles
    
    def extract_references(self, text: str) -> List[Reference]:
        """Extrait les références à d'autres textes (Vu, Conformément à, etc.)"""
        references = []
        
        # Chercher les "Vu"
        vu_pattern = r'^(?:Vu|VU)\s+(.+?)(?=(?:^(?:Vu|VU|Art)|$))'
        matches = re.finditer(vu_pattern, text, re.MULTILINE | re.DOTALL)
        
        for match in matches:
            ref_text = match.group(1).strip()
            # Nettoyer (enlever ; ou , en fin)
            ref_text = re.sub(r'[;,]\s*$', '', ref_text)
            references.append(Reference(
                type_texte="Vu",
                reference=ref_text
            ))
        
        return references
    
    def extract_signataires(self, text: str) -> List[Signataire]:
        """Extrait les signataires d'un texte"""
        signataires = []
        
        # Patterns courants
        patterns = [
            r'(?:Par le|Pour le)\s+(.+?)\s*:\s*\n\s*(.+)',
            r'Le\s+(.+?)\s*,?\s*\n\s*(.+)',
            r'Fait\s+à\s+.+?,\s+le\s+.+?\.\s*\n\s*(.+)',
        ]
        
        # Chercher "Par le Premier Ministre :"
        par_pattern = r'(?:Par le|Pour le)\s+([^\n:]+)\s*:\s*\n\s*(?:Le\s+)?([^\n]+)'
        matches = re.finditer(par_pattern, text, re.MULTILINE)
        
        for match in matches:
            fonction = match.group(1).strip()
            nom = match.group(2).strip()
            
            signataires.append(Signataire(
                nom=nom,
                fonction=fonction,
                pour=f"Par le {fonction}" if "Par le" in match.group(0) else None
            ))
        
        # Chercher signature directe "Abbe F. Youlou" etc.
        signature_pattern = r'(?:Fait\s+à\s+[^,]+,\s+le\s+[^\n]+\.\s*\n\s*(.+)|^([A-Z][a-z]+(?:\s+[A-Z]\.?\s+)?[A-Z][a-z]+)\s*\.?\s*$)'
        
        return signataires
    
    def split_into_sections(self, content: str) -> List[tuple[str, str]]:
        """Découpe le contenu en sections basées sur les titres de niveau 1 (#)"""
        sections = []
        current_title = ""
        current_content = []
        
        lines = content.split('\n')
        
        for line in lines:
            # Vérifier si c'est un titre de niveau 1
            if line.startswith('# ') and not line.startswith('##'):
                # Sauvegarder la section précédente
                if current_title or current_content:
                    sections.append((
                        current_title,
                        '\n'.join(current_content).strip()
                    ))
                
                # Démarrer nouvelle section
                current_title = line[2:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Ajouter la dernière section
        if current_title or current_content:
            sections.append((
                current_title,
                '\n'.join(current_content).strip()
            ))
        
        return sections
    
    def parse_texte(self, title: str, content: str, publication_id: str, index: int) -> Optional[TexteLegal]:
        """Parse une section en TexteLegal"""
        type_texte = self.detect_texte_type(title + '\n' + content[:500])
        
        if not type_texte:
            return None
        
        numero, date = self.extract_numero_date(title + '\n' + content[:300], type_texte)
        articles = self.extract_articles(content)
        references = self.extract_references(content)
        signataires = self.extract_signataires(content)
        
        # Générer un ID unique
        if numero:
            texte_id = f"{publication_id}-{type_texte.lower()}-{numero.replace('/', '-')}"
        else:
            texte_id = f"{publication_id}-{type_texte.lower()}-{index}"
        
        return TexteLegal(
            id=texte_id,
            type_texte=type_texte,
            numero=numero,
            date=date,
            titre=title,
            contenu=content,
            articles=articles,
            references=references,
            signataires=signataires
        )
    
    def convert_file(self, md_file: Path) -> Dict[str, Any]:
        """Convertit un fichier MD en structure JSON"""
        print(f"📄 Traitement de {md_file.name}...")
        
        # Lire le fichier
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraire les infos de publication
        pub_info = self.extract_publication_info(md_file.name, content)
        publication = Publication(**pub_info)
        
        # Découper en sections
        sections = self.split_into_sections(content)
        
        # Parser chaque section
        for index, (title, section_content) in enumerate(sections):
            if not title or not section_content:
                continue
            
            texte = self.parse_texte(title, section_content, publication.id, index)
            if texte:
                publication.textes.append(texte)
        
        print(f"   ✓ {len(publication.textes)} textes extraits")
        
        return self.to_json_dict(publication)
    
    def to_json_dict(self, publication: Publication) -> Dict[str, Any]:
        """Convertit une Publication en dictionnaire JSON serializable"""
        result = {
            'id': publication.id,
            'numero_parution': publication.numero_parution,
            'date_parution': publication.date_parution,
            'annee': publication.annee,
            'titre': publication.titre,
            'textes': []
        }
        
        for texte in publication.textes:
            texte_dict = {
                'id': texte.id,
                'type_texte': texte.type_texte,
                'numero': texte.numero,
                'date': texte.date,
                'titre': texte.titre,
                'contenu': texte.contenu,
                'articles': [
                    {'numero': art.numero, 'contenu': art.contenu}
                    for art in texte.articles
                ],
                'references': [
                    {'type_texte': ref.type_texte, 'reference': ref.reference}
                    for ref in texte.references
                ],
                'signataires': [
                    {'nom': sig.nom, 'fonction': sig.fonction, 'pour': sig.pour}
                    for sig in texte.signataires
                ]
            }
            result['textes'].append(texte_dict)
        
        return result
    
    def convert_all(self, generate_stats: bool = True):
        """Convertit tous les fichiers MD du répertoire d'entrée"""
        md_files = list(self.input_dir.glob('*.md'))
        
        if not md_files:
            print(f"❌ Aucun fichier .md trouvé dans {self.input_dir}")
            return
        
        print(f"\n🚀 Conversion de {len(md_files)} fichiers MD vers JSON")
        print(f"📂 Entrée:  {self.input_dir}")
        print(f"📂 Sortie:  {self.output_dir}\n")
        
        stats = {
            'total_fichiers': len(md_files),
            'total_textes': 0,
            'types_textes': {},
            'fichiers_traites': []
        }
        
        for md_file in md_files:
            try:
                result = self.convert_file(md_file)
                
                # Sauvegarder en JSON
                output_file = self.output_dir / f"{md_file.stem}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                # Mise à jour des stats
                stats['total_textes'] += len(result['textes'])
                stats['fichiers_traites'].append(md_file.name)
                
                for texte in result['textes']:
                    type_t = texte['type_texte']
                    stats['types_textes'][type_t] = stats['types_textes'].get(type_t, 0) + 1
                
                print(f"   ✓ Sauvegardé: {output_file.name}\n")
                
            except Exception as e:
                print(f"   ❌ Erreur: {e}\n")
                continue
        
        # Afficher les statistiques
        if generate_stats:
            self.print_stats(stats)
            
            # Sauvegarder les stats
            stats_file = self.output_dir / '_conversion_stats.json'
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, ensure_ascii=False, indent=2)
    
    def print_stats(self, stats: Dict[str, Any]):
        """Affiche les statistiques de conversion"""
        print("\n" + "="*60)
        print("📊 STATISTIQUES DE CONVERSION")
        print("="*60)
        print(f"Fichiers traités: {stats['total_fichiers']}")
        print(f"Textes extraits:  {stats['total_textes']}")
        print(f"\nRépartition par type de texte:")
        for type_texte, count in sorted(stats['types_textes'].items(), key=lambda x: -x[1]):
            print(f"  • {type_texte:25s}: {count:4d}")
        print("="*60 + "\n")


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Convertit les fichiers MD (Journaux Officiels) en JSON structuré"
    )
    parser.add_argument(
        '--input',
        '-i',
        type=str,
        default='data/processed',
        help='Répertoire contenant les fichiers .md (défaut: data/processed)'
    )
    parser.add_argument(
        '--output',
        '-o',
        type=str,
        default='data/json',
        help='Répertoire de sortie pour les fichiers .json (défaut: data/json)'
    )
    parser.add_argument(
        '--file',
        '-f',
        type=str,
        help='Convertir un seul fichier spécifique'
    )
    
    args = parser.parse_args()
    
    # Créer le convertisseur
    converter = MarkdownToJsonConverter(
        input_dir=Path(args.input),
        output_dir=Path(args.output)
    )
    
    # Convertir
    if args.file:
        # Convertir un seul fichier
        md_file = Path(args.input) / args.file
        if not md_file.exists():
            print(f"❌ Fichier non trouvé: {md_file}")
            sys.exit(1)
        
        result = converter.convert_file(md_file)
        output_file = Path(args.output) / f"{md_file.stem}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Conversion terminée: {output_file}")
    else:
        # Convertir tous les fichiers
        converter.convert_all()
        print("✅ Conversion terminée avec succès!")


if __name__ == '__main__':
    main()
