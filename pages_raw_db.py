# pages_raw_db.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Dict, Optional, Any

load_dotenv()

DB_CONFIG: Dict[str, str] = {
    "dbname": "raw_scraped_db",
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT", 5432)
}

def get_connection():
    """Establishes a connection to the 'raw_scraped_db' database."""
    return psycopg2.connect(**DB_CONFIG)

def insert_raw_page_html(url: str, html: str) -> bool:
    """
    Inserts the URL and raw HTML of a scraped listing page into the 'raw_pages' table.
    Uses ON CONFLICT DO NOTHING to prevent duplicate insertions for the same URL.
    """
    query: str = """
        INSERT INTO raw_pages (url, html)
        VALUES (%s, %s)
        ON CONFLICT (url) DO NOTHING;
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (url, html))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting raw page for {url}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def fetch_raw_page(url: str) -> Optional[Dict]:
    """Fetches a single raw page record by its URL from 'raw_pages'."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM raw_pages WHERE url = %s;", (url,))
            return cur.fetchone()
    except Exception as e:
        print(f"Error fetching raw page for {url}: {e}")
        return None
    finally:
        if conn:
            conn.close()