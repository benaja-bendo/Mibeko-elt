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
    intitule: Optional[str] = None  # Titre de l'article si présent


@dataclass
class Section:
    """Représente une section dans un chapitre"""
    numero: Optional[str]  # "I", "II", "Section 1"
    titre: str
    articles: List[Article] = None
    contenu_libre: Optional[str] = None  # Texte avant les articles
    
    def __post_init__(self):
        if self.articles is None:
            self.articles = []


@dataclass
class Chapitre:
    """Représente un chapitre dans un titre"""
    numero: Optional[str]  # "1", "2", "Chapitre premier"
    titre: str
    articles: List[Article] = None
    sections: List[Section] = None
    contenu_libre: Optional[str] = None
    
    def __post_init__(self):
        if self.articles is None:
            self.articles = []
        if self.sections is None:
            self.sections = []


@dataclass
class Titre:
    """Représente un titre dans une loi (TITRE I, TITRE II, etc.)"""
    numero: Optional[str]  # "I", "II", "III"
    intitule: str  # Ex: "DISPOSITIONS GENERALES"
    chapitres: List[Chapitre] = None
    articles: List[Article] = None  # Articles directs sans chapitre
    contenu_libre: Optional[str] = None  # Texte d'introduction
    
    def __post_init__(self):
        if self.chapitres is None:
            self.chapitres = []
        if self.articles is None:
            self.articles = []


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
class Structure:
    """Structure hiérarchique complète d'un texte légal"""
    titres: List[Titre] = None
    chapitres: List[Chapitre] = None  # Si pas de titres
    sections: List[Section] = None  # Si pas de chapitres
    articles: List[Article] = None  # Articles directs
    
    def __post_init__(self):
        if self.titres is None:
            self.titres = []
        if self.chapitres is None:
            self.chapitres = []
        if self.sections is None:
            self.sections = []
        if self.articles is None:
            self.articles = []
    

@dataclass
class TexteLegal:
    """Représente un texte légal (loi, décret, arrêté, etc.)"""
    id: str  # Identifiant unique généré
    type_texte: str  # LOI, DECRET, ARRETE, etc.
    numero: Optional[str] = None
    date: Optional[str] = None
    titre: str = ""
    preambule: Optional[str] = None  # "L'Assemblée nationale...", "Le Président promulgue..."
    structure: Optional[Structure] = None  # Structure hiérarchique
    references: List[Reference] = None
    signataires: List[Signataire] = None
    page_debut: Optional[int] = None
    
    # Champs legacy pour compatibilité
    contenu: str = ""  # Sera deprecated
    articles: List[Article] = None  # Liste plate pour compatibilité
    
    def __post_init__(self):
        if self.structure is None:
            self.structure = Structure()
        if self.references is None:
            self.references = []
        if self.signataires is None:
            self.signataires = []
        if self.articles is None:
            self.articles = []


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
    
    def find_sommaire_boundaries(self, content: str) -> tuple[int, int]:
        """
        Trouve les limites du sommaire de manière intelligente.
        
        Stratégie:
        1. Chercher le début explicite (# SOMMAIRE)
        2. Identifier les sections listées dans le sommaire
        3. Détecter la fin du sommaire quand:
           - Les mêmes sections réapparaissent avec du contenu complet
           - On trouve un texte de loi complet (avec articles, promulgation, etc.)
        
        Returns:
            tuple: (index_debut, index_fin) en nombre de lignes
        """
        lines = content.split('\n')
        sommaire_start = None
        sommaire_end = None
        
        # Pattern pour détecter les entrées du sommaire avec numéro de page
        # Ex: "28 mai Loi n° 10-2025... 759"
        page_number_pattern = re.compile(r'.*\s+\d{3,4}\s*$')
        
        # Étape 1: Trouver le début du sommaire
        for i, line in enumerate(lines):
            if re.match(r'^#\s*SOMMAIRE\s*$', line.strip(), re.IGNORECASE):
                sommaire_start = i
                break
        
        if sommaire_start is None:
            # Pas de sommaire explicite, chercher un pattern de table des matières
            for i, line in enumerate(lines[:100]):  # Chercher dans les 100 premières lignes
                if 'table des matières' in line.lower():
                    sommaire_start = i
                    break
        
        if sommaire_start is None:
            # Pas de sommaire trouvé, le contenu commence au début
            return (0, 0)
        
        # Étape 2: Identifier les sections du sommaire
        # Ces sections seront répétées quand le contenu réel commence
        sommaire_sections = []
        in_sommaire = True
        
        for i in range(sommaire_start + 1, min(sommaire_start + 200, len(lines))):
            line = lines[i].strip()
            
            # Sections principales dans le sommaire (# PARTIE OFFICIELLE, # - LOIS -, etc.)
            if line.startswith('#') and not line.startswith('##'):
                section_title = line[1:].strip()
                sommaire_sections.append({
                    'title': section_title,
                    'line': i,
                    'seen_again': False
                })
        
        # Étape 3: Détecter la fin du sommaire
        # Le sommaire se termine quand on voit les mêmes sections réapparaitre
        # mais cette fois avec du contenu réel (pas juste des références)
        
        section_repetitions = {}  # Compte combien de fois chaque section apparait
        
        for i in range(sommaire_start + 1, len(lines)):
            line = lines[i].strip()
            
            # Vérifier si c'est une section titre
            if line.startswith('#') and not line.startswith('##'):
                section_title = line[1:].strip()
                
                # Compter les répétitions
                if section_title not in section_repetitions:
                    section_repetitions[section_title] = []
                section_repetitions[section_title].append(i)
            
            # Critère 1: Si on voit une section répétée au moins 2 fois
            # et qu'on dépasse la zone probable du sommaire
            if i > sommaire_start + 15:  # Au moins 15 lignes après "SOMMAIRE"
                for section_title, occurrences in section_repetitions.items():
                    if len(occurrences) >= 2:
                        # La deuxième occurrence est probablement le début du contenu réel
                        # Vérifier qu'elle est suffisamment loin de la première
                        if occurrences[1] - occurrences[0] > 5:
                            # Vérifier que dans les lignes suivantes il y a du contenu réel
                            # (pas juste des numéros de page)
                            has_real_content = False
                            for j in range(occurrences[1] + 1, min(occurrences[1] + 20, len(lines))):
                                check_line = lines[j].strip()
                                # Contenu réel = lignes longues sans numéro de page à la fin
                                if len(check_line) > 50 and not page_number_pattern.match(check_line):
                                    has_real_content = True
                                    break
                            
                            if has_real_content:
                                sommaire_end = occurrences[1]
                                break
                
                if sommaire_end:
                    break
            
            # Critère 2: Texte de loi complet détecté
            # Un texte avec "L'Assemblée" ou "promulgue la loi" = contenu réel
            if i > sommaire_start + 20:
                if any(marker in line.lower() for marker in [
                    "l'assemblée nationale",
                    "promulgue la loi",
                    "le président de la république promulgue",
                    "article premier :",
                    "vu la constitution"
                ]):
                    # Remonter pour trouver le titre de ce texte
                    for j in range(i - 1, max(sommaire_start, i - 10), -1):
                        if lines[j].startswith('#'):
                            sommaire_end = j
                            break
                    break
        
        # Si on n'a pas trouvé de fin claire, chercher la dernière ligne avec numéro de page
        if sommaire_end is None:
            last_page_number_line = sommaire_start
            for i in range(sommaire_start + 1, min(sommaire_start + 150, len(lines))):
                if page_number_pattern.match(lines[i].strip()):
                    last_page_number_line = i
            
            # Le sommaire se termine quelques lignes après la dernière référence de page
            sommaire_end = last_page_number_line + 2
        
        return (sommaire_start, sommaire_end)
    
    def split_into_sections(self, content: str) -> List[tuple[str, str]]:
        """Découpe le contenu en sections basées sur les titres de niveau 1 (#), en ignorant le sommaire"""
        
        # Trouver les limites du sommaire
        sommaire_start, sommaire_end = self.find_sommaire_boundaries(content)
        
        lines = content.split('\n')
        
        # Ne traiter que le contenu après le sommaire
        relevant_lines = lines[sommaire_end:] if sommaire_end > 0 else lines
        
        sections = []
        current_title = ""
        current_content = []
        
        for line in relevant_lines:
            # Vérifier si c'est un titre de niveau 1
            if line.startswith('# ') and not line.startswith('##'):
                # Sauvegarder la section précédente
                if current_title and current_content:
                    section_content = '\n'.join(current_content).strip()
                    if section_content:  # Seulement si non vide
                        sections.append((current_title, section_content))
                
                # Démarrer nouvelle section
                current_title = line[2:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # Ajouter la dernière section
        if current_title and current_content:
            section_content = '\n'.join(current_content).strip()
            if section_content:
                sections.append((current_title, section_content))
        
        return sections
    
    def clean_content(self, content: str) -> str:
        """
        Nettoie le contenu textuel pour le stockage.
        Supprime les marqueurs Markdown excessifs et normalise les espaces.
        """
        # Supprimer les titres Markdown (# Titre) qui sont déjà dans la structure
        # Mais on garde le texte, juste on enlève le balisage #
        cleaned = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)
        
        # Remplacer les sauts de ligne multiples par un double saut de ligne
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Supprimer les espaces en début/fin de ligne
        cleaned = '\n'.join(line.strip() for line in cleaned.split('\n'))
        
        # Supprimer les césures de mots en fin de ligne (ex: "program-\nmation")
        # Attention: peut être risqué si le mot est vraiment composé, mais souvent utile pour l'OCR
        cleaned = re.sub(r'(\w)-\n(\w)', r'\1\2', cleaned)
        
        return cleaned.strip()

    def extract_preambule(self, content: str) -> Optional[str]:
        """
        Extrait le préambule d'un texte de loi.
        """
        # Chercher le début du texte jusqu'au premier TITRE ou Article
        lines = content.split('\n')
        preambule_lines = []
        
        for line in lines:
            if re.match(r'^#?\s*(?:TITRE|Chapitre|Section|Article|Art\.)', line.strip(), re.IGNORECASE):
                break
            if line.strip():
                preambule_lines.append(line.strip())
        
        # Si on a trouvé quelque chose et que ce n'est pas tout le texte
        if preambule_lines and len(preambule_lines) < len(lines):
            return ' '.join(preambule_lines)
        
        return None

    def parse_hierarchical_structure(self, content: str) -> Structure:
        """
        Parse le contenu pour extraire la structure hiérarchique complète.
        Gère: TITRE > Chapitre > Section > Article
        """
        lines = content.split('\n')
        structure = Structure()
        
        current_titre = None
        current_chapitre = None
        current_section = None
        current_article = None
        current_article_content = []
        
        # Fonction helper interne pour sauvegarder l'article en cours
        def save_current_article():
            nonlocal current_article, current_article_content
            if current_article:
                current_article.contenu = '\n'.join(current_article_content).strip()
                # Nettoyer le contenu de l'article
                current_article.contenu = self.clean_content(current_article.contenu)
                
                if current_section:
                    current_section.articles.append(current_article)
                elif current_chapitre:
                    current_chapitre.articles.append(current_article)
                elif current_titre:
                    current_titre.articles.append(current_article)
                else:
                    structure.articles.append(current_article)
                
                current_article = None
                current_article_content = []

        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                if current_article:
                    current_article_content.append("")
                continue

            # Détecter TITRE
            titre_match = re.match(r'^#?\s*TITRE\s+([IVX]+|\d+)(?:\s*[:：]\s*(.+))?$', line_stripped, re.IGNORECASE)
            if titre_match:
                save_current_article()
                
                # Sauvegarder les éléments précédents dans la hiérarchie
                if current_section:
                    if current_chapitre: current_chapitre.sections.append(current_section)
                    else: structure.sections.append(current_section)
                    current_section = None
                
                if current_chapitre:
                    if current_titre: current_titre.chapitres.append(current_chapitre)
                    else: structure.chapitres.append(current_chapitre)
                    current_chapitre = None
                
                if current_titre:
                    structure.titres.append(current_titre)
                
                numero = titre_match.group(1)
                intitule = titre_match.group(2).strip() if titre_match.group(2) else ""
                current_titre = Titre(numero=numero, intitule=intitule)
                continue

            # Détecter CHAPITRE
            chapitre_match = re.match(r'^#?\s*Chapitre\s+([IVX]+|\d+|premier|un)(?:\s*[:：]\s*(.+))?$', line_stripped, re.IGNORECASE)
            if chapitre_match:
                save_current_article()
                
                if current_section:
                    if current_chapitre: current_chapitre.sections.append(current_section)
                    else: structure.sections.append(current_section)
                    current_section = None
                
                if current_chapitre:
                    if current_titre: current_titre.chapitres.append(current_chapitre)
                    else: structure.chapitres.append(current_chapitre)
                
                numero = chapitre_match.group(1)
                titre = chapitre_match.group(2).strip() if chapitre_match.group(2) else ""
                current_chapitre = Chapitre(numero=numero, titre=titre)
                continue

            # Détecter SECTION
            section_match = re.match(r'^#?\s*(?:Section|SECTION)\s+([IVX]+|\d+)(?:\s*[:：]\s*(.+))?$', line_stripped, re.IGNORECASE)
            if section_match:
                save_current_article()
                
                if current_section:
                    if current_chapitre: current_chapitre.sections.append(current_section)
                    else: structure.sections.append(current_section)
                
                numero = section_match.group(1)
                titre = section_match.group(2).strip() if section_match.group(2) else ""
                current_section = Section(numero=numero, titre=titre)
                continue

            # Détecter ARTICLE
            article_match = re.match(r'^(?:Article|Art\.|ART\.)\s+(\d+(?:er|ème|°|re)?|premier|un)\s*[.：:]?\s*(?:[-–—]\s*)?(.*)$', line_stripped, re.IGNORECASE)
            if article_match:
                save_current_article()
                
                numero = article_match.group(1)
                contenu_start = article_match.group(2).strip()
                current_article = Article(numero=numero, contenu="")
                current_article_content = [contenu_start] if contenu_start else []
                continue

            # Contenu de l'article ou contenu libre
            if current_article:
                current_article_content.append(line)
        
        # Sauvegarder le dernier article et fermer la structure
        save_current_article()
        
        if current_section:
            if current_chapitre: current_chapitre.sections.append(current_section)
            else: structure.sections.append(current_section)
        
        if current_chapitre:
            if current_titre: current_titre.chapitres.append(current_chapitre)
            else: structure.chapitres.append(current_chapitre)
        
        if current_titre:
            structure.titres.append(current_titre)
            
        return structure

    def parse_texte(self, title: str, content: str, publication_id: str, index: int) -> Optional[TexteLegal]:
        """Parse une section en TexteLegal"""
        type_texte = self.detect_texte_type(title + '\n' + content[:500])
        
        # Ignorer les sections qui sont des sous-parties
        if title.strip().startswith(('TITRE ', 'Chapitre ', 'Section ', 'Sous-section',
                                     'A - ', 'B - ', 'C - ', 'Pilier ', 'ARTICLE ')):
            return None
        
        # Ignorer les sections vides
        if not type_texte or not content.strip():
            return None
        
        numero, date = self.extract_numero_date(title + '\n' + content[:300], type_texte)
        
        # Extraction de la structure hiérarchique
        structure = self.parse_hierarchical_structure(content)
        
        # Extraction du préambule
        preambule = self.extract_preambule(content)
        
        # Extraction des métadonnées
        references = self.extract_references(content)
        signataires = self.extract_signataires(content)
        
        # Nettoyage du contenu global pour le stockage
        cleaned_content = self.clean_content(content)
        
        # Générer un ID unique
        if numero:
            texte_id = f"{publication_id}-{type_texte.lower()}-{numero.replace('/', '-')}"
        else:
            texte_id = f"{publication_id}-{type_texte.lower()}-{index}"
        
        # Pour la compatibilité, on garde aussi une liste plate d'articles
        # On récupère tous les articles de la structure
        flat_articles = []
        flat_articles.extend(structure.articles)
        for titre in structure.titres:
            flat_articles.extend(titre.articles)
            for chap in titre.chapitres:
                flat_articles.extend(chap.articles)
                for sec in chap.sections:
                    flat_articles.extend(sec.articles)
        for chap in structure.chapitres:
            flat_articles.extend(chap.articles)
            for sec in chap.sections:
                flat_articles.extend(sec.articles)
        for sec in structure.sections:
            flat_articles.extend(sec.articles)
            
        return TexteLegal(
            id=texte_id,
            type_texte=type_texte,
            numero=numero,
            date=date,
            titre=title,
            contenu=cleaned_content,
            preambule=preambule,
            structure=structure,
            articles=flat_articles,
            references=references,
            signataires=signataires
        )
    
    def merge_related_sections(self, sections: List[tuple[str, str]]) -> List[tuple[str, str]]:
        """Fusionne les sections qui appartiennent au même texte légal"""
        if not sections:
            return []
        
        merged = []
        current_main_section = None
        accumulated_content = []
        
        for title, content in sections:
            # Vérifier si c'est une section principale (nouveau texte)
            is_main_section = False
            title_upper = title.upper()
            
            # Patterns de sections principales
            if re.search(r'LOI\s+(?:N°|n°|No)\s*[\d/-]+', title, re.IGNORECASE):
                is_main_section = True
            elif re.search(r'DECRET\s+(?:N°|n°|No)\s*[\d/-]+', title, re.IGNORECASE):
                is_main_section = True
            elif re.search(r'ARRETE\s+(?:N°|n°|No)\s*[\d/-]+', title, re.IGNORECASE):
                is_main_section = True
            elif any(keyword in title_upper for keyword in ['ACCORD DE', 'CONVENTION', 'PROTOCOLE']):
                is_main_section = True
            elif title_upper.startswith('- LOIS -') or title_upper.startswith('- DECRETS'):
                is_main_section = True
            
            # Si c'est un titre/chapitre/section (sous-partie)
            is_subsection = title.strip().startswith((
                'TITRE ', 'Chapitre ', 'Section ', 'Sous-section',
                'A - ', 'B - ', 'C - ', 'Pilier ', 'Article '
            ))
            
            if is_main_section and not is_subsection:
                # Sauvegarder la section précédente
                if current_main_section:
                    merged_content = '\n\n'.join(accumulated_content).strip()
                    merged.append((current_main_section, merged_content))
                
                # Démarrer une nouvelle section principale
                current_main_section = title
                accumulated_content = [content]
            elif current_main_section:
                # Ajouter à la section en cours
                # Ajouter le titre de la sous-section comme marqueur
                accumulated_content.append(f"# {title}\n\n{content}")
            else:
                # Pas encore de section principale, ignorer ou traiter séparément
                # C'est probablement du contenu introductif
                if content.strip():
                    merged.append((title, content))
        
        # Ajouter la dernière section
        if current_main_section:
            merged_content = '\n\n'.join(accumulated_content).strip()
            merged.append((current_main_section, merged_content))
        
        return merged

    
    def convert_file(self, md_file: Path) -> Dict[str, Any]:
        """Convertit un fichier MD en structure JSON"""
        print(f"📄 Traitement de {md_file.name}...")
        
        # Lire le fichier
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraire les infos de publication
        pub_info = self.extract_publication_info(md_file.name, content)
        publication = Publication(**pub_info)
        
        # Découper en sections (en ignorant le sommaire)
        sections = self.split_into_sections(content)
        
        # Fusionner les sections connexes (chapitres avec leur loi parent, etc.)
        merged_sections = self.merge_related_sections(sections)
        
        # Parser chaque section fusionnée
        for index, (title, section_content) in enumerate(merged_sections):
            if not title or not section_content:
                continue
            
            texte = self.parse_texte(title, section_content, publication.id, index)
            if texte:
                publication.textes.append(texte)
        
        print(f"   ✓ {len(publication.textes)} textes extraits")
        
        return self.to_json_dict(publication)
    
    def to_json_dict(self, publication: Publication) -> Dict[str, Any]:
        """Convertit une Publication en dictionnaire JSON serializable"""
        
        def article_to_dict(art):
            return {
                'numero': art.numero,
                'contenu': art.contenu,
                'intitule': art.intitule
            }
            
        def section_to_dict(sec):
            return {
                'numero': sec.numero,
                'titre': sec.titre,
                'articles': [article_to_dict(a) for a in sec.articles],
                'contenu_libre': sec.contenu_libre
            }
            
        def chapitre_to_dict(chap):
            return {
                'numero': chap.numero,
                'titre': chap.titre,
                'articles': [article_to_dict(a) for a in chap.articles],
                'sections': [section_to_dict(s) for s in chap.sections],
                'contenu_libre': chap.contenu_libre
            }
            
        def titre_to_dict(titre):
            return {
                'numero': titre.numero,
                'intitule': titre.intitule,
                'chapitres': [chapitre_to_dict(c) for c in titre.chapitres],
                'articles': [article_to_dict(a) for a in titre.articles],
                'contenu_libre': titre.contenu_libre
            }
            
        def structure_to_dict(struct):
            if not struct: return None
            return {
                'titres': [titre_to_dict(t) for t in struct.titres],
                'chapitres': [chapitre_to_dict(c) for c in struct.chapitres],
                'sections': [section_to_dict(s) for s in struct.sections],
                'articles': [article_to_dict(a) for a in struct.articles]
            }

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
                'preambule': texte.preambule,
                'structure': structure_to_dict(texte.structure),
                'articles': [article_to_dict(art) for art in texte.articles], # Legacy flat list
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
        default='data/out/json',
        help='Répertoire de sortie pour les fichiers JSON (défaut: data/out/json)'
    )
    parser.add_argument(
        '--file',
        '-f',
        type=str,
        help='Convertir un seul fichier spécifique'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Convertir tous les fichiers (défaut si --file n\'est pas spécifié)'
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
        file_path = Path(args.file)
        
        # Vérifier si le fichier existe tel quel
        if file_path.exists():
            md_file = file_path
        # Sinon, essayer de le trouver dans le dossier d'entrée
        elif not file_path.is_absolute():
            md_file = Path(args.input) / args.file
        else:
            md_file = file_path
            
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
