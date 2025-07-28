import scrapy
import logging

class GrantDetailSpider(scrapy.Spider):
    name = "grant_detail_spider"

    custom_settings = {
        "DEFAULT_REQUEST_HEADERS": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
            "Referer": "https://www.google.com/",
        },
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "ROBOTSTXT_OBEY": True,
    }

    def start_requests(self):
        yield scrapy.Request(
            url="https://www2.fundsforngos.org/latest-funds-for-ngos/cfas-community-economic-development-grant-program-in-australia/",
            callback=self.parse,
        )

    def parse(self, response):
        logging.info(f"Scraping URL: {response.url}")

        # Extract cleaned text content inside the article body
        text_parts = response.xpath('//div[contains(@class, "td-post-content")]//p//text()').getall()

        cleaned_text = "\n".join(t.strip() for t in text_parts if t.strip())

        yield {
            "url": response.url,
            "title": response.xpath("//title/text()").get(),
            "content": cleaned_text,
        }
