# services/embeddings.py
from __future__ import annotations
import math
from typing import List, Tuple
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
import numpy as np

BGE_MODEL_NAME = "BAAI/bge-large-en-v1.5"
CHUNK_TOKENS = 400
CHUNK_OVERLAP = 50

class Embedder:
    def __init__(self, model_name: str = BGE_MODEL_NAME, device: str = None):
        print(f"[embedder] Loading model: {model_name} (this may take a while)...")
        self.model = SentenceTransformer(model_name, device=device or "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        print("[embedder] Model loaded.")

    def _token_len(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def _split_into_chunks(self, text: str, max_tokens=CHUNK_TOKENS, overlap=CHUNK_OVERLAP) -> List[str]:
        if not text:
            return []
        tokens = self.tokenizer.encode(text, add_special_tokens=False)
        n = len(tokens)
        if n <= max_tokens:
            return [text]

        chunks = []
        start = 0
        while start < n:
            end = min(start + max_tokens, n)
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
            chunks.append(chunk_text)
            if end == n:
                break
            start = max(0, end - overlap)
        return chunks

    def embed_text(self, text: str) -> np.ndarray:
        """
        Chunk -> embed each -> length-weighted mean -> 1024-dim vector (float32).
        """
        text = (text or "").strip()
        if not text:
            return np.zeros((1024,), dtype=np.float32)

        chunks = self._split_into_chunks(text)
        if not chunks:
            return np.zeros((1024,), dtype=np.float32)

        # embed per-chunk
        embs = self.model.encode(chunks, normalize_embeddings=True, convert_to_numpy=True)
        # weights by token length of each chunk (avoid division by zero)
        weights = np.array([max(1, self._token_len(c)) for c in chunks], dtype=np.float32)
        weights = weights / weights.sum()
        pooled = (embs * weights[:, None]).sum(axis=0).astype(np.float32)
        return pooled

    def embed_batch_texts(self, texts: List[str]) -> np.ndarray:
        """
        Convenience: sequentially embeds each text with chunking+pooling.
        Returns array (N, 1024).
        """
        out = [self.embed_text(t) for t in texts]
        return np.vstack(out)
