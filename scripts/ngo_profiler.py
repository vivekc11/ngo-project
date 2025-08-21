# search_service/ngo_profiler.py
"""
Primitive NGO profiler:
- Crawl just initial page and "about-like" internal anchors
- Extract clean text with trafilatura
- Build a single concatenated text and embed+persist to ngo_profiles
"""

import re
import requests
from urllib.parse import urlparse, urljoin
import trafilatura
from data_enrichment.embedder import Embedder
from grants_db import get_connection
from pgvector.psycopg2 import register_vector
from lxml import html

ABOUT_KEYWORDS = ["about", "mission", "what-we-do", "program", "projects", "who-we-are", "focus", "impact"]

def candidate_links_from_html(base_url, html_text):
    tree = html.fromstring(html_text)
    anchors = tree.xpath('//a[@href]')
    base_domain = urlparse(base_url).netloc
    found = set()
    for a in anchors:
        href = a.get('href')
        if not href:
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        if parsed.netloc != base_domain:
            continue
        if any(k in full.lower() for k in ABOUT_KEYWORDS) or (a.text and any(k in (a.text or "").lower() for k in ABOUT_KEYWORDS)):
            found.add(full)
    return list(found)

def fetch_text(url, timeout=20):
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent":"ngov1-bot/1.0"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[ngo_profiler] fetch error for {url}: {e}")
        return None

def extract_clean_text(html_content):
    if not html_content:
        return ""
    extracted = trafilatura.extract(html_content, include_comments=False, no_fallback=True)
    if not extracted:
        # fallback simple text extraction
        from lxml.html import fromstring
        try:
            tree = fromstring(html_content)
            return " ".join(tree.xpath('//text()'))
        except Exception:
            return ""
    return extracted

def profile_url_and_save(url: str, upsert: bool = True):
    """
    Crawl seed url and about-like links, build a profile, compute embedding, save to ngo_profiles.
    Returns dict: {url, summary, raw_text, embedding}
    """
    print(f"[ngo_profiler] Profiling {url}")
    seed_html = fetch_text(url)
    if not seed_html:
        raise RuntimeError("Could not fetch seed url")

    links = candidate_links_from_html(url, seed_html)
    pages = [seed_html]
    for l in links[:6]:  # limit to first 6 about pages
        h = fetch_text(l)
        if h:
            pages.append(h)

    texts = [extract_clean_text(p) for p in pages]
    combined = "\n\n".join(t for t in texts if t and len(t) > 100)

    # short summary for UI (we just take first 300 words for now)
    words = combined.split()
    summary = " ".join(words[:300])

    # embed
    embedder = Embedder()
    emb = embedder.embed(combined)

    # persist to ngo_profiles table
    conn = get_connection()
    register_vector(conn)
    cur = conn.cursor()
    # upsert by url
    cur.execute("""
        INSERT INTO ngo_profiles (url, summary, raw_text, embedding)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (url) DO UPDATE
          SET summary = EXCLUDED.summary,
              raw_text = EXCLUDED.raw_text,
              embedding = EXCLUDED.embedding,
              created_at = now()
        RETURNING id;
    """, (url, summary, combined, emb.tolist()))
    conn.commit()
    row_id = cur.fetchone()[0]
    cur.close()
    conn.close()

    print(f"[ngo_profiler] saved profile id={row_id} url={url}")
    return {"id": row_id, "url": url, "summary": summary, "raw_text": combined, "embedding": emb}

if __name__ == "__main__":
    # simple local test: python ngo_profiler.py https://example.org
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ngo_profiler.py <url>")
        sys.exit(1)
    profile_url_and_save(sys.argv[1])
