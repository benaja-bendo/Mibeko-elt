import psycopg2
import os

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "laravel-mibeko")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "root")

def apply_schema():
    print("Connecting to database...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    with open('database/schema_postgres.sql', 'r') as f:
        schema_sql = f.read()
        
    print("Applying schema...")
    with conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            
    conn.close()
    print("Schema applied successfully.")

if __name__ == "__main__":
    apply_schema()
