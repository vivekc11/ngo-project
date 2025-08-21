# # services/embeddings.py
# from __future__ import annotations
# import math
# from typing import List, Tuple
# from transformers import AutoTokenizer
# from sentence_transformers import SentenceTransformer
# import numpy as np

# BGE_MODEL_NAME = "BAAI/bge-large-en-v1.5"
# CHUNK_TOKENS = 400
# CHUNK_OVERLAP = 50

# class Embedder:
#     def __init__(self, model_name: str = BGE_MODEL_NAME, device: str = None):
#         print(f"[embedder] Loading model: {model_name} (this may take a while)...")
#         self.model = SentenceTransformer(model_name, device=device or "cpu")
#         self.tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
#         print("[embedder] Model loaded.")

#     def _token_len(self, text: str) -> int:
#         return len(self.tokenizer.encode(text, add_special_tokens=False))

#     def _split_into_chunks(self, text: str, max_tokens=CHUNK_TOKENS, overlap=CHUNK_OVERLAP) -> List[str]:
#         if not text:
#             return []
#         tokens = self.tokenizer.encode(text, add_special_tokens=False)
#         n = len(tokens)
#         if n <= max_tokens:
#             return [text]

#         chunks = []
#         start = 0
#         while start < n:
#             end = min(start + max_tokens, n)
#             chunk_tokens = tokens[start:end]
#             chunk_text = self.tokenizer.decode(chunk_tokens, skip_special_tokens=True)
#             chunks.append(chunk_text)
#             if end == n:
#                 break
#             start = max(0, end - overlap)
#         return chunks

#     def embed_text(self, text: str) -> np.ndarray:
#         """
#         Chunk -> embed each -> length-weighted mean -> 1024-dim vector (float32).
#         """
#         text = (text or "").strip()
#         if not text:
#             return np.zeros((1024,), dtype=np.float32)

#         chunks = self._split_into_chunks(text)
#         if not chunks:
#             return np.zeros((1024,), dtype=np.float32)

#         # embed per-chunk
#         embs = self.model.encode(chunks, normalize_embeddings=True, convert_to_numpy=True)
#         # weights by token length of each chunk (avoid division by zero)
#         weights = np.array([max(1, self._token_len(c)) for c in chunks], dtype=np.float32)
#         weights = weights / weights.sum()
#         pooled = (embs * weights[:, None]).sum(axis=0).astype(np.float32)
#         return pooled

#     def embed_batch_texts(self, texts: List[str]) -> np.ndarray:
#         """
#         Convenience: sequentially embeds each text with chunking+pooling.
#         Returns array (N, 1024).
#         """
#         out = [self.embed_text(t) for t in texts]
#         return np.vstack(out)

# services/embeddings.py
import os
import logging
from typing import List, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

# ---- logging ----
logger = logging.getLogger("embeddings")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

# Singletons
_EMBEDDER = None
_DEVICE = None

# Config (override via env if needed)
MODEL_NAME = os.getenv("BGE_MODEL", "BAAI/bge-large-en-v1.5")
BATCH_SIZE = int(os.getenv("BGE_BATCH", "32"))

def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():  # Apple Silicon
        return "mps"
    return "cpu"

class _BGEEmbedder:
    """
    Thin wrapper around SentenceTransformer that:
      - loads once (GPU if available)
      - returns L2-normalized numpy vectors (float32), dim=1024 for bge-large
    """
    def __init__(self, model_name: str, device: str):
        self.model_name = model_name
        self.device = device
        logger.info(f"[embedder] Loading model: {model_name} on {device} (this may take a while)...")
        # sentence-transformers handles dtype automatically; you can set trust_remote_code via env if needed
        self.model = SentenceTransformer(model_name, device=device)
        logger.info("[embedder] Model loaded.")

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        # normalize_embeddings=True makes vectors unit-length for cosine similarity
        vecs = self.model.encode(
            texts,
            batch_size=BATCH_SIZE,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        # Ensure float32 for pgvector friendliness
        if vecs.dtype != np.float32:
            vecs = vecs.astype(np.float32, copy=False)
        return vecs

def get_embedder() -> _BGEEmbedder:
    """
    Global accessor: loads once, reuses thereafter.
    """
    global _EMBEDDER, _DEVICE
    if _EMBEDDER is None:
        _DEVICE = _pick_device()
        _EMBEDDER = _BGEEmbedder(MODEL_NAME, _DEVICE)
    return _EMBEDDER
