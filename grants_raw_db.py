# grants_raw_db.py

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import Dict, Optional, Any, List
from datetime import datetime

load_dotenv()

DB_CONFIG: Dict[str, Any] = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432)
}

def get_connection():
    """Establishes a connection to the 'raw_scraped_db' database."""
    return psycopg2.connect(**DB_CONFIG)

def create_tables() -> bool:
    """Creates the raw_pages and raw_grants tables."""
    raw_pages_query: str = """
        CREATE TABLE IF NOT EXISTS raw_pages (
            url TEXT PRIMARY KEY,
            html TEXT NOT NULL,
            scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """
    raw_grants_query: str = """
        CREATE TABLE IF NOT EXISTS raw_grants (
            url TEXT PRIMARY KEY,
            html TEXT,  -- Changed to be nullable
            scraped_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(raw_pages_query)
            cur.execute(raw_grants_query)
        conn.commit()
        print("✅ Raw pages and raw grants tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def insert_raw_page(url: str, html: str) -> bool:
    """Inserts raw HTML of a listing page into 'raw_pages' table."""
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
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error inserting raw page for {url}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_all_raw_pages() -> List[Dict]:
    """Fetches all raw listing page records from the 'raw_pages' table."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT url, html FROM raw_pages ORDER BY scraped_at DESC;")
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching all raw pages: {e}")
        return []
    finally:
        if conn:
            conn.close()

def insert_raw_grant(url: str, html: str) -> bool:
    """Inserts raw HTML of a grant page into 'raw_grants' table.
    The html parameter can be an empty string if the content is not yet scraped.
    """
    query: str = """
        INSERT INTO raw_grants (url, html)
        VALUES (%s, %s)
        ON CONFLICT (url) DO NOTHING;
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (url, html))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error inserting raw grant for {url}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def update_raw_grant_html(url: str, html: str) -> bool:
    """Updates the raw HTML of a grant page in 'raw_grants' table."""
    query: str = """
        UPDATE raw_grants
        SET html = %s, scraped_at = NOW()
        WHERE url = %s
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, (html, url))
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error updating raw grant for {url}: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_all_raw_grants() -> List[Dict]:
    """Fetches all raw grant records from the 'raw_grants' table."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT url, html FROM raw_grants ORDER BY scraped_at DESC;")
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching all raw grants: {e}")
        return []
    finally:
        if conn:
            conn.close()