# # scripts/enrich_ngo_profiles.py
# """
# Populate ngo_profiles.summary and ngo_profiles.embedding
# Only fill what's missing: summary IS NULL or embedding IS NULL.
# """

# import time
# from data_enrichment.embedder import Embedder
# from data_enrichment.summarizer import Summarizer
# from grants_db import get_connection
# from pgvector.psycopg2 import register_vector

# BATCH_SIZE = 16

# def fetch_ngos():
#     conn = get_connection()
#     register_vector(conn)
#     cur = conn.cursor()
#     cur.execute("""
#         SELECT id, title, description, summary, embedding
#         FROM ngo_profiles
#         ORDER BY id
#     """)
#     rows = cur.fetchall()
#     cols = [d[0] for d in cur.description]
#     cur.close(); conn.close()
#     return [dict(zip(cols, r)) for r in rows]

# def text_for_ngo(ngo):
#     title = (ngo.get("title") or "").strip()
#     desc  = (ngo.get("description") or "").strip()
#     return (title + "\n\n" + desc).strip() if title else desc

# def main():
#     embedder = Embedder()
#     summarizer = Summarizer()

#     ngos = fetch_ngos()
#     to_process = [n for n in ngos if (n.get("summary") is None) or (n.get("embedding") is None)]
#     print(f"[enrich_ngos] total={len(ngos)}; to_process={len(to_process)}")

#     conn = get_connection()
#     register_vector(conn)
#     cur = conn.cursor()

#     start = time.time()
#     for i in range(0, len(to_process), BATCH_SIZE):
#         batch = to_process[i:i+BATCH_SIZE]
#         texts = [text_for_ngo(n) for n in batch]

#         # Prepare containers
#         summaries = []
#         needs_embed = []
#         embed_texts = []

#         for n, t in zip(batch, texts):
#             # summary only if NULL
#             if n.get("summary") is None:
#                 summaries.append(summarizer.summarize(t))
#             else:
#                 summaries.append(n["summary"])

#             # embedding only if NULL
#             if n.get("embedding") is None:
#                 needs_embed.append(True)
#                 embed_texts.append(t)
#             else:
#                 needs_embed.append(False)
#                 embed_texts.append(None)

#         # Batch embed only the ones that need it
#         emb_results = []
#         if any(needs_embed):
#             emb_results_iter = iter(embedder.embed_batch([et for et in embed_texts if et is not None]))
#         else:
#             emb_results_iter = iter([])

#         for n, summary, need_emb in zip(batch, summaries, needs_embed):
#             if need_emb:
#                 emb = next(emb_results_iter)
#                 cur.execute("""
#                     UPDATE ngo_profiles
#                     SET summary = %s,
#                         embedding = %s,
#                         updated_at = NOW()
#                     WHERE id = %s
#                 """, (summary, emb.tolist(), n["id"]))
#             else:
#                 # just summary update
#                 cur.execute("""
#                     UPDATE ngo_profiles
#                     SET summary = %s,
#                         updated_at = NOW()
#                     WHERE id = %s
#                 """, (summary, n["id"]))

#         conn.commit()
#         print(f"[enrich_ngos] processed {i+len(batch)} / {len(to_process)}")

#     cur.close(); conn.close()
#     print(f"[enrich_ngos] done in {time.time()-start:.1f}s")

# if __name__ == "__main__":
#     main()

# scripts/enrich_ngo_profiles.py
"""
Populate ngo_profiles.summary and ngo_profiles.embedding (BGE 1024)
for rows missing either. Summaries are for developer inspection/logs.
"""

import time
from typing import List, Dict
import numpy as np
from pgvector.psycopg2 import register_vector
from services.embeddings import Embedder
from services.summarizer import Summarizer
from grants_db import get_connection  # you already have this

BATCH = 16

def fetch_ngos() -> List[Dict]:
    conn = get_connection()
    register_vector(conn)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, description, summary, embedding
        FROM ngo_profiles
        ORDER BY id ASC
    """)
    rows = cur.fetchall()
    cols = [c[0] for c in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(cols, r)) for r in rows]

def build_text(row: Dict) -> str:
    title = (row.get("title") or "").strip()
    desc  = (row.get("description") or "").strip()
    if title and desc:
        return f"{title}\n\n{desc}"
    return title or desc

def main():
    embedder = Embedder()
    summarizer = Summarizer()

    rows = fetch_ngos()
    to_process = [r for r in rows if (r.get("embedding") is None) or (r.get("summary") is None)]
    total = len(rows)
    need = len(to_process)
    print(f"[enrich_ngos] total={total}; to_process={need}")
    if not need:
        return

    conn = get_connection()
    register_vector(conn)
    cur = conn.cursor()

    t0 = time.time()
    for i in range(0, need, BATCH):
        batch = to_process[i:i+BATCH]
        texts = [build_text(r) for r in batch]

        # summaries (per doc)
        summaries = [summarizer.summarize(t) for t in texts]

        # embeddings (chunked & pooled)
        embs = [embedder.embed_text(t) for t in texts]

        for row, summ, emb in zip(batch, summaries, embs):
            cur.execute(
                """
                UPDATE ngo_profiles
                SET summary = %s,
                    embedding = %s,
                    updated_at = NOW()
                WHERE id = %s;
                """,
                (summ, emb.tolist(), row["id"])
            )
        conn.commit()
        print(f"[enrich_ngos] processed {i+len(batch)} / {need}")

    print(f"[enrich_ngos] done in {time.time()-t0:.1f}s")
    cur.close()
    conn.close()

if __name__ == "__main__":
    main()
