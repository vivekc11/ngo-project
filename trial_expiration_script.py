# import os
# import re
# import psycopg2
# import dateparser
# from psycopg2.extras import RealDictCursor
# from datetime import datetime, timezone
# from typing import Dict, Any, List, Optional
# from dotenv import load_dotenv

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

# def fetch_expired_grants() -> List[Dict]:
#     """Fetches all grants from the 'expired_grants' table for processing."""
#     conn = None
#     try:
#         conn = get_connection()
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute("SELECT * FROM expired_grants;")
#             return cur.fetchall()
#     except Exception as e:
#         print(f"Error fetching expired grants: {e}")
#         return []
#     finally:
#         if conn:
#             conn.close()

# def parse_deadline_from_text(text: str) -> Optional[datetime]:
#     """
#     Extracts and parses a datetime object from a text string using dateparser.
#     This is now a more robust function.
#     """
#     # Use a case-insensitive regex to find the 'Deadline:' line
#     deadline_pattern = re.compile(r'deadline:(.*?)\n', re.IGNORECASE | re.DOTALL)
#     match = deadline_pattern.search(text)
    
#     if match:
#         deadline_text_raw = match.group(1).strip()
        
#         # Check for the "Ongoing Opportunity" special case
#         if "ongoing" in deadline_text_raw.lower():
#             return "Ongoing"
        
#         # Use dateparser for robust date extraction
#         parsed_date = dateparser.parse(deadline_text_raw, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
#         return parsed_date
        
#     return None

# def process_grant_expiration(grant: Dict):
#     """
#     Checks if a grant has expired and moves or updates it accordingly, with verbose logging.
#     """
#     deadline = parse_deadline_from_text(grant.get("description_long", ""))
    
#     conn = None
#     try:
#         conn = get_connection()
#         with conn.cursor() as cur:
#             if deadline == "Ongoing":
#                 print(f"✅ Date parsed successfully for '{grant['title']}': {deadline}")
#                 cur.execute("""
#                     INSERT INTO grants (link_hash, link, title, description_short, description_long,
#                                        application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
#                                        min_budget, max_budget, currency, keywords, source, sdg_tags, is_active, scraped_at, updated_at)
#                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
#                     DELETE FROM expired_grants WHERE link_hash = %s;
#                 """, (
#                     grant['link_hash'], grant['link'], grant['title'], grant['description_short'], grant['description_long'],
#                     None, grant['focus_areas'], grant['target_beneficiaries'], grant['geographic_eligibility'],
#                     grant['min_budget'], grant['max_budget'], grant['currency'], grant['keywords'], grant['source'],
#                     grant['sdg_tags'], True, grant['scraped_at'], datetime.now(timezone.utc), grant['link_hash']
#                 ))
#                 conn.commit()
#                 print(f"🔄 Moved '{grant['title']}' to main grants table (Deadline: Ongoing)")
            
#             elif deadline and deadline > datetime.now(timezone.utc):
#                 print(f"✅ Date parsed successfully for '{grant['title']}': {deadline.date()}")
#                 cur.execute("""
#                     INSERT INTO grants (link_hash, link, title, description_short, description_long,
#                                        application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
#                                        min_budget, max_budget, currency, keywords, source, sdg_tags, is_active, scraped_at, updated_at)
#                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
#                     UPDATE grants SET application_deadline = %s WHERE link_hash = %s;
#                     DELETE FROM expired_grants WHERE link_hash = %s;
#                 """, (
#                     grant['link_hash'], grant['link'], grant['title'], grant['description_short'], grant['description_long'],
#                     deadline, grant['focus_areas'], grant['target_beneficiaries'], grant['geographic_eligibility'],
#                     grant['min_budget'], grant['max_budget'], grant['currency'], grant['keywords'], grant['source'],
#                     grant['sdg_tags'], True, grant['scraped_at'], datetime.now(timezone.utc),
#                     deadline, grant['link_hash'], grant['link_hash']
#                 ))
#                 conn.commit()
#                 print(f"🔄 Moved '{grant['title']}' to main grants table and updated deadline (New Deadline: {deadline.date()})")
            
#             elif deadline and deadline < datetime.now(timezone.utc):
#                 print(f"✅ Date parsed successfully for '{grant['title']}': {deadline.date()}")
#                 cur.execute("""
#                     UPDATE expired_grants SET is_active = FALSE WHERE link_hash = %s;
#                 """, (grant['link_hash'],))
#                 conn.commit()
#                 print(f"✅ Confirmed expired for '{grant['title']}': Set is_active to FALSE")
            
#             else:
#                 print(f"⚠️ Could not find a valid deadline for '{grant['title']}': No action taken.")

#     except psycopg2.errors.UniqueViolation as e:
#         conn.rollback()
#         try:
#             cur.execute("""
#                 DELETE FROM expired_grants WHERE link_hash = %s;
#             """, (grant['link_hash'],))
#             conn.commit()
#             print(f"🔄 Grant '{grant['title']}' already exists in main table; deleting from expired.")
#         except Exception as e:
#             print(f"Error during rollback deletion of grant {grant['link_hash']}: {e}")
#             if conn:
#                 conn.rollback()

#     except Exception as e:
#         print(f"Error processing grant {grant['link_hash']}: {e}")
#         if conn:
#             conn.rollback()
#     finally:
#         if conn:
#             conn.close()

# def process_expired_grants_table():
#     grants_to_process = fetch_expired_grants()
#     print(f"Found {len(grants_to_process)} grants in the expired table to process.")
#     for grant in grants_to_process:
#         process_grant_expiration(grant)
#     print("Processing complete.")

# if __name__ == "__main__":
#     process_expired_grants_table()


import os
import re
import psycopg2
import dateparser
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

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

# --- CORE LOGIC FUNCTIONS ---

def fetch_expired_grants() -> List[Dict]:
    """Fetches all grants from the 'expired_grants' table for processing."""
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM expired_grants;")
            return cur.fetchall()
    except Exception as e:
        print(f"Error fetching expired grants: {e}")
        return []
    finally:
        if conn:
            conn.close()

def parse_deadline_from_text(text: str) -> Optional[datetime]:
    """
    Extracts and parses a datetime object from a text string, without a strict 'Deadline:' prefix.
    This function is more forgiving to handle various text structures.
    """
    # Look for the word 'deadline' and grab the following text
    deadline_pattern = re.compile(r'deadline[^\n]*', re.IGNORECASE | re.DOTALL)
    match = deadline_pattern.search(text)
    
    if match:
        deadline_text_raw = match.group(0).strip()
        
        # Check for the "Ongoing Opportunity" special case
        if "ongoing" in deadline_text_raw.lower():
            return "Ongoing"
        
        # Use dateparser to extract the date from the text string
        parsed_date = dateparser.parse(deadline_text_raw, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
        return parsed_date
        
    return None

def process_expired_grants_table():
    """
    Processes all grants in the 'expired_grants' table to validate their deadlines.
    Moves grants back to the main 'grants' table if they are not truly expired.
    """
    grants_to_process = fetch_expired_grants()
    print(f"Found {len(grants_to_process)} grants in the expired table to process.")

    for grant in grants_to_process:
        deadline = parse_deadline_from_text(grant.get("description_long", ""))
        
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                if deadline:
                    print(f"✅ Date parsed successfully for '{grant['title']}': {deadline}")
                
                if deadline == "Ongoing":
                    # Re-insert into main grants table with NULL deadline
                    cur.execute("""
                        INSERT INTO grants (link_hash, link, title, description_short, description_long,
                                           application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
                                           min_budget, max_budget, currency, keywords, source, sdg_tags, is_active, scraped_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        DELETE FROM expired_grants WHERE link_hash = %s;
                    """, (
                        grant['link_hash'], grant['link'], grant['title'], grant['description_short'], grant['description_long'],
                        None, grant['focus_areas'], grant['target_beneficiaries'], grant['geographic_eligibility'],
                        grant['min_budget'], grant['max_budget'], grant['currency'], grant['keywords'], grant['source'],
                        grant['sdg_tags'], True, grant['scraped_at'], datetime.now(timezone.utc), grant['link_hash']
                    ))
                    conn.commit()
                    print(f"🔄 Moved '{grant['title']}' to main grants table (Deadline: Ongoing)")
                
                elif deadline and deadline > datetime.now(timezone.utc):
                    # Re-insert into main grants table and update deadline
                    cur.execute("""
                        INSERT INTO grants (link_hash, link, title, description_short, description_long,
                                           application_deadline, focus_areas, target_beneficiaries, geographic_eligibility,
                                           min_budget, max_budget, currency, keywords, source, sdg_tags, is_active, scraped_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                        UPDATE grants SET application_deadline = %s WHERE link_hash = %s;
                        DELETE FROM expired_grants WHERE link_hash = %s;
                    """, (
                        grant['link_hash'], grant['link'], grant['title'], grant['description_short'], grant['description_long'],
                        deadline, grant['focus_areas'], grant['target_beneficiaries'], grant['geographic_eligibility'],
                        grant['min_budget'], grant['max_budget'], grant['currency'], grant['keywords'], grant['source'],
                        grant['sdg_tags'], True, grant['scraped_at'], datetime.now(timezone.utc),
                        deadline, grant['link_hash'], grant['link_hash']
                    ))
                    conn.commit()
                    print(f"🔄 Moved '{grant['title']}' to main grants table and updated deadline (New Deadline: {deadline.date()})")
                
                elif deadline and deadline < datetime.now(timezone.utc):
                    # Update is_active to false
                    cur.execute("""
                        UPDATE expired_grants SET is_active = FALSE WHERE link_hash = %s;
                    """, (grant['link_hash'],))
                    conn.commit()
                    print(f"✅ Confirmed expired for '{grant['title']}': Set is_active to FALSE")
                
                else:
                    print(f"⚠️ Could not find a valid deadline for '{grant['title']}': No action taken.")

        except psycopg2.errors.UniqueViolation as e:
            conn.rollback()
            try:
                cur.execute("""
                    DELETE FROM expired_grants WHERE link_hash = %s;
                """, (grant['link_hash'],))
                conn.commit()
                print(f"🔄 Grant '{grant['title']}' already exists in main table; deleting from expired.")
            except Exception as e:
                print(f"Error during rollback deletion of grant {grant['link_hash']}: {e}")
                if conn:
                    conn.rollback()

        except Exception as e:
            print(f"Error processing grant {grant['link_hash']}: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

if __name__ == "__main__":
    process_expired_grants_table()