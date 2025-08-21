# # scripts/run_ngo_profile_and_search.py
# import sys
# import logging
# from search_service.ngo_profiler import profile_url
# from search_service.vector_search import search_from_profile

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# def main():
#     if len(sys.argv) < 2:
#         print('Usage: python -m scripts.run_ngo_profile_and_search "<ngo_url>" [top_k]')
#         sys.exit(1)

#     url = sys.argv[1]
#     top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 10

#     profile = profile_url(url, store=True)
#     if not profile:
#         print(f"\n❌ Could not profile URL: {url}. Check logs/ngo_profiler.log for details.")
#         sys.exit(2)

#     results = search_from_profile(profile, top_k=top_k)
#     if not results:
#         print("\nNo results (empty profile embedding or no candidates).")
#         sys.exit(0)

#     print(f"\nTop {top_k} results for: {url}\n")
#     for i, r in enumerate(results[:top_k], 1):
#         score = f"{r.get('score', 0.0):.3f}"
#         title = (r.get("title") or "").strip() or "(no title)"
#         link = r.get("url") or "(no link)"
#         summary = (r.get("summary") or "").strip()
#         if len(summary) > 140:
#             summary = summary[:137] + "…"
#         print(f"{i:02d}. [{score}] {title}\n    {link}\n    {summary}\n")

# if __name__ == "__main__":
#     main()

# scripts/run_ngo_profile_and_search.py
# Run with:
#   python -m scripts.run_ngo_profile_and_search "https://www.unicef.org/what-we-do" 10 --store
#
# What it does (brief):
# - Fetches a real NGO About/Mission page, cleans text, embeds it (GPU if available, fallback CPU)
# - (Optional) stores a compact profile row
# - Runs ANN search in PostgreSQL (pgvector) if a DB connection is available
# - Prints top-K matches with scores
#
# Robustness:
# - Clear ❌ messages on fetch/HTML/content-type failures (no crashes)
# - Graceful fallbacks if project-local helpers are missing (utils, logging_setup, services.*)
# - Safe guards for None/empty text and embedding

import argparse
import logging
import os
import sys
import time
from typing import Optional, Tuple, List

# -----------------------------
# Logging setup
# -----------------------------
LOGGER_NAME = "ngo_profiler"
LOG_PATH = os.path.join("logs", "ngo_profiler.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger: logging.Logger

try:
    # Prefer the project's logging setup if present
    from logging_setup import setup_logger  # type: ignore
    logger = setup_logger(LOGGER_NAME, LOG_PATH)
except Exception:
    # Fallback basic logger
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    ch = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)

# -----------------------------
# Fetching (requests) with guards
# -----------------------------
from urllib.parse import urlparse

try:
    import requests
except Exception as e:
    logger.error("`requests` is required. Please install it: pip install requests")
    raise

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/115.0 Safari/537.36"
}

def valid_http_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False

def fetch_html(url: str, timeout: int = 20) -> Tuple[Optional[str], Optional[str]]:
    """Returns (html_text, content_type) or (None, None) on failure."""
    if not valid_http_url(url):
        logger.error(f"Invalid URL format: {url}")
        return None, None
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
        if resp.status_code >= 400:
            logger.error(f"HTTP {resp.status_code} fetching {url}")
            return None, None
        ctype = resp.headers.get("Content-Type", "")
        if "text/html" not in ctype.lower():
            logger.error(f"Unsupported content-type for URL: {ctype}")
            return None, None
        return resp.text, ctype
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching URL: {e}")
        return None, None

# -----------------------------
# HTML -> clean text
# -----------------------------
def extract_clean_text(html: str) -> str:
    # Prefer project utils.preprocess_text (keeps consistency)
    try:
        from utils import preprocess_text  # type: ignore
        txt = preprocess_text(html)
        if isinstance(txt, str):
            return txt.strip()
    except Exception:
        pass

    # Fallback: BeautifulSoup text extraction + simple cleanup
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        logger.error("BeautifulSoup not available. Install with: pip install beautifulsoup4")
        return ""

    soup = BeautifulSoup(html, "html.parser")
    # Remove script/style
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()
    text = soup.get_text(separator=" ")
    # Normalize whitespace
    text = " ".join(text.split())
    return text.strip()

# -----------------------------
# Embedding service (GPU→CPU)
# -----------------------------
import numpy as np

def get_embedder():
    """
    Returns a callable: embed_fn(text:str)->np.ndarray
    Tries project service first; falls back to sentence-transformers.
    """
    # 1) Project service (preferred)
    try:
        # Expected to be a small factory the user already has
        # e.g., services/embeddings.py exposing get_embedder()
        from services.embeddings import get_embedder as project_get_embedder  # type: ignore
        embedder = project_get_embedder()
        # Sanity test
        v = embedder("test")
        if isinstance(v, (list, np.ndarray)):
            return lambda s: np.asarray(embedder(s), dtype=np.float32)
    except Exception as e:
        logger.info(f"Project embedder not available, falling back. Details: {e}")

    # 2) sentence-transformers fallback (MiniLM/BGE)
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        # Prefer BGE large if present, else MiniLM
        model_name = os.environ.get("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        model = SentenceTransformer(model_name, device="cuda" if _has_cuda() else "cpu")
        def _embed(text: str) -> np.ndarray:
            if not text:
                return np.zeros((384,), dtype=np.float32)  # safe default dim for MiniLM
            vec = model.encode([text], normalize_embeddings=True)[0]
            return np.asarray(vec, dtype=np.float32)
        return _embed
    except Exception as e:
        logger.error(
            "No embedding backend available. "
            "Install sentence-transformers or ensure services.embeddings.get_embedder() exists."
        )
        raise

def _has_cuda() -> bool:
    try:
        import torch  # type: ignore
        return bool(torch.cuda.is_available())
    except Exception:
        return False

# -----------------------------
# Optional: store profile row
# -----------------------------
def maybe_store_profile(url: str, text: str, embedding: np.ndarray) -> None:
    """
    Stores a compact profile row if project DB helpers are present.
    Fails silently (with logs) if storage is not configured.
    """
    try:
        from grants_db import insert_ngo_profile  # type: ignore
        # Trim text to a reasonable size for a "short description"
        short_desc = text[:1500]
        insert_ngo_profile(source_url=url, description=short_desc, embedding=embedding.tolist())
        logger.info("Stored NGO profile via grants_db.insert_ngo_profile")
        return
    except Exception as e:
        logger.info(f"Skipping DB store (no insert_ngo_profile?): {e}")

# -----------------------------
# ANN search via pgvector (if available)
# -----------------------------
def get_db_connection():
    """
    Returns a psycopg2 connection if DATABASE_URL is set, otherwise tries project helper.
    """
    # Try project helper first (so it reuses user's pooling/config)
    try:
        from grants_db import get_db_connection as project_conn  # type: ignore
        return project_conn()
    except Exception:
        pass

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        return None
    try:
        import psycopg2  # type: ignore
        return psycopg2.connect(dsn)
    except Exception as e:
        logger.info(f"Could not connect via DATABASE_URL: {e}")
        return None

def ann_search_pgvector(embedding: np.ndarray, top_k: int = 10) -> List[Tuple[float, dict]]:
    """
    Returns list of (score, row) sorted by best match.
    Assumes a table `grants` with pgvector column named `embedding`.
    Distance: cosine (use <#> with normalized vectors).
    """
    conn = get_db_connection()
    if conn is None:
        logger.info("No DB connection; skipping ANN search.")
        return []

    # Ensure embedding is a Python list of floats
    vec = embedding.astype(float).tolist()

    # NOTE: Adjust table/columns to your schema if different.
    sql = """
    SELECT
        id,
        title,
        link,
        summary,
        1 - (embedding <#> %s::vector) AS score
    FROM grants
    ORDER BY embedding <#> %s::vector
    LIMIT %s;
    """

    try:
        with conn.cursor() as cur:
            cur.execute(sql, (vec, vec, top_k))
            rows = cur.fetchall()
        conn.close()
    except Exception as e:
        logger.error(f"ANN query failed: {e}")
        return []

    results: List[Tuple[float, dict]] = []
    for r in rows:
        _id, title, link, summary, score = r
        results.append((float(score), {
            "id": _id,
            "title": title,
            "link": link,
            "summary": summary
        }))
    return results

# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser(description="Profile an NGO page and search similar grants.")
    parser.add_argument("url", type=str, help="NGO About/Mission page URL")
    parser.add_argument("top_k", type=int, nargs="?", default=10, help="Number of ANN results to show")
    parser.add_argument("--store", action="store_true", help="Store the NGO short profile in DB (if available)")
    args = parser.parse_args()

    start_ts = time.time()
    url = args.url.strip()

    logger.info(f"Starting NGO profiling for URL: {url}")

    # Fetch
    html, ctype = fetch_html(url)
    if not html:
        print(f"❌ Could not profile URL: {url} (fetch failed or not text/html). See {LOG_PATH}")
        return

    # Clean → text
    text = extract_clean_text(html)
    if not text or len(text) < 50:
        logger.error("Extracted text is empty or too short to embed.")
        print(f"❌ Could not profile URL: {url} (no usable text). See {LOG_PATH}")
        return

    # Embed
    try:
        embed_fn = get_embedder()
        vec = embed_fn(text)
        if vec is None or (isinstance(vec, np.ndarray) and vec.size == 0):
            raise ValueError("Empty embedding")
        # normalize (safety for cosine)
        norm = np.linalg.norm(vec)
        if norm == 0:
            raise ValueError("Zero-norm embedding")
        vec = (vec / norm).astype(np.float32)
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        print(f"❌ Could not compute embedding. See {LOG_PATH}")
        return

    # Optional store
    if args.store:
        try:
            maybe_store_profile(url, text, vec)
        except Exception as e:
            logger.info(f"Skipped storing profile: {e}")

    # ANN search (pgvector) if DB available
    results = ann_search_pgvector(vec, top_k=args.top_k)

    elapsed = time.time() - start_ts
    logger.info(f"Completed profiling + search in {elapsed:.2f}s")

    # Print results (CLI)
    if not results:
        print("No ANN results shown (DB not configured or query failed).")
        print(f"✔ Text length: {len(text)} | Embedding dim: {len(vec)} | Time: {elapsed:.2f}s")
        print(f"(Check logs at {LOG_PATH})")
        return

    print(f"\nTop {len(results)} matches for: {url}\n")
    for rank, (score, row) in enumerate(results, start=1):
        print(f"{rank:02d}. {row.get('title') or '(no title)'}")
        print(f"    Score: {score:.4f}")
        link = row.get("link") or ""
        if link:
            print(f"    Link: {link}")
        summary = (row.get("summary") or "")[:220].replace("\n", " ")
        if summary:
            print(f"    Summary: {summary}...")
        print()

    print(f"✔ Text length: {len(text)} | Embedding dim: {len(vec)} | Time: {elapsed:.2f}s")
    print(f"(Logs: {LOG_PATH})")

if __name__ == "__main__":
    main()
