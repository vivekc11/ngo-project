# scrapers/funds_scraper/pipelines.py
import sys
import os
from scrapy.exceptions import DropItem

# The path manipulation is necessary for local execution but is not required if the project is installed as a package.
# It ensures that sibling modules like `grants_raw_db` can be imported correctly.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from grants_raw_db import insert_raw_page, update_raw_grant_html
from scrapers.funds_scraper.items import ListPagesItem, GrantPagesItem
from logging_setup import SpiderLogger

class FundsScraperPipeline:
    def open_spider(self, spider):
        self.logger = spider.logger
        self.processed_count = 0

    def process_item(self, item, spider):
        if isinstance(item, ListPagesItem):
            if insert_raw_page(item['url'], item['html']):
                self.logger.info(f"✅ Stored raw list page: {item['url']}")
                return item
            else:
                self.logger.warning(f"⚠️ Page already exists in DB: {item['url']}")
                return item # Don't drop the item, allow the spider to continue
        elif isinstance(item, GrantPagesItem):
            if update_raw_grant_html(item['url'], item['html']):
                self.logger.info(f"✅ Updated raw grant page with HTML: {item['url']}")
                return item
            else:
                self.logger.warning(f"⚠️ Failed to update raw grant page: {item['url']}")
                raise DropItem(f"Update failed for item: {item['url']}")
        else:
            self.logger.warning(f"Unknown item type received: {type(item)}")
            return item