# import requests
# from bs4 import BeautifulSoup
# from urllib.parse import urljoin
# from datetime import datetime, timezone
# import re
# import time
# from typing import List, Dict, Optional, Any
# import logging

# from grants_db import insert_grant, update_grant, fetch_grant_by_link_hash
# from utils import generate_link_hash, preprocess_text, nlp, extract_keywords_from_doc # Corrected import for extract_keywords_from_doc
# from sdg_classifier import SDGClassifier
# from logging_setup import setup_logger

# # Setup logger for this script
# logger = setup_logger(__name__)

# # Initialize SDG classifier once
# sdg_classifier = SDGClassifier()

# def _extract_details_from_deep_scrape(soup: BeautifulSoup) -> Dict[str, Any]:
#     """
#     Extracts detailed information from an individual grant page's BeautifulSoup object.
#     Returns a dictionary of extracted details.
#     """
#     details: Dict[str, Any] = {
#         "description_long": "",
#         "application_deadline": None,
#         "focus_areas": [],
#         "target_beneficiaries": [],
#         "geographic_eligibility": [],
#         "min_budget": None,
#         "max_budget": None,
#         "keywords": [],
#     }

#     # Extract full description (main content area)
#     content_div = soup.select_one("div.entry-content[itemprop='text']")
#     if content_div:
#         for tag in content_div(["script", "style", "noscript", "iframe", "div[class*='code-block']"]):
#             tag.decompose()
#         details["description_long"] = content_div.get_text(separator=" ", strip=True)[:15000]

#     # Extract Deadline (more robustly from individual page)
#     deadline_tag = soup.find("strong", text=re.compile(r"Deadline:", re.IGNORECASE))
#     if deadline_tag:
#         deadline_text_raw = deadline_tag.next_sibling
#         if deadline_text_raw and isinstance(deadline_text_raw, str):
#             date_match = re.search(r'\b(\d{1,2}-\w{3}-\d{4})\b', deadline_text_raw, re.IGNORECASE)
#             if not date_match:
#                 date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', deadline_text_raw)
#             if not date_match:
#                 date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', deadline_text_raw, re.IGNORECASE)

#             if date_match:
#                 try:
#                     date_str = date_match.group(0)
#                     if '-' in date_str and date_str.count('-') == 2:
#                         details["application_deadline"] = datetime.strptime(date_str, '%d-%b-%Y').replace(tzinfo=timezone.utc)
#                     elif '-' in date_str and date_str.count('-') == 1:
#                          details["application_deadline"] = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
#                     else:
#                         details["application_deadline"] = datetime.strptime(date_str, '%B %d, %Y').replace(tzinfo=timezone.utc)
#                 except ValueError:
#                     logger.warning(f"Could not parse deadline '{date_str}' from deep scrape.")
#                     details["application_deadline"] = None

#     # Attempt to extract budget information using regex from the long description
#     if details["description_long"]:
#         budgets = re.findall(r'£(\d{1,3}(?:,\d{3})*)|(?:\$|USD)\s*(\d{1,3}(?:,\d{3})*)', details["description_long"])
#         extracted_budgets = []
#         for currency_match in budgets:
#             for amount_str in currency_match:
#                 if amount_str:
#                     try:
#                         extracted_budgets.append(int(amount_str.replace(',', '')))
#                     except ValueError:
#                         pass
#         if extracted_budgets:
#             details["min_budget"] = min(extracted_budgets)
#             details["max_budget"] = max(extracted_budgets)

#     # Attempt to extract focus areas, beneficiaries, eligibility from common headings
#     sections_of_interest: Dict[str, List[str]] = {
#         "focus_areas": [r"Focus Area(?:s)?", r"Thematic Area(?:s)?", r"Priorities"],
#         "target_beneficiaries": [r"Target (?:Beneficiaries|Population|Groups)", r"Who Can Apply"],
#         "geographic_eligibility": [r"Eligib(?:ility|le) Countr(?:y|ies)", r"Geographic Focus", r"Where to Apply"],
#         "keywords": [r"Keywords", r"Tags"]
#     }

#     for field, patterns in sections_of_interest.items():
#         for pattern in patterns:
#             heading = soup.find(re.compile(r"h[3-5]", re.IGNORECASE), text=re.compile(pattern, re.IGNORECASE))
#             if heading:
#                 current_element = heading.next_sibling
#                 section_text: List[str] = []
#                 while current_element and current_element.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'p', 'footer']:
#                     if current_element.name in ['ul', 'ol']:
#                         for li in current_element.find_all('li'):
#                             item_text = li.get_text(separator=' ', strip=True)
#                             if item_text:
#                                 section_text.append(item_text)
#                     elif current_element.name == 'p':
#                          paragraph_text = current_element.get_text(separator=' ', strip=True)
#                          if paragraph_text:
#                             section_text.append(paragraph_text)
#                     current_element = current_element.next_sibling
                
#                 if section_text:
#                     combined_section: str = " ".join(section_text)
#                     if field in ["focus_areas", "target_beneficiaries", "geographic_eligibility", "keywords"]:
#                         extracted_items: List[str] = [item.strip() for item in re.split(r'[,;•–-]', combined_section) if item.strip()]
#                         extracted_items = [item for item in extracted_items if len(item) > 2 and "and" not in item.lower()]
#                         details[field] = list(set(extracted_items))

#                 break

#     if not details["keywords"] and nlp and details["description_long"]:
#         doc = nlp(preprocess_text(details["description_long"]))
#         details["keywords"] = list(extract_keywords_from_doc(doc))

#     return details

# def scrape_fundsforngos(num_pages: int = 3, grants_per_page_limit: Optional[int] = None) -> int:
#     """
#     Scrapes grants from fundsforngos.org, handling pagination and deep-scraping
#     individual grant pages. Stores classified grants in the database.
#     """
#     base_category_url: str = "https://www2.fundsforngos.org/category/latest-funds-for-ngos/"
#     headers: Dict[str, str] = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36)"}

#     total_grants_processed: int = 0

#     for page_num in range(1, num_pages + 1):
#         listing_url: str = urljoin(base_category_url, f"page/{page_num}/")
#         logger.info(f"Attempting to scrape listing page: {listing_url}")

#         try:
#             response = requests.get(listing_url, headers=headers, timeout=20)
#             response.raise_for_status()
#             soup = BeautifulSoup(response.text, "html.parser")

#             articles = soup.select("article.post")
            
#             grants_on_page_count: int = 0
#             for article in articles:
#                 if grants_per_page_limit is not None and grants_on_page_count >= grants_per_page_limit:
#                     logger.info(f"Reached per-page limit ({grants_per_page_limit}) on page {page_num}.")
#                     break

#                 title_tag = article.select_one("h2.entry-title a")
#                 description_short_tag = article.select_one("div.entry-content p") # Corrected selector

#                 if title_tag and description_short_tag:
#                     title: str = title_tag.get_text(strip=True)
#                     link: str = title_tag['href']
#                     link_hash: str = generate_link_hash(link)
#                     description_short: str = description_short_tag.get_text(separator=" ", strip=True)

#                     logger.info(f"Found grant on listing page: '{title}'")
                    
#                     existing_grant: Optional[Dict] = fetch_grant_by_link_hash(link_hash)
#                     if existing_grant and existing_grant.get("description_long"):
#                         logger.info(f"Grant '{title}' already exists with full details. Skipping deep scrape and re-insertion.")
#                         total_grants_processed += 1
#                         grants_on_page_count += 1
#                         continue

#                     deep_scraped_details: Dict[str, Any] = {}
#                     try:
#                         deep_response = requests.get(link, headers=headers, timeout=30)
#                         deep_response.raise_for_status()
#                         deep_soup = BeautifulSoup(deep_response.text, "html.parser")
#                         deep_scraped_details = _extract_details_from_deep_scrape(deep_soup)
#                     except requests.exceptions.RequestException as e:
#                         logger.error(f"HTTP/Network error deep scraping '{link}': {e}")
#                         deep_scraped_details["description_long"] = description_short + " (Full description not available)"
#                         deep_scraped_details["application_deadline"] = None
#                     except Exception as e:
#                         logger.error(f"General error deep scraping '{link}': {e}", exc_info=True)
#                         deep_scraped_details["description_long"] = description_short + " (Full description not available)"
#                         deep_scraped_details["application_deadline"] = None

#                     final_grant_data: Dict = {
#                         "link_hash": link_hash,
#                         "link": link,
#                         "title": title,
#                         "description_short": description_short,
#                         "description_long": deep_scraped_details.get("description_long", ""),
#                         "application_deadline": deep_scraped_details.get("application_deadline"),
#                         "focus_areas": deep_scraped_details.get("focus_areas", []),
#                         "target_beneficiaries": deep_scraped_details.get("target_beneficiaries", []),
#                         "geographic_eligibility": deep_scraped_details.get("geographic_eligibility", []),
#                         "min_budget": deep_scraped_details.get("min_budget"),
#                         "max_budget": deep_scraped_details.get("max_budget"),
#                         "source": "FundsforNGOs",
#                         "is_active": True
#                     }

#                     text_for_sdg_classification: str = f"{final_grant_data['title']} {final_grant_data['description_short']} {final_grant_data['description_long']}"
#                     final_grant_data["sdg_tags"] = sdg_classifier.classify_text(text_for_sdg_classification)

#                     if deep_scraped_details.get("keywords") and len(deep_scraped_details["keywords"]) > 0:
#                         final_grant_data["keywords"] = deep_scraped_details["keywords"]
#                     elif nlp and final_grant_data["description_long"]:
#                         doc_for_keywords = nlp(preprocess_text(final_grant_data["description_long"]))
#                         final_grant_data["keywords"] = list(extract_keywords_from_doc(doc_for_keywords))
#                     else:
#                         final_grant_data["keywords"] = list(set(re.findall(r'\b\w+\b', preprocess_text(final_grant_data["description_short"]))))

#                     if not existing_grant:
#                         if insert_grant(final_grant_data):
#                             logger.info(f"Successfully inserted: '{title}' (SDGs: {', '.join(final_grant_data['sdg_tags'])})")
#                             total_grants_processed += 1
#                             grants_on_page_count += 1
#                         else:
#                             logger.error(f"Failed to insert: '{title}'")
#                     else:
#                         if not existing_grant.get("description_long") or (deep_scraped_details.get("description_long") and len(deep_scraped_details["description_long"]) > len(existing_grant.get("description_long", ""))):
#                             logger.info(f"Updating existing grant: '{title}' with new details.")
#                             if update_grant(final_grant_data):
#                                 logger.info(f"Successfully updated: '{title}'")
#                             else:
#                                 logger.error(f"Failed to update: '{title}'")
#                         else:
#                             logger.info(f"Grant '{title}' already exists with sufficient detail. Skipping update.")
#                         total_grants_processed += 1
#                         grants_on_page_count += 1

#                 time.sleep(2)

#             logger.info(f"Finished processing {grants_on_page_count} grants on page {page_num}.")
#             time.sleep(5)

#         except requests.exceptions.RequestException as e:
#             logger.error(f"[Scraper HTTP/Network Error] Failed to scrape listing page {listing_url}: {e}")
#         except Exception as e:
#             logger.error(f"[Scraper General Error] An unexpected error occurred on listing page {listing_url}: {e}", exc_info=True)

#     return total_grants_processed

# if __name__ == "__main__":
#     logger.info("\n" + "="*80)
#     logger.info("Starting NGO Grant Scraper (FundsforNGOs.org) - Deep Scrape & Pagination")
#     logger.info("This will fetch grants from multiple pages, classify SDGs, and store them in your DB.")
#     logger.info("Existing grants with full details will be skipped.")
#     logger.info("="*80 + "\n")
    
#     num_pages_to_scrape: int = 1
#     grants_limit_per_page: Optional[int] = None

#     num_scraped_and_processed = scrape_fundsforngos(num_pages=num_pages_to_scrape, grants_per_page_limit=grants_limit_per_page)
    
#     logger.info(f"\nFinished scraping process. {num_scraped_and_processed} grants processed and attempted to be stored/updated.")
#     logger.info("="*80 + "\n")


import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timezone
import re
import time
from typing import List, Dict, Optional, Any
import logging

from grants_db import insert_grant, update_grant, fetch_grant_by_link_hash
from utils import generate_link_hash, preprocess_text, nlp, extract_keywords_from_doc
from sdg_classifier import SDGClassifier
from logging_setup import setup_logger

logger = setup_logger(__name__)

sdg_classifier = SDGClassifier()

def _extract_details_from_deep_scrape(soup: BeautifulSoup) -> Dict[str, Any]:
    details: Dict[str, Any] = {
        "description_long": "",
        "application_deadline": None,
        "focus_areas": [],
        "target_beneficiaries": [],
        "geographic_eligibility": [],
        "min_budget": None,
        "max_budget": None,
        "keywords": [],
    }

    content_div = soup.select_one("div.entry-content[itemprop='text']")
    if content_div:
        for tag in content_div(["script", "style", "noscript", "iframe", "div[class*='code-block']"]):
            tag.decompose()
        details["description_long"] = content_div.get_text(separator=" ", strip=True)[:15000]

    deadline_tag = soup.find("strong", text=re.compile(r"Deadline:", re.IGNORECASE))
    if deadline_tag:
        deadline_text_raw = deadline_tag.next_sibling
        if deadline_text_raw and isinstance(deadline_text_raw, str):
            date_match = re.search(r'\b(\d{1,2}-\w{3}-\d{4})\b', deadline_text_raw, re.IGNORECASE)
            if not date_match:
                date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', deadline_text_raw)
            if not date_match:
                date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', deadline_text_raw, re.IGNORECASE)

            if date_match:
                try:
                    date_str = date_match.group(0)
                    if '-' in date_str and date_str.count('-') == 2:
                        details["application_deadline"] = datetime.strptime(date_str, '%d-%b-%Y').replace(tzinfo=timezone.utc)
                    elif '-' in date_str and date_str.count('-') == 1:
                         details["application_deadline"] = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    else:
                        details["application_deadline"] = datetime.strptime(date_str, '%B %d, %Y').replace(tzinfo=timezone.utc)
                except ValueError:
                    logger.warning(f"Could not parse deadline '{date_str}' from deep scrape.")
                    details["application_deadline"] = None

    if details["description_long"]:
        budgets = re.findall(r'£(\d{1,3}(?:,\d{3})*)|(?:\$|USD)\s*(\d{1,3}(?:,\d{3})*)', details["description_long"])
        extracted_budgets = []
        for currency_match in budgets:
            for amount_str in currency_match:
                if amount_str:
                    try:
                        extracted_budgets.append(int(amount_str.replace(',', '')))
                    except ValueError:
                        pass
        if extracted_budgets:
            details["min_budget"] = min(extracted_budgets)
            details["max_budget"] = max(extracted_budgets)

    sections_of_interest: Dict[str, List[str]] = {
        "focus_areas": [r"Focus Area(?:s)?", r"Thematic Area(?:s)?", r"Priorities"],
        "target_beneficiaries": [r"Target (?:Beneficiaries|Population|Groups)", r"Who Can Apply"],
        "geographic_eligibility": [r"Eligib(?:ility|le) Countr(?:y|ies)", r"Geographic Focus", r"Where to Apply"],
        "keywords": [r"Keywords", r"Tags"]
    }

    for field, patterns in sections_of_interest.items():
        for pattern in patterns:
            heading = soup.find(re.compile(r"h[3-5]", re.IGNORECASE), text=re.compile(pattern, re.IGNORECASE))
            if heading:
                current_element = heading.next_sibling
                section_text: List[str] = []
                while current_element and current_element.name not in ['h1', 'h2', 'h3', 'h4', 'h5', 'div', 'p', 'footer']:
                    if current_element.name in ['ul', 'ol']:
                        for li in current_element.find_all('li'):
                            item_text = li.get_text(separator=' ', strip=True)
                            if item_text:
                                section_text.append(item_text)
                    elif current_element.name == 'p':
                         paragraph_text = current_element.get_text(separator=' ', strip=True)
                         if paragraph_text:
                            section_text.append(paragraph_text)
                    current_element = current_element.next_sibling
                
                if section_text:
                    combined_section: str = " ".join(section_text)
                    if field in ["focus_areas", "target_beneficiaries", "geographic_eligibility", "keywords"]:
                        extracted_items: List[str] = [item.strip() for item in re.split(r'[,;•–-]', combined_section) if item.strip()]
                        extracted_items = [item for item in extracted_items if len(item) > 2 and "and" not in item.lower()]
                        details[field] = list(set(extracted_items))

                break

    if not details["keywords"] and nlp and details["description_long"]:
        doc = nlp(preprocess_text(details["description_long"]))
        details["keywords"] = list(extract_keywords_from_doc(doc))

    return details

def scrape_fundsforngos(num_pages: int = 3, grants_per_page_limit: Optional[int] = None) -> int:
    """
    Scrapes grants from fundsforngos.org, handling pagination and deep-scraping
    individual grant pages. Stores classified grants in the database.
    """
    base_category_url: str = "https://www2.fundsforngos.org/category/latest-funds-for-ngos/"
    headers: Dict[str, str] = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36)"}

    total_grants_processed: int = 0

    for page_num in range(1, num_pages + 1):
        listing_url: str = urljoin(base_category_url, f"page/{page_num}/")
        logger.info(f"Attempting to scrape listing page: {listing_url}")

        try:
            response = requests.get(listing_url, headers=headers, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            articles = soup.select("article.post")
            
            grants_on_page_count: int = 0
            for article in articles:
                if grants_per_page_limit is not None and grants_on_page_count >= grants_per_page_limit:
                    logger.info(f"Reached per-page limit ({grants_per_page_limit}) on page {page_num}.")
                    break

                title_tag = article.select_one("h2.entry-title a")
                description_short_tag = article.select_one("div.entry-content p")

                if title_tag and description_short_tag:
                    title: str = title_tag.get_text(strip=True)
                    link: str = title_tag['href']
                    link_hash: str = generate_link_hash(link)
                    description_short: str = description_short_tag.get_text(separator=" ", strip=True)

                    logger.info(f"Found grant on listing page: '{title}'")
                    
                    existing_grant: Optional[Dict] = fetch_grant_by_link_hash(link_hash)
                    if existing_grant and existing_grant.get("description_long"):
                        logger.info(f"Grant '{title}' already exists with full details. Skipping deep scrape and re-insertion.")
                        total_grants_processed += 1
                        grants_on_page_count += 1
                        continue

                    deep_scraped_details: Dict[str, Any] = {}
                    try:
                        deep_response = requests.get(link, headers=headers, timeout=30)
                        deep_response.raise_for_status()
                        deep_soup = BeautifulSoup(deep_response.text, "html.parser")
                        deep_scraped_details = _extract_details_from_deep_scrape(deep_soup)
                    except requests.exceptions.RequestException as e:
                        logger.error(f"HTTP/Network error deep scraping '{link}': {e}")
                        deep_scraped_details["description_long"] = description_short + " (Full description not available)"
                        deep_scraped_details["application_deadline"] = None
                    except Exception as e:
                        logger.error(f"General error deep scraping '{link}': {e}", exc_info=True)
                        deep_scraped_details["description_long"] = description_short + " (Full description not available)"
                        deep_scraped_details["application_deadline"] = None

                    final_grant_data: Dict = {
                        "link_hash": link_hash,
                        "link": link,
                        "title": title,
                        "description_short": description_short,
                        "description_long": deep_scraped_details.get("description_long", ""),
                        "application_deadline": deep_scraped_details.get("application_deadline"),
                        "focus_areas": deep_scraped_details.get("focus_areas", []),
                        "target_beneficiaries": deep_scraped_details.get("target_beneficiaries", []),
                        "geographic_eligibility": deep_scraped_details.get("geographic_eligibility", []),
                        "min_budget": deep_scraped_details.get("min_budget"),
                        "max_budget": deep_scraped_details.get("max_budget"),
                        "source": "FundsforNGOs",
                        "is_active": True
                    }

                    text_for_sdg_classification: str = f"{final_grant_data['title']} {final_grant_data['description_short']} {final_grant_data['description_long']}"
                    final_grant_data["sdg_tags"] = sdg_classifier.classify_text(text_for_sdg_classification)

                    if deep_scraped_details.get("keywords") and len(deep_scraped_details["keywords"]) > 0:
                        final_grant_data["keywords"] = deep_scraped_details["keywords"]
                    elif nlp and final_grant_data["description_long"]:
                        doc_for_keywords = nlp(preprocess_text(final_grant_data["description_long"]))
                        final_grant_data["keywords"] = list(extract_keywords_from_doc(doc_for_keywords))
                    else:
                        final_grant_data["keywords"] = list(set(re.findall(r'\b\w+\b', preprocess_text(final_grant_data["description_short"]))))

                    if not existing_grant:
                        if insert_grant(final_grant_data):
                            logger.info(f"Successfully inserted: '{title}' (SDGs: {', '.join(final_grant_data['sdg_tags'])})")
                            total_grants_processed += 1
                            grants_on_page_count += 1
                        else:
                            logger.error(f"Failed to insert: '{title}'")
                    else:
                        if not existing_grant.get("description_long") or (deep_scraped_details.get("description_long") and len(deep_scraped_details["description_long"]) > len(existing_grant.get("description_long", ""))):
                            logger.info(f"Updating existing grant: '{title}' with new details.")
                            if update_grant(final_grant_data):
                                logger.info(f"Successfully updated: '{title}'")
                            else:
                                logger.error(f"Failed to update: '{title}'")
                        else:
                            logger.info(f"Grant '{title}' already exists with sufficient detail. Skipping update.")
                        total_grants_processed += 1
                        grants_on_page_count += 1

                time.sleep(2)

            logger.info(f"Finished processing {grants_on_page_count} grants on page {page_num}.")
            time.sleep(5)

        except requests.exceptions.RequestException as e:
            logger.error(f"[Scraper HTTP/Network Error] Failed to scrape listing page {listing_url}: {e}")
        except Exception as e:
            logger.error(f"[Scraper General Error] An unexpected error occurred on listing page {listing_url}: {e}", exc_info=True)

    return total_grants_processed

if __name__ == "__main__":
    logger.info("\n" + "="*80)
    logger.info("Starting NGO Grant Scraper (FundsforNGOs.org) - Deep Scrape & Pagination")
    logger.info("This will fetch grants from multiple pages, classify SDGs, and store them in your DB.")
    logger.info("Existing grants with full details will be skipped.")
    logger.info("="*80 + "\n")
    
    num_pages_to_scrape: int = 3
    grants_limit_per_page: Optional[int] = None

    num_scraped_and_processed = scrape_fundsforngos(num_pages=num_pages_to_scrape, grants_per_page_limit=grants_limit_per_page)
    
    logger.info(f"\nFinished scraping process. {num_scraped_and_processed} grants processed and attempted to be stored/updated.")
    logger.info("="*80 + "\n")

