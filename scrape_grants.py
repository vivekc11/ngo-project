import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone # Added timezone
import re
import time
from typing import List, Dict, Optional # Corrected and added typing imports

from grants_db import insert_grant, update_grant, fetch_grant_by_link_hash
from utils import generate_link_hash, preprocess_text, nlp
from sdg_classifier import SDGClassifier

def scrape_fundsforngos(limit: int = 5) -> int:
    """
    Scrapes the latest grants from fundsforngos.org.
    For each grant:
    - Generates a link hash.
    - Classifies the grant's text for SDG tags.
    - Stores or updates the grant in the PostgreSQL database.
    """
    base_url: str = "https://www2.fundsforngos.org/" # Added type hint
    latest_grants_url: str = urljoin(base_url, "category/latest-funds-for-ngos/") # Added type hint
    headers: Dict[str, str] = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36)"} # Added type hint

    sdg_classifier: SDGClassifier = SDGClassifier() # Added type hint

    try:
        print(f"Attempting to scrape from: {latest_grants_url}")
        response = requests.get(latest_grants_url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("article.post")
        grants_processed_count: int = 0 # Added type hint

        for article in articles:
            if grants_processed_count >= limit:
                break

            title_tag = article.select_one("h2.entry-title a")
            link_tag = title_tag
            description_short_tag = article.select_one("div.entry-summary p")

            deadline_text_raw: Optional[str] = article.find(string=re.compile(r"(deadline|apply by)", re.IGNORECASE)) # Added type hint
            deadline: Optional[datetime] = None
            if deadline_text_raw:
                date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', deadline_text_raw)
                if not date_match:
                     date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', deadline_text_raw, re.IGNORECASE)
                if date_match:
                    try:
                        if '-' in date_match.group(0):
                            deadline = datetime.strptime(date_match.group(0), '%Y-%m-%d')
                        else:
                            deadline = datetime.strptime(date_match.group(0), '%B %d, %Y')
                        # Make deadline timezone aware if possible, e.g., assume UTC if not specified
                        if deadline and deadline.tzinfo is None:
                            deadline = deadline.replace(tzinfo=timezone.utc)
                    except ValueError:
                        deadline = None

            if link_tag and description_short_tag:
                title: str = title_tag.get_text(strip=True) # Added type hint
                link: str = link_tag['href'] # Added type hint
                link_hash: str = generate_link_hash(link) # Added type hint
                description_short: str = description_short_tag.get_text(strip=True) # Added type hint

                description_long: str = "" # Added type hint

                text_for_sdg_classification: str = f"{title} {description_short} {description_long}" # Added type hint
                sdg_tags: List[str] = sdg_classifier.classify_text(text_for_sdg_classification) # Added type hint

                grant_data: Dict = {
                    "link_hash": link_hash,
                    "link": link,
                    "title": title,
                    "description_short": description_short,
                    "description_long": description_long,
                    "application_deadline": deadline,
                    "focus_areas": [],
                    "target_beneficiaries": [],
                    "geographic_eligibility": [],
                    "min_budget": None,
                    "max_budget": None,
                    "keywords": [],
                    "source": "FundsforNGOs",
                    "sdg_tags": sdg_tags,
                    "is_active": True
                }

                existing_grant: Optional[Dict] = fetch_grant_by_link_hash(link_hash) # Added type hint
                if not existing_grant:
                    if insert_grant(grant_data):
                        print(f"-> Inserted new grant: '{title}' (SDGs: {', '.join(sdg_tags)})")
                        grants_processed_count += 1
                else:
                    print(f"-> Grant already exists: '{title}' (link_hash: {link_hash}), skipping insertion.")
            
            time.sleep(1.5)
            
        return grants_processed_count

    except requests.exceptions.RequestException as e:
        print(f"[Scraper HTTP/Network Error]: A network or HTTP error occurred during scraping: {e}")
        return 0
    except Exception as e:
        print(f"[Scraper General Error]: An unexpected error occurred during scraping: {e}")
        return 0

if __name__ == "__main__":
    print("\n" + "="*50)
    print("Starting NGO Grant Scraper (FundsforNGOs.org)")
    print("This will fetch grants, classify SDGs, and store them in your DB.")
    print("="*50 + "\n")
    num_scraped = scrape_fundsforngos(limit=10)
    print(f"\nFinished scraping process. {num_scraped} new grants attempted to be stored.")
    print("="*50 + "\n")