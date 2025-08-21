# # scripts/enrich_grants.py
# """
# Populate grants.embedding for all grants missing embeddings.
# Uses data_enrichment.embedder. Updates DB in a safe idempotent way.
# """

# import time
# import numpy as np
# from data_enrichment.embedder import Embedder
# from grants_db import fetch_all_grants, get_connection
# from pgvector.psycopg2 import register_vector

# BATCH_SIZE = 32  # embed/update in batches

# def text_for_grant(grant):
#     # Prefer long description; fallback to short or title.
#     text = grant.get("description_long") or grant.get("description_short") or ""
#     if not text:
#         text = f"{grant.get('title','')}"
#     return text

# def main():
#     embedder = Embedder()
#     grants = fetch_all_grants()
#     print(f"[enrich_grants] fetched {len(grants)} grants from DB.")
#     to_process = [g for g in grants if not g.get('embedding')]
#     print(f"[enrich_grants] {len(to_process)} grants missing embeddings.")

#     conn = get_connection()
#     register_vector(conn)  # enable pgvector adapater for this connection
#     cur = conn.cursor()

#     start = time.time()
#     for i in range(0, len(to_process), BATCH_SIZE):
#         batch = to_process[i:i+BATCH_SIZE]
#         texts = [text_for_grant(g) for g in batch]
#         embs = embedder.embed_batch(texts)  # numpy array shape (n, dim)

#         for grant, emb in zip(batch, embs):
#             link_hash = grant['link_hash']
#             # Update embedding for this grant
#             cur.execute(
#                 "UPDATE grants SET embedding = %s WHERE link_hash = %s;",
#                 (emb.tolist(), link_hash)
#             )
#         conn.commit()
#         print(f"[enrich_grants] processed {i+len(batch)} / {len(to_process)}")

#     elapsed = time.time() - start
#     print(f"[enrich_grants] Done. Time: {elapsed:.1f}s")
#     cur.close()
#     conn.close()

# if __name__ == "__main__":
#     main()


# scripts/enrich_ngo_profiles.py
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from services.embeddings import EmbeddingService
from services.summarizer import SummarizerService

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

def enrich_ngo_profiles():
    # Connect to DB
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    embedder = EmbeddingService()
    summarizer = SummarizerService(max_sentences=3)

    # Fetch rows needing enrichment
    cur.execute("""
        SELECT id, title, description
        FROM ngo_profiles
        WHERE summary IS NULL OR embedding IS NULL
        LIMIT 20;
    """)
    rows = cur.fetchall()

    for row in rows:
        text_input = f"{row['title']}\n\n{row['description']}" if row['title'] else row['description']

        # Generate summary
        summary = summarizer.summarize(row['description'])

        # Generate embedding
        embedding = embedder.encode(text_input)

        # Update DB
        cur.execute("""
            UPDATE ngo_profiles
            SET summary = %s,
                embedding = %s,
                updated_at = NOW()
            WHERE id = %s;
        """, (summary, embedding, row['id']))

        print(f"Updated NGO profile {row['id']} with summary + embedding.")

    conn.commit()
    cur.close()
    conn.close()

if __name__ == "__main__":
    enrich_ngo_profiles()
