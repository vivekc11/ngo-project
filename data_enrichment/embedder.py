# data_enrichment/embedder.py
import os
import numpy as np
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")

class Embedder:
    def __init__(self, model_name: str = MODEL_NAME):
        print(f"[embedder] Loading model: {model_name} (this may take a while)...")
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"[embedder] ERROR loading {model_name}: {e}")
            raise
        print("[embedder] Model loaded.")

    def embed(self, text: str) -> np.ndarray:
        """Embed a single text. Returns a normalized numpy vector (1-D)."""
        if not text:
            return np.zeros(self.model.get_sentence_embedding_dimension(), dtype=np.float32)
        emb = self.model.encode([text], convert_to_numpy=True)[0]
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        return emb.astype(np.float32)

    def embed_batch(self, texts):
        """Batch embed: returns numpy array (n, dim)."""
        embs = self.model.encode(texts, convert_to_numpy=True)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embs = embs / norms
        return embs.astype(np.float32)
