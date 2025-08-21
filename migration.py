#!/usr/bin/env python3
"""
migrate_descriptions.py
- Connects to Postgres using environment variables
- Normalizes URLs (scheme+netloc+path, lowercased, strip trailing slash)
- For each grant with a non-empty description_long: find matching ngo_profiles by normalized url
  - If ngo_profiles found and description empty -> update description
  - If not found -> insert new ngo_profiles row with description
"""

import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()  # expects .env in project root

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def normalize_url(u: str) -> str:
    if not u:
        return ""
    u = u.strip()
    # If missing scheme, assume https for normalization
    if not re.match(r'^[a-zA-Z]+://', u):
        u = "https://" + u
    try:
        p = urlparse(u)
        path = p.path or ""
        # drop trailing slashes
        path = re.sub(r'/+$', '', path)
        norm = f"{p.netloc.lower()}{path}".strip()
        return norm
    except Exception:
        return u.lower().rstrip('/')

def main():
    conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS,
                            host=DB_HOST, port=DB_PORT)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch grants that have description_long
    cur.execute("""
        SELECT link, title, description_long, application_deadline, is_active
        FROM grants
        WHERE description_long IS NOT NULL AND trim(description_long) <> ''
    """)
    grants = cur.fetchall()
    print(f"[+] Grants with descriptions fetched: {len(grants)}")

    # Build a map of normalized ngo_profile URLs to their id + description status
    cur.execute("SELECT id, url, description FROM ngo_profiles")
    profiles = cur.fetchall()
    profile_map = {}
    for p in profiles:
        profile_map[normalize_url(p['url'])] = p

    updated = 0
    inserted = 0
    for g in grants:
        norm_g = normalize_url(g['link'])
        desc = g['description_long']
        now_vals = (g['application_deadline'], g['is_active'] if 'is_active' in g else True)

        if norm_g in profile_map:
            p = profile_map[norm_g]
            if not p['description'] or str(p['description']).strip() == '':
                cur.execute("""
                    UPDATE ngo_profiles
                    SET description = %s, title = COALESCE(title, %s), application_deadline = COALESCE(application_deadline, %s),
                        is_active = COALESCE(is_active, %s), updated_at = NOW()
                    WHERE id = %s
                """, (desc, g['title'], g['application_deadline'], g.get('is_active', True), p['id']))
                updated += 1
        else:
            # Insert new row
            cur.execute("""
                INSERT INTO ngo_profiles (url, title, description, application_deadline, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (url) DO NOTHING
                RETURNING id
            """, (g['link'], g['title'], desc, g['application_deadline'], g.get('is_active', True)))
            r = cur.fetchone()
            if r:
                inserted += 1
            # add to profile_map to avoid duplicates in same run
            profile_map[norm_g] = {'id': r['id'] if r else None, 'url': g['link'], 'description': desc}

    conn.commit()
    cur.close()
    conn.close()
    print(f"[+] Updated descriptions: {updated}, Inserted new profiles: {inserted}")

if __name__ == "__main__":
    main()
