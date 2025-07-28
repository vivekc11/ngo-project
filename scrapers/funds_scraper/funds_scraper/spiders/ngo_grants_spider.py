import scrapy
from sentence_transformers import SentenceTransformer, util
from funds_scraper.items import GrantItem
import logging

model = SentenceTransformer("all-MiniLM-L6-v2")

class NgoGrantsSpider(scrapy.Spider):
    name = "ngo_grants_spider"
    allowed_domains = ["example.com"]  # replace with actual domain
    start_urls = ["https://example.com/grants"]  # replace with actual grant listing URL

    def parse(self, response):
        # Select links to individual grant detail pages
        links = response.css("a.grant-link::attr(href)").getall()
        for link in links:
            yield response.follow(link, callback=self.parse_grant)

    def parse_grant(self, response):
        item = GrantItem()

        # Basic title extraction
        item["title"] = response.css("h1::text").get(default="").strip()
        
        # Extract raw text for embedding
        full_text = " ".join(response.css("div.grant-content *::text").getall())

        # Embed and extract semantically relevant info
        extracted_data = self.extract_semantic_fields(full_text)
        item.update(extracted_data)

        yield item

    def extract_semantic_fields(self, text):
        fields = {
            "deadline": ["deadline", "apply by", "last date", "closing date"],
            "eligibility": ["eligibility", "who can apply"],
            "summary": ["summary", "overview", "description"],
        }

        text_lines = text.split("\n")
        results = {}

        for key, phrases in fields.items():
            max_score = 0
            best_line = ""
            for line in text_lines:
                line = line.strip()
                if not line:
                    continue
                for phrase in phrases:
                    sim = util.cos_sim(model.encode(phrase, convert_to_tensor=True),
                                       model.encode(line, convert_to_tensor=True)).item()
                    if sim > max_score:
                        max_score = sim
                        best_line = line
            results[key] = best_line

        return results
