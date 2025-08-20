# # # process_grants.py
# # import sys
# # import os
# # import re
# # from typing import Dict, Any, List
# # from datetime import datetime, timezone
# # from lxml.html import fromstring
# # from parsel import Selector

# # # Set up the Python path to access project modules
# # project_root = os.path.abspath(os.path.dirname(__file__))
# # if project_root not in sys.path:
# #     sys.path.insert(0, project_root)

# # from grants_raw_db import get_all_raw_grants
# # from grants_db import insert_grant, update_grant, fetch_grant_by_link_hash
# # from sdg_classifier import SDGClassifier
# # from utils import generate_link_hash, preprocess_text, nlp, extract_keywords_from_doc
# # from logging_setup import setup_logger, SpiderLogger

# # # Define logger at the global scope so all functions can access it.
# # logger = setup_logger("grant_processor", "grant_processor.log")

# # def _extract_details_from_raw_html(html: str, url: str) -> Dict[str, Any]:
# #     """
# #     Extracts detailed information from a single grant's raw HTML using LXML and Parsel.
# #     """
# #     details: Dict[str, Any] = {
# #         "title": "N/A",
# #         "description_long": "",
# #         "application_deadline": None,
# #         "focus_areas": [],
# #         "target_beneficiaries": [],
# #         "geographic_eligibility": [],
# #         "min_budget": None,
# #         "max_budget": None,
# #         "keywords": [],
# #     }

# #     selector = Selector(text=html)
    
# #     # Extract title
# #     details["title"] = selector.css('h1.entry-title::text').get(default='').strip()

# #     # Extract long description
# #     content_container = selector.css('div.entry-content[itemprop="text"]')
# #     # Remove unwanted tags before extracting text
# #     content_container.css('script, style, noscript, iframe, div[class*="code-block"]').get()
    
# #     raw_description = ''.join(content_container.xpath('string()').getall()).strip()
# #     details["description_long"] = raw_description
    
# #     # Extract deadline
# #     deadline_text = selector.xpath('//strong[contains(text(), "Deadline:")]/following-sibling::text()').get(default='').strip()
# #     if deadline_text:
# #         try:
# #             date_match = re.search(r'\b(\d{1,2}-\w{3}-\d{4})\b', deadline_text, re.IGNORECASE)
# #             if not date_match:
# #                 date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', deadline_text)
# #             if not date_match:
# #                 date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', deadline_text, re.IGNORECASE)

# #             if date_match:
# #                 date_str = date_match.group(0)
# #                 if '-' in date_str and date_str.count('-') == 2:
# #                     details["application_deadline"] = datetime.strptime(date_str, '%d-%b-%Y').replace(tzinfo=timezone.utc)
# #                 elif '-' in date_str and date_str.count('-') == 1:
# #                     details["application_deadline"] = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
# #                 else:
# #                     details["application_deadline"] = datetime.strptime(date_str, '%B %d, %Y').replace(tzinfo=timezone.utc)
# #         except ValueError:
# #             logger.warning(f"Could not parse deadline '{deadline_text}' for URL: {url}.")

# #     # Extract budget from long description
# #     if details["description_long"]:
# #         budgets = re.findall(r'£(\d{1,3}(?:,\d{3})*)|(?:\$|USD)\s*(\d{1,3}(?:,\d{3})*)', details["description_long"])
# #         extracted_budgets = []
# #         for currency_match in budgets:
# #             for amount_str in currency_match:
# #                 if amount_str:
# #                     try:
# #                         extracted_budgets.append(int(amount_str.replace(',', '')))
# #                     except ValueError:
# #                         pass
# #         if extracted_budgets:
# #             details["min_budget"] = min(extracted_budgets)
# #             details["max_budget"] = max(extracted_budgets)

# #     # Extract metadata (focus areas, eligibility)
# #     focus_areas = selector.css('meta[property="article:section"]::attr(content)').get(default='')
# #     if focus_areas:
# #         details['focus_areas'] = [area.strip() for area in focus_areas.split(',') if area.strip()]

# #     tags = selector.css('meta[name="post_tags"]::attr(content)').get(default='')
# #     if tags:
# #         details['geographic_eligibility'] = [tag.strip() for tag in tags.split('|') if tag.strip()]
    
# #     # Generate keywords from description if they don't exist
# #     if not details["keywords"] and nlp and details["description_long"]:
# #         doc = nlp(preprocess_text(details["description_long"]))
# #         details["keywords"] = list(extract_keywords_from_doc(doc))
    
# #     return details

# # def process_raw_grants_to_final_db():
# #     processor_logger = SpiderLogger("grant_processor", target_pages='all')
# #     sdg_seeds_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sdg_seeds.yml')
# #     sdg_classifier = SDGClassifier(sdg_seeds_path=sdg_seeds_path)
    
# #     logger.info("Starting Stage 3: Processing raw grants into structured grants.")
    
# #     raw_grants = get_all_raw_grants()
# #     if not raw_grants:
# #         logger.info("No raw grants found to process. Please run Stage 2 first.")
# #         return

# #     for page in raw_grants:
# #         url = page.get('url')
# #         html = page.get('html')
        
# #         try:
# #             details = _extract_details_from_raw_html(html, url)
            
# #             title = details.get("title", "N/A")
# #             description_short = details.get("description_long", "")[:255]

# #             final_grant_data = {
# #                 "link_hash": generate_link_hash(url),
# #                 "link": url,
# #                 "title": title,
# #                 "description_short": description_short,
# #                 "description_long": details.get("description_long", ""),
# #                 "application_deadline": details.get("application_deadline"),
# #                 "focus_areas": details.get("focus_areas", []),
# #                 "target_beneficiaries": details.get("target_beneficiaries", []),
# #                 "geographic_eligibility": details.get("geographic_eligibility", []),
# #                 "min_budget": details.get("min_budget"),
# #                 "max_budget": details.get("max_budget"),
# #                 "keywords": details.get("keywords", []),
# #                 "source": "FundsforNGOs",
# #                 "sdg_tags": sdg_classifier.classify_text(f"{title} {description_short} {details.get('description_long', '')}"),
# #                 "is_active": True
# #             }

# #             existing_grant = fetch_grant_by_link_hash(final_grant_data["link_hash"])
            
# #             if not existing_grant:
# #                 if insert_grant(final_grant_data):
# #                     processor_logger.logger.info(f"✅ Successfully inserted new grant: {title}")
# #                     processor_logger.progress_tracker.track_successful_extraction()
# #             else:
# #                 if update_grant(final_grant_data):
# #                     processor_logger.logger.info(f"🔄 Successfully updated existing grant: {title}")
# #                 else:
# #                     processor_logger.logger.warning(f"⚠️ No update needed for grant: {title}")

# #         except Exception as e:
# #             processor_logger.logger.error(f"Error processing page {url}: {e}")
            
# #     processor_logger.log_final_summary()

# # if __name__ == "__main__":
# #     process_raw_grants_to_final_db()




# # process_grants.py
# import sys
# import os
# import re
# from typing import Dict, Any, List
# from datetime import datetime, timezone
# from parsel import Selector
# import spacy
# import trafilatura
# from lxml.html import fromstring

# # Set up the Python path to access project modules
# project_root = os.path.abspath(os.path.dirname(__file__))
# if project_root not in sys.path:
#     sys.path.insert(0, project_root)

# from grants_raw_db import get_all_raw_grants
# from grants_db import insert_grant, update_grant, fetch_grant_by_link_hash
# from sdg_classifier import SDGClassifier
# from utils import generate_link_hash, preprocess_text, nlp, extract_main_text_from_html
# from logging_setup import setup_logger, SpiderLogger

# # Define logger at the global scope so all functions can access it.
# logger = setup_logger("grant_processor", "grant_processor.log")

# # Load a spaCy model for NER.
# try:
#     nlp_ner = spacy.load("en_core_web_sm")
# except ImportError:
#     logger.warning("Warning: spaCy model 'en_core_web_sm' not found. Please install with 'python -m spacy download en_core_web_sm'.")
#     nlp_ner = None

# def _extract_details_from_raw_html(html: str, url: str) -> Dict[str, Any]:
#     """
#     Extracts detailed information from a single grant's raw HTML using a refined process.
#     """
#     details: Dict[str, Any] = {
#         "title": "N/A",
#         "description_short": "",
#         "description_long": "",
#         "application_deadline": None,
#         "focus_areas": [],
#         "target_beneficiaries": [],
#         "geographic_eligibility": [],
#         "min_budget": None,
#         "max_budget": None,
#         "currency": None,
#         "keywords": [],
#     }

#     selector = Selector(text=html)
    
#     # Use a robust extractor for the main text content
#     main_content = extract_main_text_from_html(html)
#     details["description_long"] = main_content
#     details["title"] = selector.css('h1.entry-title::text').get(default='').strip()
#     details["description_short"] = main_content[:255]
    
#     # Extract deadline
#     deadline_text = selector.xpath('//strong[contains(text(), "Deadline:")]/following-sibling::text()').get(default='').strip()
#     if deadline_text:
#         try:
#             date_match = re.search(r'\b(\d{1,2}-\w{3}-\d{4})\b', deadline_text, re.IGNORECASE)
#             if not date_match:
#                 date_match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', deadline_text)
#             if not date_match:
#                 date_match = re.search(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b', deadline_text, re.IGNORECASE)

#             if date_match:
#                 date_str = date_match.group(0)
#                 if '-' in date_str and date_str.count('-') == 2:
#                     details["application_deadline"] = datetime.strptime(date_str, '%d-%b-%Y').replace(tzinfo=timezone.utc)
#                 elif '-' in date_str and date_str.count('-') == 1:
#                     details["application_deadline"] = datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
#                 else:
#                     details["application_deadline"] = datetime.strptime(date_str, '%B %d, %Y').replace(tzinfo=timezone.utc)
#         except ValueError:
#             logger.warning(f"Could not parse deadline '{deadline_text}' for URL: {url}.")

#     # Use NER for location extraction
#     if nlp_ner and main_content:
#         doc = nlp_ner(main_content)
#         locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
#         details['geographic_eligibility'] = list(set(locations))
        
#     # Extract budget from long description
#     if main_content:
#         budgets = re.findall(r'(?:£|€|\$|USD|INR|CAD|AUD)\s*([\d,.]+)(?:\s*(k|m|million|lakh|crore)?)?', main_content, re.IGNORECASE)
#         extracted_budgets = []
#         for match in budgets:
#             currency, amount_str, multiplier = match
#             try:
#                 amount = float(amount_str.replace(',', ''))
#                 if multiplier:
#                     if multiplier.lower() in ['k']: amount *= 1_000
#                     if multiplier.lower() in ['m', 'million']: amount *= 1_000_000
#                     if multiplier.lower() in ['lakh']: amount *= 100_000
#                     if multiplier.lower() in ['crore']: amount *= 10_000_000
#                 extracted_budgets.append(amount)
#                 if not details["currency"]:
#                     details["currency"] = currency
#             except (ValueError, IndexError):
#                 pass
        
#         if extracted_budgets:
#             details["min_budget"] = min(extracted_budgets)
#             details["max_budget"] = max(extracted_budgets)

#     # Use original keyword extraction for other fields
#     focus_areas = selector.css('meta[property="article:section"]::attr(content)').get(default='')
#     if focus_areas:
#         details['focus_areas'] = [area.strip() for area in focus_areas.split(',') if area.strip()]

#     return details


# def process_raw_grants_to_final_db():
#     processor_logger = SpiderLogger("grant_processor", target_pages='all')
#     sdg_seeds_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sdg_seeds.yml')
#     sdg_classifier = SDGClassifier(sdg_seeds_path=sdg_seeds_path)
    
#     logger.info("Starting Stage 3: Processing raw grants into structured grants.")
    
#     raw_grants = get_all_raw_grants()
#     if not raw_grants:
#         logger.info("No raw grants found to process. Please run Stage 2 first.")
#         return

#     for page in raw_grants:
#         url = page.get('url')
#         html = page.get('html')
        
#         if not html:
#             logger.warning(f"Skipping processing for {url} as HTML content is empty.")
#             continue
            
#         try:
#             details = _extract_details_from_raw_html(html, url)
            
#             title = details.get("title", "N/A")
#             description_short = details.get("description_long", "")[:255]

#             final_grant_data = {
#                 "link_hash": generate_link_hash(url),
#                 "link": url,
#                 "title": title,
#                 "description_short": description_short,
#                 "description_long": details.get("description_long", ""),
#                 "application_deadline": details.get("application_deadline"),
#                 "focus_areas": details.get("focus_areas", []),
#                 "target_beneficiaries": details.get("target_beneficiaries", []),
#                 "geographic_eligibility": details.get("geographic_eligibility", []),
#                 "min_budget": details.get("min_budget"),
#                 "max_budget": details.get("max_budget"),
#                 "currency": details.get("currency"),
#                 "keywords": details.get("keywords", []),
#                 "source": "FundsforNGOs",
#                 "sdg_tags": sdg_classifier.classify_text(f"{title} {description_short} {details.get('description_long', '')}"),
#                 "is_active": True
#             }

#             existing_grant = fetch_grant_by_link_hash(final_grant_data["link_hash"])
            
#             if not existing_grant:
#                 if insert_grant(final_grant_data):
#                     processor_logger.log_processing_success(f"Inserted new grant: {title}", url)
#             else:
#                 if update_grant(final_grant_data):
#                     processor_logger.log_processing_success(f"Updated existing grant: {title}", url)
#                 else:
#                     processor_logger.logger.warning(f"⚠️ No update needed for grant: {title}")

#         except Exception as e:
#             processor_logger.logger.error(f"Error processing page {url}: {e}")
            
#     processor_logger.log_final_summary()

# if __name__ == "__main__":
#     process_raw_grants_to_final_db()

# process_grants.py
import sys
import os
import re
from typing import Dict, Any, List
from datetime import datetime, timezone
from parsel import Selector
import spacy
import trafilatura
from lxml.html import fromstring
import dateparser

# Set up the Python path to access project modules
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from grants_raw_db import get_all_raw_grants
from grants_db import insert_grant, update_grant, fetch_grant_by_link_hash
from sdg_classifier import SDGClassifier
from utils import generate_link_hash, preprocess_text, nlp, extract_main_text_from_html
from logging_setup import setup_logger, SpiderLogger

# Define logger at the global scope so all functions can access it.
logger = setup_logger("grant_processor", "grant_processor.log")

# Load a spaCy model for NER.
try:
    nlp_ner = spacy.load("en_core_web_sm")
except ImportError:
    logger.warning("Warning: spaCy model 'en_core_web_sm' not found. Please install with 'python -m spacy download en_core_web_sm'.")
    nlp_ner = None

def _extract_details_from_raw_html(html: str, url: str) -> Dict[str, Any]:
    """
    Extracts detailed information from a single grant's raw HTML using a refined process.
    """
    details: Dict[str, Any] = {
        "title": "N/A",
        "description_short": "",
        "description_long": "",
        "application_deadline": None,
        "focus_areas": [],
        "target_beneficiaries": [],
        "geographic_eligibility": [],
        "min_budget": None,
        "max_budget": None,
        "currency": None,
        "keywords": [],
    }

    selector = Selector(text=html)
    
    # Use a robust extractor for the main text content
    main_content = extract_main_text_from_html(html)
    details["description_long"] = main_content
    details["title"] = selector.css('h1.entry-title::text').get(default='').strip()
    details["description_short"] = main_content[:255]
    
    # Extract deadline
    deadline_text = selector.xpath('//strong[contains(text(), "Deadline:")]/following-sibling::text()').get(default='').strip()
    if deadline_text:
        parsed_date = dateparser.parse(deadline_text, settings={'TIMEZONE': 'UTC', 'RETURN_AS_TIMEZONE_AWARE': True})
        if parsed_date:
            details["application_deadline"] = parsed_date
        else:
            logger.warning(f"⚠️ Could not parse deadline '{deadline_text}' for URL: {url}.")

    # Use NER for location extraction
    if nlp_ner and main_content:
        doc = nlp_ner(main_content)
        locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
        details['geographic_eligibility'] = list(set(locations))
        
    # Extract budget from long description
    if main_content:
        budgets = re.findall(r'(?:(£|€|\$|USD|INR|CAD|AUD)\s*|)([\d,.]+)(?:\s*(k|m|million|lakh|crore)?)?', main_content, re.IGNORECASE)
        extracted_budgets = []
        details["currency"] = None  # Explicitly set to None
        for match in budgets:
            currency, amount_str, multiplier = match
            try:
                amount = float(amount_str.replace(',', ''))
                if multiplier:
                    if multiplier.lower() in ['k']: amount *= 1_000
                    if multiplier.lower() in ['m', 'million']: amount *= 1_000_000
                    if multiplier.lower() in ['lakh']: amount *= 100_000
                    if multiplier.lower() in ['crore']: amount *= 10_000_000
                extracted_budgets.append(amount)
                if not details["currency"] and currency:
                    details["currency"] = currency
            except (ValueError, IndexError):
                pass
        
        if extracted_budgets:
            details["min_budget"] = min(extracted_budgets)
            details["max_budget"] = max(extracted_budgets)

    # Use original keyword extraction for other fields
    focus_areas = selector.css('meta[property="article:section"]::attr(content)').get(default='')
    if focus_areas:
        details['focus_areas'] = [area.strip() for area in focus_areas.split(',') if area.strip()]

    return details


def process_raw_grants_to_final_db():
    processor_logger = SpiderLogger("grant_processor", target_pages='all')
    sdg_seeds_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'sdg_seeds.yml')
    sdg_classifier = SDGClassifier(sdg_seeds_path=sdg_seeds_path)
    
    logger.info("Starting Stage 3: Processing raw grants into structured grants.")
    
    raw_grants = get_all_raw_grants()
    if not raw_grants:
        logger.info("No raw grants found to process. Please run Stage 2 first.")
        return

    for page in raw_grants:
        url = page.get('url')
        html = page.get('html')
        
        if not html:
            logger.warning(f"Skipping processing for {url} as HTML content is empty.")
            continue
            
        try:
            details = _extract_details_from_raw_html(html, url)
            
            title = details.get("title", "N/A")
            description_short = details.get("description_long", "")[:255]

            final_grant_data = {
                "link_hash": generate_link_hash(url),
                "link": url,
                "title": title,
                "description_short": description_short,
                "description_long": details.get("description_long", ""),
                "application_deadline": details.get("application_deadline"),
                "focus_areas": details.get("focus_areas", []),
                "target_beneficiaries": details.get("target_beneficiaries", []),
                "geographic_eligibility": details.get("geographic_eligibility", []),
                "min_budget": details.get("min_budget"),
                "max_budget": details.get("max_budget"),
                "currency": None,  # Ignore currency for now
                "keywords": details.get("keywords", []),
                "source": "FundsforNGOs",
                "sdg_tags": sdg_classifier.classify_text(f"{title} {description_short} {details.get('description_long', '')}"),
                "is_active": True
            }

            existing_grant = fetch_grant_by_link_hash(final_grant_data["link_hash"])
            
            if not existing_grant:
                if insert_grant(final_grant_data):
                    processor_logger.log_processing_success(f"Inserted new grant: {title}", url)
            else:
                if update_grant(final_grant_data):
                    processor_logger.log_processing_success(f"Updated existing grant: {title}", url)
                else:
                    processor_logger.logger.warning(f"⚠️ No update needed for grant: {title}")

        except Exception as e:
            processor_logger.logger.error(f"Error processing page {url}: {e}")
            
    processor_logger.log_final_summary()

if __name__ == "__main__":
    process_raw_grants_to_final_db()