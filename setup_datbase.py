# setup_database.py

import psycopg2
from config import settings

def setup():
    conn = psycopg2.connect(
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT
    )
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS raw_pages (
        url TEXT PRIMARY KEY,
        html TEXT NOT NULL,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS raw_grants (
        url TEXT PRIMARY KEY,
        html TEXT NOT NULL,
        scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS grants (
        id SERIAL PRIMARY KEY,
        title TEXT,
        url TEXT UNIQUE,
        deadline TEXT,
        description TEXT,
        eligibility TEXT,
        amount TEXT,
        source TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables created.")

if __name__ == "__main__":
    setup()
