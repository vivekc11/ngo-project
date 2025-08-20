# import os
# import re
# import psycopg2
# import dateparser
# from psycopg2.extras import RealDictCursor
# from datetime import datetime, timezone
# from typing import Dict, Any, List, Optional
# from dotenv import load_dotenv

# # Load environment variables from .env file
# load_dotenv()

# # --- DATABASE CONFIGURATION ---
# DB_CONFIG: Dict[str, Any] = {
#     "dbname": os.getenv("DB_NAME"),
#     "user": os.getenv("DB_USER"),
#     "password": os.getenv("DB_PASSWORD"),
#     "host": os.getenv("DB_HOST", "localhost"),
#     "port": os.getenv("DB_PORT", 5432)
# }

# def get_connection():
#     """Establishes a connection to the PostgreSQL database."""
#     return psycopg2.connect(**DB_CONFIG)

# # --- CORE LOGIC FUNCTIONS ---

# def fetch_grants_with_null_deadline() -> List[Dict]:
#     """Fetches grants with a NULL application_deadline from the 'grants' table."""
#     conn = None
#     try:
#         conn = get_connection()
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute("SELECT * FROM grants WHERE application_deadline IS NULL;")
#             return cur.fetchall()
#     except Exception as e:
#         print(f"Error fetching grants with NULL deadline: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def parse_deadline_from_text(text: str) -> Optional[datetime]:
#     """
#     Extracts and parses a datetime object from a text string, handling a variety of keywords.
#     """
#     if not text:
#         return None

#     # Normalize whitespace to handle inconsistent spacing and newlines
#     normalized_text = re.sub(r'\s+', ' ', text).strip()

#     # Regex to find flexible deadline phrases and grab the following text
#     deadline_pattern = re.compile(
#         r'(?:deadline|closing date|due date)[^:\n]*:?\s*(?P<deadline_str>[\w\s,-]+)(?:\.|\n|$)', 
#         re.IGNORECASE | re.DOTALL
#     )
#     match = deadline_pattern.search(normalized_text)

#     if match:
#         deadline_text_raw = match.group('deadline_str').strip()

#         # Handle the "Ongoing" special case
#         if "ongoing" in deadline_text_raw.lower():
#             return "Ongoing"

#         # Use dateparser for robust date extraction
#         parsed_date = dateparser.parse(
#             deadline_text_raw, 
#             settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True}
#         )
#         return parsed_date

#     return None

# def process_and_update_grants():
#     """
#     Processes grants with a NULL deadline and updates or moves them.
#     """
#     grants_to_process = fetch_grants_with_null_deadline()
#     print(f"Found {len(grants_to_process)} grants with a NULL deadline to process.")
    
#     for grant in grants_to_process:
#         deadline = parse_deadline_from_text(grant.get("description_long", ""))
        
#         conn = None
#         try:
#             conn = get_connection()
#             with conn.cursor() as cur:
#                 if deadline == "Ongoing":
#                     cur.execute("""
#                         UPDATE grants SET is_active = TRUE, application_deadline = NULL WHERE link_hash = %s;
#                     """, (grant["link_hash"],))
#                     conn.commit()
#                     print(f"✅ Found an ongoing grant: {grant['title']}. Updated 'is_active' and set deadline to NULL.")
                
#                 elif deadline and deadline < datetime.now(timezone.utc):
#                     cur.execute("""
#                         INSERT INTO expired_grants (link_hash, link, title, description_short, description_long,
#                                                    application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
#                                                    min_budget, max_budget, currency, keywords, source, sdg_tags, is_active, scraped_at, updated_at)
#                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
#                         DELETE FROM grants WHERE link_hash = %s;
#                     """, (
#                         grant['link_hash'], grant['link'], grant['title'], grant['description_short'], grant['description_long'],
#                         deadline, grant['focus_areas'], grant['target_beneficiaries'], grant['geographic_eligibility'],
#                         grant['min_budget'], grant['max_budget'], grant['currency'], grant['keywords'], grant['source'],
#                         grant['sdg_tags'], False, grant['scraped_at'], datetime.now(timezone.utc), grant['link_hash']
#                     ))
#                     conn.commit()
#                     print(f"✅ Moved to expired: {grant['title']} (Deadline: {deadline.date()})")

#                 elif deadline:
#                     cur.execute("""
#                         UPDATE grants SET application_deadline = %s WHERE link_hash = %s;
#                     """, (deadline, grant["link_hash"]))
#                     conn.commit()
#                     print(f"🔄 Updated deadline for: {grant['title']} (New Deadline: {deadline.date()})")

#                 else:
#                     print(f"⚠️ Could not find a valid deadline for: {grant['title']}. No action taken.")
        
#         except psycopg2.errors.UniqueViolation as e:
#             conn.rollback()
#             print(f"⚠️ Duplicate grant found: {grant['title']}. Skipping.")
#         except Exception as e:
#             print(f"Error processing grant {grant['link_hash']}: {e}")
#             if conn:
#                 conn.rollback()
#         finally:
#             if conn:
#                 conn.close()

# if __name__ == "__main__":
#     process_and_update_grants()



import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from typing import Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- DATABASE CONFIGURATION ---
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

def fetch_grants_with_null_deadline() -> List[Dict]:
    """Fetches grants with a NULL application_deadline from the 'grants' table."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM grants WHERE application_deadline IS NULL;")
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching grants with NULL deadline: {e}")
        return []
    finally:
        if conn:
            conn.close()

def move_broken_grants():
    """
    Moves grants with a NULL deadline from the 'grants' table to the 'broken_grants' table.
    """
    grants_to_move = fetch_grants_with_null_deadline()
    print(f"Found {len(grants_to_move)} grants with a NULL deadline to move.")
    
    for grant in grants_to_move:
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                # Insert the record into the broken_grants table
                cur.execute("""
                    INSERT INTO broken_grants (link_hash, link, title, description_short, description_long,
                                               application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
                                               min_budget, max_budget, currency, keywords, source, sdg_tags, is_active, scraped_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    grant['link_hash'], grant['link'], grant['title'], grant['description_short'], grant['description_long'],
                    grant['application_deadline'], grant['focus_areas'], grant['target_beneficiaries'], grant['geographic_eligibility'],
                    grant['min_budget'], grant['max_budget'], grant['currency'], grant['keywords'], grant['source'],
                    grant['sdg_tags'], grant['is_active'], grant['scraped_at'], grant['updated_at']
                ))

                # Delete the record from the grants table
                cur.execute("DELETE FROM grants WHERE link_hash = %s;", (grant['link_hash'],))
                conn.commit()

                print(f"✅ Moved grant '{grant['title']}' to broken_grants.")

        except Exception as e:
            print(f"Error moving grant {grant['link_hash']}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    print("Processing complete.")

if __name__ == "__main__":
    move_broken_grants()