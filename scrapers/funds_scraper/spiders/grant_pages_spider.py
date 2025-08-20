# scrapers/funds_scraper/spiders/grant_pages_spider.py
import scrapy
from grants_raw_db import update_raw_grant_html
from logging_setup import SpiderLogger
from psycopg2.extras import RealDictCursor
from grants_raw_db import get_connection

# --- USER CONFIGURATION ---
BATCH_SIZE = 2000 # Number of links to scrape in one batch, 'None' means all links
# -------------------------

class GrantPagesSpider(scrapy.Spider):
    name = "grant_pages_spider"
    allowed_domains = ["fundsforngos.org", "www2.fundsforngos.org"]
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'AUTOTHROTTLE_ENABLED': True
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.links_to_scrape = self._get_links_without_html()
        self.total_pages = len(self.links_to_scrape)
        self.logger_system = SpiderLogger(self.name, self.total_pages)
        self.custom_logger = self.logger_system.logger

    def _get_links_without_html(self):
        """Fetches a limited number of links from the database that don't have HTML content."""
        query = f"""
            SELECT url
            FROM raw_grants
            WHERE html IS NULL OR html = ''
            LIMIT {BATCH_SIZE};
        """
        conn = None
        try:
            conn = get_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(query)
                return [row['url'] for row in cur.fetchall()]
        except Exception as e:
            self.custom_logger.error(f"Error fetching links from DB: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def start_requests(self):
        self.custom_logger.info(self.logger_system.console.header_message(f"Starting {self.name}"))
        self.custom_logger.info(f"Found {self.total_pages} grant links to scrape in this batch. Starting requests...")
        
        for link in self.links_to_scrape:
            yield scrapy.Request(link, self.parse)

    def parse(self, response):
        update_raw_grant_html(response.url, response.text)
        self.logger_system.progress_tracker.track_successful_extraction()
        self.custom_logger.info(f"✅ Scraped and updated HTML for: {response.url}")

    def closed(self, reason):
        self.custom_logger.info(f"Spider 'grant_pages_spider' closed: {reason}")
        self.logger_system.log_final_summary()