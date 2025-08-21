import psycopg2
import torch
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load MiniLM
logger.info("Loading MiniLM model...")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# DB connection
conn = psycopg2.connect(
    dbname="ngo_v1_vector",
    user="postgres",
    password="pSQL@superuser",   # <- replace with your actual DB password
    host="localhost",
    port=5432
)
cur = conn.cursor()

# Fetch grants without embeddings
cur.execute("SELECT link_hash, title, description_long FROM grants WHERE embedding IS NULL;")
rows = cur.fetchall()
logger.info(f"Found {len(rows)} grants without embeddings.")

for link_hash, title, description_long in rows:
    text = f"{title}. {description_long or ''}"
    emb = model.encode(text, convert_to_numpy=True).astype(np.float32).tolist()

    # Update DB
    cur.execute("UPDATE grants SET embedding = %s WHERE link_hash = %s;", (emb, link_hash))

conn.commit()
cur.close()
conn.close()
logger.info("✅ Finished updating grant embeddings.")
