# # search_service/ngo_profiler.py
# from __future__ import annotations
# import re
# from typing import Dict, Optional
# import trafilatura
# import requests
# from bs4 import BeautifulSoup

# from data_enrichment.embedder import Embedder
# from data_enrichment.summarizer import Summarizer
# from grants_db import get_connection
# from pgvector.psycopg2 import register_vector
# from logging_setup import setup_logger

# logger = setup_logger("ngo_profiler")

# def _fetch_html(url: str) -> str:
#     # Let trafilatura download first (handles robots & retries decently)
#     downloaded = trafilatura.fetch_url(url, no_ssl=True, timeout=20)
#     if downloaded:
#         return downloaded
#     # Fallback
#     resp = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
#     resp.raise_for_status()
#     return resp.text

# def _clean_text_from_html(html: str) -> Dict[str, str]:
#     # Title
#     soup = BeautifulSoup(html, "lxml")
#     title = soup.title.get_text(strip=True) if soup.title else ""

#     # Main article text
#     extracted = trafilatura.extract(html, include_comments=False, no_fallback=True)
#     if not extracted:
#         # crude fallback
#         extracted = soup.get_text(" ", strip=True)
#     # Normalize whitespace
#     extracted = re.sub(r"\s+", " ", extracted).strip()
#     return {"title": title, "text": extracted}

# def profile_url(url: str, store: bool = True) -> Dict[str, Optional[str]]:
#     """
#     Build an NGO profile from a single URL:
#     - fetch + clean text
#     - create a dev-only summary (logged)
#     - embed (GPU if available via Embedder)
#     - optionally store minimal row in ngo_profiles
#     """
#     logger.info(f"[profile_url] fetching: {url}")
#     html = _fetch_html(url)
#     parts = _clean_text_from_html(html)
#     title = parts["title"]
#     text = parts["text"]

#     # Dev-only short summary -> log it (not returned to UI)
#     summarizer = Summarizer()
#     # Keep the summary ~50 words and avoid deadline/date noise
#     summary = summarizer.summarize(text, max_words=55, forbid_terms=["deadline", "closing date", "apply by"])
#     logger.info(f"[summary] {summary}")

#     # Embedding
#     embedder = Embedder()
#     # We embed title + text to capture title-only info
#     to_embed = f"{title}\n\n{text}".strip()
#     emb = embedder.embed_one(to_embed)  # 1024-d vector (list/np.array)

#     row_id = None
#     if store:
#         conn = get_connection()
#         register_vector(conn)
#         cur = conn.cursor()
#         cur.execute(
#             """
#             INSERT INTO ngo_profiles (url, title, description, summary, embedding)
#             VALUES (%s, %s, %s, %s, %s)
#             ON CONFLICT (url) DO UPDATE
#             SET title = EXCLUDED.title,
#                 description = EXCLUDED.description,
#                 summary = EXCLUDED.summary,
#                 embedding = EXCLUDED.embedding,
#                 updated_at = NOW()
#             RETURNING id;
#             """,
#             (url, title, text, summary, emb.tolist())
#         )
#         row_id = cur.fetchone()[0]
#         conn.commit()
#         cur.close()
#         conn.close()
#         logger.info(f"[profile_url] stored/updated ngo_profiles.id={row_id}")

#     return {
#         "id": row_id,
#         "url": url,
#         "title": title,
#         "text": text,
#         "summary_dev": summary,
#         "embedding": emb,
#     }

# search_service/ngo_profiler.py
import os
import re
import logging
from urllib.parse import urlparse

import requests
import trafilatura
from bs4 import BeautifulSoup

from grants_db import get_connection
from services.embeddings import get_embedder
from services.summarizer import get_summarizer

logger = logging.getLogger("ngo_profiler")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(os.path.join("logs", "ngo_profiler.log"), encoding="utf-8")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    fh.setFormatter(fmt); ch.setFormatter(fmt)
    logger.addHandler(fh); logger.addHandler(ch)

USER_AGENT = os.getenv("CRAWL_UA", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NGO-Profiler/1.0")

def _fetch_html(url: str) -> str:
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.error("[fetch_html] failed for %s: %s", url, e)
        return ""

def _clean_text(html: str) -> str:
    if not html:
        return ""
    # Try trafilatura first
    extracted = trafilatura.extract(html, include_comments=False, no_fallback=True)
    if extracted:
        return extracted.strip()

    # Fallback: strip with BeautifulSoup
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
            tag.decompose()
        text = soup.get_text(" ").strip()
        return re.sub(r"\s+", " ", text)
    except Exception:
        return ""

def _extract_title(html: str) -> str:
    try:
        soup = BeautifulSoup(html, "lxml")
        if soup.title and soup.title.string:
            return soup.title.string.strip()
    except Exception:
        pass
    return ""

def _domain_from_url(url: str) -> str:
    try:
        return urlparse(url).netloc
    except Exception:
        return url

def profile_url(url: str, store: bool = True):
    """
    Fetch -> clean -> summarize (for logs) -> embed.
    Returns dict on success, None on failure.
    """
    logger.info("[profile_url] start %s", url)
    html = _fetch_html(url)
    if not html:
        logger.error("[profile_url] no HTML for %s", url)
        return None

    title = _extract_title(html)
    text = _clean_text(html)
    if not text or len(text) < 200:
        logger.error("[profile_url] cleaned text too short for %s (len=%d)", url, len(text or ""))
        return None

    # Summarize for console/logs only (not UI)
    try:
        summarizer = get_summarizer()
        summary = summarizer.summarize(text)
        logger.info("[profile_url] summary (~50w): %s", summary)
    except Exception as e:
        logger.warning("[profile_url] summarizer failed: %s", e)
        summary = ""

    # Embed
    try:
        embedder = get_embedder()
        # We embed title + text so important signals in title aren’t lost
        embedding = embedder.embed_one(f"{title}\n\n{text}".strip())
    except Exception as e:
        logger.error("[profile_url] embedding failed: %s", e)
        return None

    if embedding is None:
        logger.error("[profile_url] got empty embedding for %s", url)
        return None

    prof = {
        "url": url,
        "title": title or _domain_from_url(url),
        "description": text,
        "summary": summary,
        "embedding": embedding,
    }

    if store:
        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO ngo_profiles (url, title, description, summary, embedding)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    summary = EXCLUDED.summary,
                    embedding = EXCLUDED.embedding,
                    updated_at = NOW();
                """,
                (prof["url"], prof["title"], prof["description"], prof["summary"], prof["embedding"].tolist()),
            )
            conn.commit()
            cur.close(); conn.close()
            logger.info("[profile_url] stored/updated %s", url)
        except Exception as e:
            logger.warning("[profile_url] DB upsert failed (continuing): %s", e)

    return prof
