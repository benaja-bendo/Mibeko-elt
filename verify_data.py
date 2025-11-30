import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mibeko")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

def verify_data():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    with conn:
        with conn.cursor() as cur:
            print("\n--- Legal Documents ---")
            cur.execute("SELECT id, type_code, titre_officiel FROM legal_documents LIMIT 5")
            for row in cur.fetchall():
                print(row)
                
            print("\n--- Structure Nodes (Hierarchy) ---")
            cur.execute("SELECT id, type_unite, numero, tree_path FROM structure_nodes ORDER BY tree_path LIMIT 10")
            for row in cur.fetchall():
                print(row)
                
            print("\n--- Articles & Versions ---")
            cur.execute("""
                SELECT a.numero_article, v.contenu_texte 
                FROM articles a 
                JOIN article_versions v ON a.id = v.article_id 
                LIMIT 5
            """)
            for row in cur.fetchall():
                print(f"Article {row[0]}: {row[1][:50]}...")

    conn.close()

if __name__ == "__main__":
    verify_data()
