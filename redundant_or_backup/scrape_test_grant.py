# scrape_test_grant.py
import os
import requests

def save_grant_html(url: str, output_folder: str = "txtoutput") -> None:
    print(f"[Scraping HTML] {url}")

    # 1. Get the HTML response
    response = requests.get(url, timeout=15)
    if response.status_code != 200:
        print(f"[Error] Status code {response.status_code}")
        return

    # 2. Create output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # 3. Create filename based on slug in URL
    slug = url.rstrip("/").split("/")[-1]
    output_path = os.path.join(output_folder, f"{slug}.txt")

    # 4. Save full HTML to .txt file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(response.text)

    print(f"[✓] HTML saved to {output_path}")

if __name__ == "__main__":
    url = "https://www.fundsforngos.org/latest-funds-for-ngos/eu-eritrea-strengthening-the-capacities-of-civil-society-organisations-local-authorities/"
    save_grant_html(url)