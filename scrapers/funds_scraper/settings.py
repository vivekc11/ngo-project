# scrapers/funds_scraper/settings.py
import os
import sys

# Add project root to sys.path for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

BOT_NAME = "funds_scraper"
SPIDER_MODULES = ["funds_scraper.spiders"]
NEWSPIDER_MODULE = "funds_scraper.spiders"
ROBOTSTXT_OBEY = True
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
DOWNLOAD_DELAY = 1
CONCURRENT_REQUESTS_PER_DOMAIN = 1
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]
DOWNLOAD_TIMEOUT = 30
LOG_LEVEL = 'INFO'

# Remove the pipelines setting as they are no longer used
# ITEM_PIPELINES = {
#    "scrapers.funds_scraper.pipelines.FundsScraperPipeline": 300,
# }