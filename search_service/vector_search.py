import numpy as np
from typing import List, Dict, Optional, Any
from pgvector.psycopg2 import register_vector
from grants_db import get_connection
from data_enrichment.embedder import Embedder  # you already have this

class VectorSearcher:
    def __init__(self):
        # Load BGE-large once
        self.embedder = Embedder()

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        is_active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Embed the query_text, run ANN search over ngo_profiles.embedding (cosine),
        return rows ordered by similarity.
        """
        # 1) Build the query vector
        qvec = self.embedder.embed_batch([query_text])[0]  # np.array shape (1024,)
        qvec_list = qvec.tolist()

        # 2) Query Postgres with ORDER BY embedding <=> $1 (cosine distance)
        conn = get_connection()
        register_vector(conn)
        cur = conn.cursor()

        base_sql = """
            SELECT
                id,
                title,
                url,
                summary,
                1 - (embedding <=> %s::vector) AS cosine_similarity
            FROM ngo_profiles
            {where_clause}
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """
        where_clause = "WHERE is_active = true" if is_active_only else ""
        sql = base_sql.format(where_clause=where_clause)

        cur.execute(sql, (qvec_list, qvec_list, top_k))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        conn.close()

        results = [dict(zip(cols, r)) for r in rows]
        return results
