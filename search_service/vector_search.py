# import numpy as np
# from typing import List, Dict, Optional, Any
# from pgvector.psycopg2 import register_vector
# from grants_db import get_connection
# from data_enrichment.embedder import Embedder  # you already have this

# class VectorSearcher:
#     def __init__(self):
#         # Load BGE-large once
#         self.embedder = Embedder()

#     def search(
#         self,
#         query_text: str,
#         top_k: int = 10,
#         is_active_only: bool = True,
#     ) -> List[Dict[str, Any]]:
#         """
#         Embed the query_text, run ANN search over ngo_profiles.embedding (cosine),
#         return rows ordered by similarity.
#         """
#         # 1) Build the query vector
#         qvec = self.embedder.embed_batch([query_text])[0]  # np.array shape (1024,)
#         qvec_list = qvec.tolist()

#         # 2) Query Postgres with ORDER BY embedding <=> $1 (cosine distance)
#         conn = get_connection()
#         register_vector(conn)
#         cur = conn.cursor()

#         base_sql = """
#             SELECT
#                 id,
#                 title,
#                 url,
#                 summary,
#                 1 - (embedding <=> %s::vector) AS cosine_similarity
#             FROM ngo_profiles
#             {where_clause}
#             ORDER BY embedding <=> %s::vector
#             LIMIT %s;
#         """
#         where_clause = "WHERE is_active = true" if is_active_only else ""
#         sql = base_sql.format(where_clause=where_clause)

#         cur.execute(sql, (qvec_list, qvec_list, top_k))
#         rows = cur.fetchall()
#         cols = [d[0] for d in cur.description]
#         cur.close()
#         conn.close()

#         results = [dict(zip(cols, r)) for r in rows]
#         return results


# search_service/vector_search.py
import logging
from typing import List, Dict, Any

import numpy as np
from grants_db import get_connection
from pgvector.psycopg2 import register_vector

from services.embeddings import get_embedder

logger = logging.getLogger("vector_search")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler("logs/vector_search.log", encoding="utf-8")
    ch = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] [%(name)s] %(message)s")
    fh.setFormatter(fmt); ch.setFormatter(fmt)
    logger.addHandler(fh); logger.addHandler(ch)

def ann_search_with_filters(embedding: np.ndarray, top_k: int = 50) -> List[Dict[str, Any]]:
    if embedding is None:
        logger.error("[ann_search_with_filters] embedding is None")
        return []
    conn = get_connection()
    register_vector(conn)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, url, summary, description,
               1 - (embedding <=> %s::vector) AS score
        FROM ngo_profiles
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %s::vector
        LIMIT %s;
        """,
        (embedding.tolist(), embedding.tolist(), max(top_k, 10)),
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    cur.close(); conn.close()
    return [dict(zip(cols, r)) for r in rows]

def search_from_text(text: str, top_k: int = 10) -> List[Dict[str, Any]]:
    if not text or not text.strip():
        logger.error("[search_from_text] empty text")
        return []
    emb = get_embedder().embed_one(text.strip())
    return ann_search_with_filters(emb, top_k=top_k)

def search_from_profile(profile: Dict[str, Any], top_k: int = 10) -> List[Dict[str, Any]]:
    if not profile:
        logger.error("[search_from_profile] profile is None/empty")
        return []
    emb = profile.get("embedding")
    if emb is None:
        logger.error("[search_from_profile] profile has no embedding")
        return []
    return ann_search_with_filters(emb, top_k=top_k)
