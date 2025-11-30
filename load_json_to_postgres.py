#!/usr/bin/env python3
"""
Script de chargement des données JSON vers PostgreSQL.
Ce script lit les fichiers JSON générés par md_to_json_converter.py et les insère
dans la base de données PostgreSQL définie par schema_postgres.sql.
"""

import json
import os
import psycopg2
from psycopg2.extras import Json
from pathlib import Path
import argparse
from typing import Dict, Any, Optional, List

# Configuration de la base de données (à modifier ou passer en variables d'env)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mibeko")
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

def insert_publication(cursor, pub_data: Dict[str, Any]):
    """Insère ou met à jour une publication."""
    sql = """
    INSERT INTO publications (id, numero_parution, date_parution, annee, titre)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        numero_parution = EXCLUDED.numero_parution,
        date_parution = EXCLUDED.date_parution,
        annee = EXCLUDED.annee,
        titre = EXCLUDED.titre;
    """
    cursor.execute(sql, (
        pub_data.get('id'),
        pub_data.get('numero_parution'),
        pub_data.get('date_parution'),
        pub_data.get('annee'),
        pub_data.get('titre')
    ))

def insert_texte(cursor, texte: Dict[str, Any], publication_id: str):
    """Insère un texte légal et ses composants."""
    texte_id = texte.get('id')
    
    # 1. Insertion du texte principal
    sql_texte = """
    INSERT INTO textes (id, publication_id, type_texte, numero, date_texte, titre, contenu, preambule, page_debut)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        titre = EXCLUDED.titre,
        contenu = EXCLUDED.contenu,
        preambule = EXCLUDED.preambule;
    """
    cursor.execute(sql_texte, (
        texte_id,
        publication_id,
        texte.get('type_texte'),
        texte.get('numero'),
        texte.get('date'),
        texte.get('titre'),
        texte.get('contenu'),
        texte.get('preambule'),
        texte.get('page_debut')
    ))

    # 2. Gestion de la structure hiérarchique
    structure = texte.get('structure', {})
    
    # Titres
    for i, titre in enumerate(structure.get('titres', [])):
        titre_id = insert_titre(cursor, texte_id, titre, i)
        # Chapitres dans Titre
        for j, chapitre in enumerate(titre.get('chapitres', [])):
            chapitre_id = insert_chapitre(cursor, texte_id, chapitre, j, titre_id=titre_id)
            # Sections dans Chapitre
            for k, section in enumerate(chapitre.get('sections', [])):
                section_id = insert_section(cursor, texte_id, section, k, chapitre_id=chapitre_id, titre_id=titre_id)
                # Articles dans Section
                insert_articles_list(cursor, texte_id, section.get('articles', []), titre_id, chapitre_id, section_id)
            # Articles dans Chapitre (directs)
            insert_articles_list(cursor, texte_id, chapitre.get('articles', []), titre_id, chapitre_id, None)
        # Articles dans Titre (directs)
        insert_articles_list(cursor, texte_id, titre.get('articles', []), titre_id, None, None)

    # Chapitres (hors Titres)
    for i, chapitre in enumerate(structure.get('chapitres', [])):
        chapitre_id = insert_chapitre(cursor, texte_id, chapitre, i, titre_id=None)
        # Sections dans Chapitre
        for j, section in enumerate(chapitre.get('sections', [])):
            section_id = insert_section(cursor, texte_id, section, j, chapitre_id=chapitre_id, titre_id=None)
            # Articles dans Section
            insert_articles_list(cursor, texte_id, section.get('articles', []), None, chapitre_id, section_id)
        # Articles dans Chapitre (directs)
        insert_articles_list(cursor, texte_id, chapitre.get('articles', []), None, chapitre_id, None)

    # Sections (hors Chapitres/Titres)
    for i, section in enumerate(structure.get('sections', [])):
        section_id = insert_section(cursor, texte_id, section, i, chapitre_id=None, titre_id=None)
        # Articles dans Section
        insert_articles_list(cursor, texte_id, section.get('articles', []), None, None, section_id)

    # Articles (directs dans Texte)
    insert_articles_list(cursor, texte_id, structure.get('articles', []), None, None, None)

    # 3. Signataires
    for signataire in texte.get('signataires', []):
        cursor.execute("""
        INSERT INTO signataires (texte_id, nom, fonction, pour)
        VALUES (%s, %s, %s, %s)
        """, (texte_id, signataire.get('nom'), signataire.get('fonction'), signataire.get('pour')))

    # 4. Références
    for ref in texte.get('references', []):
        cursor.execute("""
        INSERT INTO references_texte (texte_id, type_reference, contenu_reference)
        VALUES (%s, %s, %s)
        """, (texte_id, ref.get('type_texte'), ref.get('reference')))

def insert_titre(cursor, texte_id, titre_data, ordre):
    sql = """
    INSERT INTO titres (texte_id, numero, intitule, contenu_libre, ordre)
    VALUES (%s, %s, %s, %s, %s)
    RETURNING id;
    """
    cursor.execute(sql, (
        texte_id,
        titre_data.get('numero'),
        titre_data.get('intitule'),
        titre_data.get('contenu_libre'),
        ordre
    ))
    return cursor.fetchone()[0]

def insert_chapitre(cursor, texte_id, chap_data, ordre, titre_id=None):
    sql = """
    INSERT INTO chapitres (texte_id, titre_id, numero, titre, contenu_libre, ordre)
    VALUES (%s, %s, %s, %s, %s, %s)
    RETURNING id;
    """
    cursor.execute(sql, (
        texte_id,
        titre_id,
        chap_data.get('numero'),
        chap_data.get('titre'),
        chap_data.get('contenu_libre'),
        ordre
    ))
    return cursor.fetchone()[0]

def insert_section(cursor, texte_id, section_data, ordre, chapitre_id=None, titre_id=None):
    sql = """
    INSERT INTO sections (texte_id, chapitre_id, titre_id, numero, titre, contenu_libre, ordre)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    RETURNING id;
    """
    cursor.execute(sql, (
        texte_id,
        chapitre_id,
        titre_id,
        section_data.get('numero'),
        section_data.get('titre'),
        section_data.get('contenu_libre'),
        ordre
    ))
    return cursor.fetchone()[0]

def insert_articles_list(cursor, texte_id, articles, titre_id, chapitre_id, section_id):
    """Insère une liste d'articles."""
    if not articles:
        return
        
    sql = """
    INSERT INTO articles (texte_id, titre_id, chapitre_id, section_id, numero, intitule, contenu, ordre)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    for i, article in enumerate(articles):
        cursor.execute(sql, (
            texte_id,
            titre_id,
            chapitre_id,
            section_id,
            article.get('numero'),
            article.get('intitule'),
            article.get('contenu'),
            i
        ))

def process_file(filepath: Path):
    """Traite un fichier JSON unique."""
    print(f"Traitement de {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        conn = get_db_connection()
        try:
            with conn:
                with conn.cursor() as cur:
                    # Insertion Publication
                    insert_publication(cur, data)
                    
                    # Insertion Textes
                    for texte in data.get('textes', []):
                        insert_texte(cur, texte, data.get('id'))
                        
            print(f"Succès : {filepath} chargé dans la base.")
        finally:
            conn.close()
            
    except Exception as e:
        print(f"Erreur lors du traitement de {filepath}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Charge les fichiers JSON Mibeko dans PostgreSQL")
    parser.add_argument("input", help="Fichier JSON ou dossier contenant les JSON")
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
