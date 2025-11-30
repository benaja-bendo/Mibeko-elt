#!/usr/bin/env python3
"""
Schema-Compliant Journal Officiel Converter
Extracts individual legal texts from Journal Officiel MD files
and outputs separate JSON files conforming to schemas/journal_officiel.schema.json
"""

import re
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import jsonschema

class SchemaCompliantConverter:
    """Converts Journal Officiel MD files to schema-compliant JSON files"""
    
    # Regex patterns for text detection
    PATTERNS = {
        'loi': r'(?:Loi|LOI)\s+(?:N°|n°|No)\s*([0-9-]+)\s+(?:DU|du)\s+([^\n]+)',
        'decret': r'(?:Décret|DECRET|Decret)\s+(?:N°|n°|No)\s*([0-9-]+)',
        'arrete': r'(?:Arrêté|ARRETE|Arrete)\s+(?:N°|n°|No)\s*([0-9-]+)',
        'date': r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})',
    }
    
    def __init__(self, output_dir: Path, schema_path: Path):
        """
        Initialize converter
        
        Args:
            output_dir: Directory for schema-compliant JSON output
            schema_path: Path to the JSON schema file
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.quarantine_dir = self.output_dir / "quarantine"
        self.quarantine_dir.mkdir(exist_ok=True)
        
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)

    def sanitize_content(self, content: str) -> str:
        """
        Sanitize content to fix common OCR errors and normalize text
        """
        # Common OCR replacements
        replacements = [
            (r'\bL0I\b', 'LOI'),
            (r'\bArtide\b', 'Article'),
            (r'\bDÉCRÊT\b', 'DECRET'),
            (r'\bARRETÊ\b', 'ARRETE'),
            (r'\bN°\s*o\b', 'N°'),  # Fix N° o -> N°
        ]
        
        sanitized = content
        for pattern, replacement in replacements:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
            
        return sanitized

    def find_sommaire_boundaries(self, content: str) -> Tuple[int, int]:
        """
        Find table of contents boundaries (reused from md_to_json_converter.py)
        
        Returns:
            (start_line, end_line) tuple
        """
        lines = content.split('\n')
        sommaire_start = None
        sommaire_end = None
        
        # Find SOMMAIRE header
        for i, line in enumerate(lines):
            if re.match(r'^#\s*SOMMAIRE\s*$', line.strip(), re.IGNORECASE):
                sommaire_start = i
                break
        
        if sommaire_start is None:
            return (0, 0)
        
        # Pattern for sommaire entries with page numbers
        page_number_pattern = re.compile(r'.*\s+\d{3,4}\s*$')
        
        # Track section repetitions to detect end of sommaire
        section_repetitions = {}
        
        for i in range(sommaire_start + 1, len(lines)):
            line = lines[i].strip()
            
            # Check for section headers
            if line.startswith('#') and not line.startswith('##'):
                section_title = line[1:].strip()
                
                if section_title not in section_repetitions:
                    section_repetitions[section_title] = []
                section_repetitions[section_title].append(i)
            
            # Detect end: section appears 2+ times with real content
            if i > sommaire_start + 15:
                for section_title, occurrences in section_repetitions.items():
                    if len(occurrences) >= 2:
                        if occurrences[1] - occurrences[0] > 5:
                            # Check for real content after second occurrence
                            has_real_content = False
                            for j in range(occurrences[1] + 1, min(occurrences[1] + 20, len(lines))):
                                check_line = lines[j].strip()
                                if len(check_line) > 50 and not page_number_pattern.match(check_line):
                                    has_real_content = True
                                    break
                            
                            if has_real_content:
                                sommaire_end = occurrences[1]
                                break
                
                if sommaire_end:
                    break
            
            # Alternative: detect promulgation text
            if i > sommaire_start + 20:
                if any(marker in line.lower() for marker in [
                    "l'assemblée nationale",
                    "promulgue la loi",
                    "article premier :"
                ]):
                    # Backtrack to find section header
                    for j in range(i - 1, max(sommaire_start, i - 10), -1):
                        if lines[j].startswith('#'):
                            sommaire_end = j
                            break
                    break
        
        # Fallback: last line with page numbers
        if sommaire_end is None:
            last_page_line = sommaire_start
            for i in range(sommaire_start + 1, min(sommaire_start + 150, len(lines))):
                if page_number_pattern.match(lines[i].strip()):
                    last_page_line = i
            sommaire_end = last_page_line + 2
        
        return (sommaire_start, sommaire_end)
    
    def detect_texte_type(self, text: str) -> Optional[str]:
        """Detect type of legal text"""
        text_upper = text.upper()
        
        types = [
            ('LOI CONSTITUTIONNELLE', 'LOI_CONSTITUTIONNELLE'),
            ('LOI', 'LOI'),
            ('DECRET', 'DECRET'),
            ('ARRETE', 'ARRETE'),
            ('CONVENTION', 'CONVENTION'),
            ('DELIBERATION', 'DELIBERATION'),
        ]
        
        for keyword, type_name in types:
            if keyword in text_upper:
                return type_name
        
        return None
    
    def normalize_date(self, date_str: str) -> Optional[str]:
        """Normalize date to ISO format (YYYY-MM-DD)"""
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
    
    def extract_numero_date(self, text: str, type_texte: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract numero and date from text"""
        numero = None
        date = None
        
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
            
            if date_str:
                date = self.normalize_date(date_str)
        
        return numero, date
    
    def split_into_texts(self, content: str) -> List[Tuple[str, str]]:
        """
        Split MD content into individual legal texts
        
        Returns:
            List of (title, content) tuples
        """
        # Skip sommaire
        sommaire_start, sommaire_end = self.find_sommaire_boundaries(content)
        lines = content.split('\n')
        relevant_lines = lines[sommaire_end:] if sommaire_end > 0 else lines
        
        texts = []
        current_title = ""
        current_content = []
        in_text = False
        
        for i, line in enumerate(relevant_lines):
            line_stripped = line.strip()
            
            # Check if this line is a legal text title
            # Pattern: "Loi n° XX du YY..." or "Décret n° XX..." etc.
            is_text_title = False
            
            # Check for text title patterns (with or without #)
            title_line = line_stripped.lstrip('#').strip()
            if re.search(r'^(?:Loi|LOI|Décret|DECRET|Décret|Arrêté|ARRETE|Arrete)\s+(?:N°|n°|No)\s*[0-9-]+', title_line):
                is_text_title = True
            
            if is_text_title:
                # Save previous text
                if current_title and current_content:
                    content_text = '\n'.join(current_content).strip()
                    if content_text:
                        texts.append((current_title, content_text))
                
                # Start new text
                current_title = title_line
                current_content = []
                in_text = True
            elif in_text:
                # Check if we've hit another section marker that ends this text
                # (another PARTIE, another major section, etc.)
                if line.startswith('# PARTIE ') or line.startswith('# - DECRETS') or \
                   (line.startswith('# - ') and 'LOIS' not in line and 'DECRET' not in line):
                    # This marks the end of current text
                    if current_title and current_content:
                        content_text = '\n'.join(current_content).strip()
                        if content_text:
                            texts.append((current_title, content_text))
                        current_title = ""
                        current_content = []
                        in_text = False
                else:
                    current_content.append(line)
            else:
                # Not in a text yet, skip
                pass
        
        # Save last text
        if current_title and current_content:
            content_text = '\n'.join(current_content).strip()
            if content_text:
                texts.append((current_title, content_text))
        
        return texts
    
    def parse_article_content(self, article_text: str) -> List[Dict[str, str]]:
        """
        Parse article content into structured items (alinea, enumeration)
        """
        # Split by newlines to handle lists that are single-spaced
        lines = [line.strip() for line in article_text.split('\n') if line.strip()]
        structured_content = []
        
        for line in lines:
            # Check for enumeration markers
            enum_match = re.match(r'^(\d+[°\.]|[a-z]\)|\-)\s+(.*)', line, re.DOTALL)
            if enum_match:
                marker = enum_match.group(1)
                content = enum_match.group(2)
                structured_content.append({
                    "type": "enumeration",
                    "marker": marker,
                    "content": content
                })
            else:
                # If it's not an enumeration, it's an alinea.
                # However, if the previous item was an alinea and this line doesn't start with a marker,
                # it might be a continuation of the previous alinea?
                # In legal texts, usually each visual paragraph (or list item) is distinct.
                # But if we split by \n, we might split a wrapped sentence.
                # For now, let's assume \n means new item if it looks like one, or we can merge?
                # Given the user wants granularity, treating each line as an item (if meaningful) is better than merging incorrectly.
                # But "Le dossier comprend :" is clearly an alinea.
                structured_content.append({
                    "type": "alinea",
                    "content": line
                })
        
        return structured_content

    def extract_references(self, text: str) -> List[Dict[str, str]]:
        """
        Extract legal references from text
        """
        references = []
        # Regex for finding references like "Loi n° 10-2025"
        ref_pattern = r'(Loi|Décret|Arrêté)\s+(?:n°|N°)\s*([0-9-]+(?:\s+du\s+\d{1,2}\s+\w+\s+\d{4})?)'
        
        matches = re.finditer(ref_pattern, text, re.IGNORECASE)
        for match in matches:
            full_ref = match.group(0)
            ref_type = match.group(1).lower()
            # Normalize type
            if ref_type == 'décret': ref_type = 'decret'
            if ref_type == 'arrêté': ref_type = 'arrete'
            
            references.append({
                "type": ref_type,
                "texte_cite": full_ref,
                # "id": "uuid-placeholder" # TODO: Implement lookup
            })
            
        return references

    def parse_hierarchical_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse content into schema-compliant hierarchical structure
        
        Returns:
            List of DivisionHierarchique and Article objects
        """
        lines = content.split('\n')
        result = []
        
        current_division = None
        division_stack = []  # Stack to track nested divisions
        current_article = None
        current_article_lines = []
        
        def save_article():
            """Helper to save current article"""
            nonlocal current_article, current_article_lines
            if current_article:
                article_text = '\n'.join(current_article_lines).strip()
                
                # Parse structured content
                structured_text = self.parse_article_content(article_text)
                
                # Extract references
                references = self.extract_references(article_text)
                
                article_obj = {
                    "type": "Article",
                    "numero": current_article,
                    "texte": structured_text
                }
                
                if references:
                    article_obj["references"] = references
                
                # Add to current division or top-level
                if division_stack:
                    if 'elements' not in division_stack[-1]:
                        division_stack[-1]['elements'] = []
                    division_stack[-1]['elements'].append(article_obj)
                else:
                    result.append(article_obj)
                
                current_article = None
                current_article_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                if current_article:
                    current_article_lines.append("")
                continue
            
            # Detect TITRE, Chapitre, Section, etc.
            division_match = re.match(
                r'^#?\s*(TITRE|Titre|Chapitre|Section|Sous-section|Paragraphe)\s+([IVX0-9]+|premier|un)(?:\s*[:：]\s*(.+))?$',
                line_stripped,
                re.IGNORECASE
            )
            
            if division_match:
                save_article()
                
                div_type = division_match.group(1).capitalize()
                if div_type.lower() == 'titre':
                    div_type = 'Titre'
                
                numero = division_match.group(2)
                intitule_text = division_match.group(3).strip() if division_match.group(3) else ""
                
                # Create full intitule with type and numero
                if intitule_text:
                    full_intitule = f"{div_type.upper()} {numero} : {intitule_text}"
                else:
                    full_intitule = f"{div_type.upper()} {numero}"
                
                division_obj = {
                    "type": div_type,
                    "intitule": full_intitule,
                    "elements": []
                }
                
                # Determine nesting level
                division_levels = ['Titre', 'Chapitre', 'Section', 'Sous-section', 'Paragraphe']
                current_level = division_levels.index(div_type) if div_type in division_levels else 0
                
                # Pop stack until we find the right parent level
                while division_stack and division_levels.index(division_stack[-1]['type']) >= current_level:
                    completed_div = division_stack.pop()
                    if division_stack:
                        division_stack[-1]['elements'].append(completed_div)
                    else:
                        result.append(completed_div)
                
                # Push new division onto stack
                division_stack.append(division_obj)
                continue
            
            # Detect Article
            article_match = re.match(
                r'^(?:Article|Art\.|ART\.)\s+([\d]+(?:er|ème|°|re)?|premier|un)\s*[.：:]?\s*(?:[-–—]\s*)?(.*)$',
                line_stripped,
                re.IGNORECASE
            )
            
            if article_match:
                save_article()
                
                current_article = article_match.group(1)
                content_start = article_match.group(2).strip()
                current_article_lines = [content_start] if content_start else []
                continue
            
            # Regular content line
            if current_article:
                current_article_lines.append(line)
        
        # Save final article
        save_article()
        
        # Pop remaining divisions from stack
        while division_stack:
            completed_div = division_stack.pop()
            if division_stack:
                division_stack[-1]['elements'].append(completed_div)
            else:
                result.append(completed_div)
        
        return result
    
    def extract_formule_promulgation(self, content: str) -> Optional[str]:
        """Extract promulgation formula"""
        # Look for standard promulgation phrases
        promulgation_patterns = [
            r"(L'Assemblée nationale.*?promulgue.*?:)",
            r"(Le Président de la République promulgue.*?:)",
            r"(L'Assemblée nationale et le Sénat ont délibéré.*?promulgue.*?:)"
        ]
        
        for pattern in promulgation_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                formula = match.group(1).strip()
                # Clean up: replace multiple whitespaces/newlines with single space
                formula = re.sub(r'\s+', ' ', formula)
                return formula
        
        return None
    
    def extract_signatures(self, content: str) -> List[str]:
        """
        Extract signatures as simple string array
        
        Returns:
            List of signature strings with name and function
        """
        signatures = []
        
        # Find "Fait à" section which marks signature block
        fait_match = re.search(r'Fait à ([^,]+), le ([^\n]+)', content)
        if not fait_match:
            return signatures
        
        # Get content after "Fait à"
        fait_pos = fait_match.start()
        signature_block = content[fait_pos:]
        
        # Parse signature patterns
        lines = signature_block.split('\n')
        
        current_function = None
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Function line (e.g., "Le Premier ministre, chef du Gouvernement,")
            if re.match(r'^(?:Le|La|Pour le|Par le)\s+', line, re.IGNORECASE):
                current_function = line.rstrip(',;.')
                continue
            
            # Name line (capitalized names)
            if re.match(r'^[A-Z][a-zA-Z\s\'-]+$', line) and len(line.split()) <= 5:
                if current_function:
                    signatures.append(f"{line}, {current_function}")
                else:
                    signatures.append(line)
                current_function = None
        
        return signatures
    
    def convert_text(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """
        Convert single legal text to schema-compliant JSON
        
        Args:
            title: Text title (e.g., "Loi n° 10-2025 du 28 mai 2025...")
           content: Text content
        
        Returns:
            Schema-compliant dict or None if parsing fails
        """
        # Detect type
        type_texte = self.detect_texte_type(title + '\n' + content[:500])
        if not type_texte:
            return None
        
        # Extract numero and date
        numero, date = self.extract_numero_date(title + '\n' + content[:300], type_texte)
        if not numero:
            return None
        
        # Build numero_texte with type prefix
        if type_texte == 'LOI':
            numero_texte = f"Loi n° {numero}"
        elif type_texte == 'DECRET':
            numero_texte = f"Décret n° {numero}"
        elif type_texte == 'ARRETE':
            numero_texte = f"Arrêté n° {numero}"
        else:
            numero_texte = f"{type_texte} n° {numero}"
        
        # Extract intitule_long (full title after numero)
        intitule_long = title
        # Clean up the title
        for prefix in ['Loi n°', 'Décret n°', 'Arrêté n°', 'LOI', 'DECRET', 'ARRETE']:
            if intitule_long.startswith(prefix):
                intitule_long = intitule_long[len(prefix):].strip()
                # Remove numero pattern
                intitule_long = re.sub(r'^\d+[-/]\d+\s+(?:du|DU)\s+\d+\s+\w+\s+\d{4}\s*', '', intitule_long)
                break
        
        # Extract formule promulgation
        formule_promulgation = self.extract_formule_promulgation(content)
        
        # Parse hierarchical content
        contenu = self.parse_hierarchical_content(content)
        
        # Extract signatures
        signatures = self.extract_signatures(content)
        
        # Build schema object
        schema_obj = {
            "numero_texte": numero_texte,
            "date_publication": date,
            "intitule_long": intitule_long.strip()
        }
        
        # Add optional fields if present
        if formule_promulgation:
            schema_obj["formule_promulgation"] = formule_promulgation
        
        schema_obj["contenu"] = contenu
        
        if signatures:
            schema_obj["signatures"] = signatures
        
        return schema_obj
    
    def generate_filename(self, numero_texte: str) -> str:
        """Generate safe filename from numero_texte"""
        # Convert to lowercase, replace spaces and special chars
        filename = numero_texte.lower()
        filename = re.sub(r'[^a-z0-9-]', '-', filename)
        filename = re.sub(r'-+', '-', filename)
        filename = filename.strip('-')
        return f"{filename}.json"
    
    def convert_file(self, md_file: Path) -> int:
        """
        Convert MD file to single JSON file containing all legal texts
        
        Args:
            md_file: Path to input MD file
        
        Returns:
            Number of texts successfully converted
        """
        print(f"Processing: {md_file.name}")
        
        # Read MD file
        content = md_file.read_text(encoding='utf-8')
        
        # Sanitize content
        content = self.sanitize_content(content)
        
        # Split into individual texts
        texts = self.split_into_texts(content)
        print(f"  Found {len(texts)} legal texts")
        
        # Parse all texts
        parsed_texts = []
        converted_count = 0
        
        for title, text_content in texts:
            # Convert to schema format
            schema_obj = self.convert_text(title, text_content)
            
            if schema_obj:
                parsed_texts.append(schema_obj)
                print(f"  ✓ Parsed: {schema_obj['numero_texte']}")
                converted_count += 1
            else:
                print(f"  ✗ Failed to parse: {title[:50]}...")
        
        # Create output JSON structure
        output_data = {
            "id": md_file.stem,  # e.g., "congo-jo-2025-26"
            "source_file": md_file.name,
            "textes": parsed_texts
        }
        
        # Validate against schema (basic check on structure, though schema is for individual texts usually, 
        # but here we are validating the whole output if we had a schema for it. 
        # The user asked to validate the output. 
        # Since the provided schema is for "DocumentJournalOfficiel" which seems to be a single text based on properties like "numero_texte",
        # but the output is a collection.
        # Wait, the schema has "numero_texte" at root. So the schema is for ONE text.
        # The output file contains MANY texts.
        # So we should validate EACH text against the schema.
        
        valid_texts = []
        for text in parsed_texts:
            try:
                jsonschema.validate(instance=text, schema=self.schema)
                valid_texts.append(text)
            except jsonschema.exceptions.ValidationError as e:
                print(f"  ⚠ Validation Error for {text.get('numero_texte', 'Unknown')}: {e.message}")
                # Save to quarantine
                quarantine_path = self.quarantine_dir / f"INVALID_{text.get('numero_texte', 'unknown').replace(' ', '_')}.json"
                with open(quarantine_path, 'w', encoding='utf-8') as qf:
                    json.dump(text, qf, ensure_ascii=False, indent=2)
        
        # Update output data with only valid texts
        output_data["textes"] = valid_texts
        
        # Generate output filename (same as input but .json)
        output_filename = f"{md_file.stem}.json"
        output_path = self.output_dir / output_filename
        
        # Write single JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Created: {output_filename}")
        print(f"  Contains: {len(valid_texts)} valid legal texts")
        if len(parsed_texts) > len(valid_texts):
            print(f"  ⚠ {len(parsed_texts) - len(valid_texts)} texts failed validation (see quarantine)")
        
        return len(valid_texts)


def main():
    parser = argparse.ArgumentParser(
        description='Convert Journal Officiel MD files to schema-compliant JSON'
    )
    parser.add_argument(
        '--input',
        type=Path,
        help='Input MD file'
    )
    parser.add_argument(
        '--input-dir',
        type=Path,
        default=Path('data/processed'),
        help='Input directory containing MD files (default: data/processed)'
    )
    parser.add_argument(
        '--output-dir',
        type=Path,
        default=Path('data/out'),
        help='Output directory for JSON files (default: data/out)'
    )
    parser.add_argument(
        '--schema',
        type=Path,
        default=Path('schemas/journal_officiel.schema.json'),
        help='Path to JSON schema file'
    )
    
    args = parser.parse_args()
    
    # if not args.input and not args.input_dir:
    #     parser.error('Either --input or --input-dir must be specified')
    
    if not args.schema.exists():
        print(f"Error: Schema file not found: {args.schema}")
        return 1

    # Create converter
    converter = SchemaCompliantConverter(args.output_dir, args.schema)
    
    total_converted = 0
    
    # Process files
    if args.input:
        if not args.input.exists():
            print(f"Error: File not found: {args.input}")
            return 1
        total_converted = converter.convert_file(args.input)
    
    elif args.input_dir:
        if not args.input_dir.exists():
            print(f"Error: Directory not found: {args.input_dir}")
            return 1
        
        md_files = list(args.input_dir.glob('*.md'))
        if not md_files:
            print(f"No .md files found in {args.input_dir}")
            return 1
        
        print(f"Found {len(md_files)} MD files\n")
        
        for md_file in md_files:
            count = converter.convert_file(md_file)
            total_converted += count
            print()
    
    print(f"✓ Successfully converted {total_converted} legal texts")
    print(f"  Output directory: {args.output_dir}")
    
    return 0


if __name__ == '__main__':
    exit(main())
