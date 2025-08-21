# setup_database.py
"""
Creates/ensures pgvector extension and embedding column + index.
Run once before populating embeddings.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", 1024))

CONN_STR = f"dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD} host={DB_HOST} port={DB_PORT}"

DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column if missing (vector type)
ALTER TABLE grants
    ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM});

-- Optional: create a lightweight ngo_profiles table
CREATE TABLE IF NOT EXISTS ngo_profiles (
    id serial PRIMARY KEY,
    url text UNIQUE NOT NULL,
    summary text,
    raw_text text,
    created_at timestamptz DEFAULT now(),
    embedding vector({EMBEDDING_DIM})
);

-- Create an IVF index for approximate nearest neighbor search (fast).
-- Note: ivfflat works best after you populate embeddings and run VACUUM ANALYZE.
CREATE INDEX IF NOT EXISTS idx_grants_embedding_ivfflat
    ON grants USING ivfflat (embedding) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_ngo_profiles_embedding_ivfflat
    ON ngo_profiles USING ivfflat (embedding) WITH (lists = 100);
"""

def run():
    conn = None
    try:
        conn = psycopg2.connect(CONN_STR)
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(DDL)
        print("✅ Database prepared: extension/columns/indexes created (or already present).")
    except Exception as e:
        print("❌ Error preparing database:", e)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run()
