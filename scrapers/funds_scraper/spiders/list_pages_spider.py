# scrapers/funds_scraper/spiders/list_pages_spider.py
import scrapy
from logging_setup import SpiderLogger
from urllib.parse import urljoin
from scrapy.exceptions import CloseSpider
from grants_raw_db import insert_raw_grant
import re

# --- USER CONFIGURATION ---
BASE_URL = "https://www2.fundsforngos.org/category/latest-funds-for-ngos/"
PAGES_TO_SCRAPE = None
OUTPUT_FILE = "scraped_grant_links.txt"
# -------------------------

class ListPagesSpider(scrapy.Spider):
    name = "list_pages_spider"
    allowed_domains = ["fundsforngos.org", "www2.fundsforngos.org"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'AUTOTHROTTLE_ENABLED': True,
        'ITEM_PIPELINES': {} # Disable pipelines for this spider
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_count = 0
        self.logger_system = SpiderLogger(self.name, PAGES_TO_SCRAPE or "all")
        self.custom_logger = self.logger_system.logger
        self.all_grant_links = set()

    def start_requests(self):
        self.custom_logger.info(self.logger_system.console.header_message(f"Starting {self.name} - configured to scrape {PAGES_TO_SCRAPE or 'all'} pages."))
        yield scrapy.Request(BASE_URL, callback=self.parse)

    def parse(self, response):
        self.page_count += 1
        self.custom_logger.info(f"Scraping list page {self.page_count}: {response.url}")

        # Extract all grant links from the current page
        links = response.css("a.more-link::attr(href)").getall()
        for link in links:
            full_url = urljoin(response.url, link)
            self.all_grant_links.add(full_url)
            # Insert the link directly into the raw_grants table as a placeholder
            insert_raw_grant(full_url, html="")

        self.logger_system.progress_tracker.track_page_completed()

        if PAGES_TO_SCRAPE is not None and self.page_count >= PAGES_TO_SCRAPE:
            self.custom_logger.info(f"Scraped {self.page_count} pages, stopping due to limit.")
            raise CloseSpider('page_limit_reached')

        next_page_link = response.css("li.pagination-next a::attr(href)").get()
        if next_page_link:
            full_url = urljoin(response.url, next_page_link)
            yield scrapy.Request(full_url, callback=self.parse)
        else:
            self.custom_logger.info("No more pages to crawl.")
    
    def closed(self, reason):
        self.custom_logger.info(f"Spider 'list_pages_spider' closed: {reason}")
        self.logger_system.log_final_summary()
        self._write_links_to_file()

    def _write_links_to_file(self):
        """Writes all collected links to a text file."""
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            for link in sorted(list(self.all_grant_links)):
                f.write(link + '\n')
        self.custom_logger.info(f"✅ All {len(self.all_grant_links)} unique grant links saved to {OUTPUT_FILE}")