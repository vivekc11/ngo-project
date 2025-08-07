# grants_db.py
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
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
    """Establishes a connection to the PostgreSQL database."""
    return psycopg2.connect(**DB_CONFIG)

def insert_grant(grant: Dict) -> bool:
    """
    Inserts a new grant into the 'grants' table.
    Returns True on successful insertion, False otherwise.
    """
    query: str = """
        INSERT INTO grants (
            link_hash, link, title, description_short, description_long,
            application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
            min_budget, max_budget, keywords, source, sdg_tags, is_active
        )
        VALUES (
            %(link_hash)s, %(link)s, %(title)s, %(description_short)s, %(description_long)s,
            %(application_deadline)s, %(focus_areas)s, %(target_beneficiaries)s, %(geographic_eligibility)s,
            %(min_budget)s, %(max_budget)s, %(keywords)s, %(source)s, %(sdg_tags)s, %(is_active)s
        )
        ON CONFLICT (link_hash) DO NOTHING;
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, grant)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error inserting grant: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def update_grant(grant: Dict) -> bool:
    """
    Updates an existing grant in the database based on its link_hash.
    Returns True if the grant was updated, False otherwise.
    """
    set_clauses: List[str] = []
    update_data: Dict = {}
    for key, value in grant.items():
        if key not in ['link_hash', 'scraped_at']:
            set_clauses.append(f"{key} = %({key})s")
            update_data[key] = value

    if not set_clauses:
        return False

    query: str = f"""
        UPDATE grants
        SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
        WHERE link_hash = %(link_hash)s;
    """
    update_data['link_hash'] = grant['link_hash']

    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(query, update_data)
        conn.commit()
        return cur.rowcount > 0
    except Exception as e:
        print(f"Error updating grant (link_hash: {grant.get('link_hash')}): {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def fetch_all_grants() -> List[Dict]:
    """Fetches all grants from the database, ordered by application_deadline descending."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM grants ORDER BY application_deadline DESC;")
                return cur.fetchall()
    except Exception as e:
        print(f"Error fetching all grants: {e}")
        return []

def fetch_grant_by_link_hash(link_hash: str) -> Optional[Dict]:
    """Fetches a single grant from the database by its unique link_hash."""
    try:
        with get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM grants WHERE link_hash = %s;", (link_hash,))
                return cur.fetchone()
    except Exception as e:
        print(f"Error fetching grant by link hash '{link_hash}': {e}")
        return None