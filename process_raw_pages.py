# process_raw_pages.py

from scrapy.http import HtmlResponse
from grants_raw_db import get_all_raw_pages, insert_raw_grant
from logging_setup import SpiderLogger
from urllib.parse import urljoin
import re

def extract_grant_links_from_listing(html: str, base_url: str) -> list[str]:
    """
    Extracts grant links from a raw list page's HTML.
    This version is updated to target links within the 'more-link' class.
    """
    response = HtmlResponse(url=base_url, body=html, encoding='utf-8')
    links = response.css("a.more-link::attr(href)").getall()
    return [urljoin(base_url, link) for link in links if link]

def process_all_raw_pages():
    """
    Orchestrates the process of extracting links from raw pages and
    inserting them as placeholders in the raw grants database.
    """
    pages = get_all_raw_pages()
    logger = SpiderLogger("process_raw_pages", target_pages=len(pages))
    seen = set()
    total_inserted, total_skipped = 0, 0

    if not pages:
        logger.logger.warning("No raw pages found in the database. Please run Stage 1 first.")
        logger.log_final_summary()
        return

    for i, page in enumerate(pages, 1):
        base_url = page['url']
        html = page['html']
        
        # Extract links using the updated selector
        grant_links = extract_grant_links_from_listing(html, base_url)
        logger.log_page_progress(i, len(grant_links))

        for link in grant_links:
            if link in seen:
                total_skipped += 1
                continue
            seen.add(link)
            
            # Insert a placeholder for raw HTML to be fetched later by a spider
            inserted = insert_raw_grant(link, "")
            if inserted:
                logger.logger.info(f"✅ Inserted placeholder for grant link: {link}")
                total_inserted += 1
            else:
                logger.logger.warning(f"⚠️ Failed to insert placeholder or link already exists: {link}")
                total_skipped += 1

    logger.log_final_summary()
    logger.logger.info(f"Total links processed: {total_inserted + total_skipped}, Inserted: {total_inserted}, Skipped: {total_skipped}")

if __name__ == "__main__":
    process_all_raw_pages()