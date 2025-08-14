import requests
from bs4 import BeautifulSoup

def fetch_latest_grants(limit=5):
    url = "https://www2.fundsforngos.org/category/latest-funds-for-ngos/"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        articles = soup.select("article")[:limit]
        grants = []

        for article in articles:
            title_tag = article.select_one("h2 a")
            desc_tag = article.select_one("div.entry-summary")

            if title_tag and desc_tag:
                grants.append({
                    "title": title_tag.get_text(strip=True),
                    "description": desc_tag.get_text(strip=True)
                })

        return grants

    except Exception as e:
        print(f"[Scraper Error]: {e}")
        return []
