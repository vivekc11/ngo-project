# scrape_grants.py

import subprocess
import sys


def run_spider(spider_name: str):
    try:
        subprocess.run(["scrapy", "crawl", spider_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run {spider_name}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scrape_grants.py [list|detail|all]")
        return

    command = sys.argv[1].lower()

    if command == "list":
        run_spider("list_pages_spider")
    elif command == "detail":
        run_spider("grant_pages_spider")
    elif command == "all":
        run_spider("list_pages_spider")
        run_spider("grant_pages_spider")
    else:
        print("Invalid command. Use: list, detail, or all")


if __name__ == "__main__":
    main()
