#!/usr/bin/env python3
"""
Script de chargement des données JSON vers PostgreSQL (Nouveau Schéma).
Ce script lit les fichiers JSON générés par convert_jo_structured.py et les insère
dans la base de données PostgreSQL définie par schema_postgres.sql.
"""

import json
import os
import re
import psycopg2
from psycopg2.extras import Json
from pathlib import Path
import argparse
from typing import Dict, Any, Optional, List
from datetime import date, datetime

# Configuration de la base de données
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "laravel-mibeko")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

def get_db_connection():
    """Établit une connexion à la base de données."""
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

def sanitize_ltree_label(label: str) -> str:
    """
    Nettoie une chaîne pour qu'elle soit compatible avec le type ltree.
    Ltree accepte: A-Z, a-z, 0-9, _
    """
    # Remplacer les caractères non-alphanumériques par _
    clean = re.sub(r'[^a-zA-Z0-9]', '_', label)
    # Supprimer les _ multiples et les _ au début/fin
    clean = re.sub(r'_+', '_', clean).strip('_')
    # Si vide ou commence par chiffre (interdit parfois selon config, mais ok en ltree standard si pas mot clé),
    # on préfixe. Ltree labels cannot be empty.
    if not clean:
        return "node"
    return clean[:50] # Limiter la longueur

def get_or_create_document_type(cursor, type_code: str, nom: str) -> str:
    """Récupère ou crée un type de document."""
    # Normalisation du code
    code = type_code.upper()[:10]
    
    cursor.execute("SELECT code FROM document_types WHERE code = %s", (code,))
    res = cursor.fetchone()
    if res:
        return res[0]
    
    cursor.execute(
        "INSERT INTO document_types (code, nom) VALUES (%s, %s) RETURNING code",
        (code, nom)
    )
    return cursor.fetchone()[0]

def insert_legal_document(cursor, texte: Dict[str, Any], publication_date: Optional[str] = None) -> str:
    """Insère un document légal."""
    
    # 1. Gestion du Type de document
    # On essaie de déduire le type depuis le numéro ou le titre si pas explicite
    # Le JSON de convert_jo_structured a "numero_texte" genre "Loi n°..."
    raw_numero = texte.get('numero_texte', '')
    type_str = "AUTRE"
    if raw_numero.lower().startswith('loi'):
        type_str = "LOI"
    elif raw_numero.lower().startswith('décret') or raw_numero.lower().startswith('decret'):
        type_str = "DECRET"
    elif raw_numero.lower().startswith('arrêté') or raw_numero.lower().startswith('arrete'):
        type_str = "ARRETE"
    elif raw_numero.lower().startswith('ordonnance'):
        type_str = "ORD"
        
    type_code = get_or_create_document_type(cursor, type_str, type_str)
    
    # 2. Insertion du Document
    # Extraction des dates
    date_pub = texte.get('date_publication') or publication_date
    
    # On essaie d'extraire une date de signature du titre ou du contenu si possible, 
    # sinon on utilise date_publication comme fallback pour date_signature pour l'instant
    # ou NULL.
    date_sig = date_pub # Simplification
    
    sql = """
    INSERT INTO legal_documents (
        type_code, 
        titre_officiel, 
        date_signature, 
        date_publication, 
        statut
    ) VALUES (%s, %s, %s, %s, 'vigueur')
    RETURNING id;
    """
    
    cursor.execute(sql, (
        type_code,
        texte.get('intitule_long', 'Sans titre'),
        date_sig,
        date_pub
    ))
    doc_id = cursor.fetchone()[0]
    
    # 3. Insertion de la Structure (Récursif)
    # Le contenu est une liste d'éléments (Divisions ou Articles)
    contenu = texte.get('contenu', [])
    
    # On commence avec un path vide ou 'root' ? 
    # Le schema dit "root.livre1..."
    # On va utiliser l'ID du document comme racine virtuelle ou juste commencer par les titres.
    # Mais ltree doit être unique ? Non, juste le path.
    # On va utiliser "doc_{id}" comme racine pour éviter les collisions si on stocke tout dans la même table
    # Mais structure_nodes a un document_id, donc le scope est le document.
    # On peut commencer les paths par "root".
    
    insert_structure_elements(cursor, doc_id, contenu, "root", date_sig)
    
    return doc_id

def insert_structure_elements(cursor, doc_id: str, elements: List[Dict[str, Any]], parent_path: str, date_validity_start: str):
    """
    Parcourt récursivement les éléments de structure.
    parent_path: le ltree path du parent (ex: "root.titre_1")
    """
    if not elements:
        return

    # Compteurs pour générer des labels uniques (titre_1, titre_2...)
    counts = {} 
    
    for i, el in enumerate(elements):
        el_type = el.get('type')
        
        if el_type == 'Article':
            insert_article(cursor, doc_id, el, parent_path, date_validity_start, i)
        else:
            # C'est une Division (Titre, Chapitre, etc.)
            # Génération du label ltree
            # Ex: Titre I -> titre_i, ou juste titre_1, titre_2
            # On va utiliser le type et un index pour être sûr
            prefix = sanitize_ltree_label(el_type).lower()
            if prefix not in counts:
                counts[prefix] = 0
            counts[prefix] += 1
            
            # On essaie d'utiliser le numéro si dispo et propre (ex: "I", "1")
            # Sinon on utilise l'index
            # Pour ltree, "titre_I" est valide.
            
            # Extraction du numéro du titre "TITRE I" -> "I"
            # Le JSON a "intitule": "TITRE I : ..."
            # Mais convert_jo_structured ne sépare pas toujours proprement le numéro dans 'numero'.
            # On va générer un label séquentiel pour la robustesse : "titre_1", "chapitre_1"...
            # Ou utiliser le path existant si on veut être sémantique.
            # Restons simple : type_index
            
            node_label = f"{prefix}_{counts[prefix]}"
            current_path = f"{parent_path}.{node_label}"
            
            # Insertion dans structure_nodes
            sql_node = """
            INSERT INTO structure_nodes (
                document_id,
                type_unite,
                numero,
                titre,
                tree_path
            ) VALUES (%s, %s, %s, %s, %s::ltree)
            RETURNING id;
            """
            
            # Essayer d'extraire un numéro propre de l'intitulé
            # Ex: "TITRE I : DISPOSITIONS" -> Num: "I", Titre: "DISPOSITIONS"
            intitule = el.get('intitule', '')
            parts = intitule.split(':', 1)
            numero_candidat = parts[0].strip() # "TITRE I"
            titre_candidat = parts[1].strip() if len(parts) > 1 else ""
            
            cursor.execute(sql_node, (
                doc_id,
                el_type,
                numero_candidat,
                titre_candidat,
                current_path
            ))
            node_id = cursor.fetchone()[0]
            
            # Récursion pour les enfants
            children = el.get('elements', [])
            insert_structure_elements(cursor, doc_id, children, current_path, date_validity_start)

def insert_article(cursor, doc_id: str, article_data: Dict[str, Any], parent_path: str, date_start: str, ordre: int):
    """Insère un article et sa version initiale."""
    
    # 1. Récupérer l'ID du parent (le noeud de structure correspondant au parent_path)
    # Attention: parent_path est le path ltree.
    cursor.execute("SELECT id FROM structure_nodes WHERE document_id = %s AND tree_path = %s::ltree", (doc_id, parent_path))
    res = cursor.fetchone()
    parent_id = res[0] if res else None
    
    # 2. Créer l'article (Identité)
    numero = article_data.get('numero', '')
    
    sql_article = """
    INSERT INTO articles (
        document_id,
        parent_node_id,
        numero_article,
        ordre_affichage
    ) VALUES (%s, %s, %s, %s)
    RETURNING id;
    """
    cursor.execute(sql_article, (doc_id, parent_id, numero, ordre))
    article_id = cursor.fetchone()[0]
    
    # 3. Créer la version (Contenu)
    # Reconstruire le contenu texte depuis la structure (alineas, etc.)
    texte_struct = article_data.get('texte', [])
    contenu_lines = []
    for item in texte_struct:
        if item.get('type') == 'enumeration':
            contenu_lines.append(f"{item.get('marker')} {item.get('content')}")
        else:
            contenu_lines.append(item.get('content', ''))
            
    contenu_complet = "\n".join(contenu_lines)
    
    # Période de validité : [date_start, infinity)
    # Si date_start est None, on met -infinity ou today ? On met today par défaut si manque.
    if not date_start:
        date_start = date.today().isoformat()
        
    validity = f"[{date_start},)"
    
    sql_version = """
    INSERT INTO article_versions (
        article_id,
        validity_period,
        contenu_texte,
        modifie_par_document_id
    ) VALUES (%s, %s::daterange, %s, %s)
    """
    
    cursor.execute(sql_version, (
        article_id,
        validity,
        contenu_complet,
        doc_id # La version initiale est créée par le document lui-même
    ))

def process_file(filepath: Path):
    """Traite un fichier JSON."""
    print(f"Traitement de {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        conn = get_db_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # Le JSON contient une liste de textes sous la clé "textes"
                    textes = data.get('textes', [])
                    # Ou c'est un fichier d'un seul texte ?
                    # convert_jo_structured produit { "textes": [...] }
                    
                    for texte in textes:
                        insert_legal_document(cur, texte)
                        
            print(f"Succès : {filepath} chargé.")
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Erreur lors du traitement de {filepath}: {e}")
        import traceback
        traceback.print_exc()

def main():
    parser = argparse.ArgumentParser(description="Charge les JSON Mibeko dans PostgreSQL (Nouveau Schema)")
    parser.add_argument("input", nargs='?', default='data/out', help="Fichier JSON ou dossier (défaut: data/out)")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if input_path.is_file():
        process_file(input_path)
    elif input_path.is_dir():
        for json_file in input_path.glob("*.json"):
            process_file(json_file)
    else:
        print("Chemin invalide.")

if __name__ == "__main__":
    main()
