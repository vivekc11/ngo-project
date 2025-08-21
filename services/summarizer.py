# # services/summarizer.py
# from __future__ import annotations
# import re
# from typing import List
# from transformers import pipeline, AutoTokenizer

# PEGASUS_MODEL = "google/pegasus-xsum"
# MAX_TOKENS = 400        # per chunk
# OVERLAP = 50
# FINAL_WORDS = 50        # ~50 words target

# _DEADLINE_PAT = re.compile(r"\b(deadline|apply by|closing date)\b", re.IGNORECASE)
# _DATEY_PAT = re.compile(r"\b(\d{1,2}\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b")

# class Summarizer:
#     def __init__(self, device: str = None):
#         print("[summarizer] Loading Pegasus-XSum...")
#         self.summarizer = pipeline(
#             "summarization",
#             model=PEGASUS_MODEL,
#             tokenizer=PEGASUS_MODEL,
#             device=-1,  # CPU
#         )
#         self.tokenizer = AutoTokenizer.from_pretrained(PEGASUS_MODEL, use_fast=True)
#         print("[summarizer] Model loaded.")

#     def _token_len(self, text: str) -> int:
#         return len(self.tokenizer.encode(text, add_special_tokens=False))

#     def _split(self, text: str, max_tokens=MAX_TOKENS, overlap=OVERLAP) -> List[str]:
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
#             chunk_text = self.tokenizer.decode(tokens[start:end], skip_special_tokens=True)
#             chunks.append(chunk_text)
#             if end == n:
#                 break
#             start = max(0, end - overlap)
#         return chunks

#     def _clean_lines(self, text: str) -> str:
#         # drop lines dominated by deadlines/dates
#         kept = []
#         for line in text.splitlines():
#             s = line.strip()
#             if not s:
#                 continue
#             if _DEADLINE_PAT.search(s):
#                 continue
#             # if >30% tokens are "date-like", skip
#             toks = s.split()
#             if toks and (len(_DATEY_PAT.findall(s)) / max(1, len(toks))) > 0.3:
#                 continue
#             kept.append(s)
#         return " ".join(kept)

#     def _truncate_words(self, text: str, max_words=FINAL_WORDS) -> str:
#         words = text.split()
#         if len(words) <= max_words:
#             return text
#         return " ".join(words[:max_words])

#     def summarize(self, text: str) -> str:
#         text = (text or "").strip()
#         if not text:
#             return ""

#         text = self._clean_lines(text)
#         if not text:
#             return ""

#         chunks = self._split(text)
#         if len(chunks) == 1:
#             # direct summary
#             out = self.summarizer(
#                 chunks[0],
#                 max_new_tokens=64,
#                 min_length=15,
#                 do_sample=False,
#             )[0]["summary_text"]
#             return self._truncate_words(out, FINAL_WORDS)

#         # summarize each chunk briefly
#         chunk_summaries = []
#         for ch in chunks:
#             cs = self.summarizer(
#                 ch,
#                 max_new_tokens=40,
#                 min_length=12,
#                 do_sample=False,
#             )[0]["summary_text"]
#             chunk_summaries.append(cs)

#         # summarize the summaries
#         mega = " ".join(chunk_summaries)
#         final = self.summarizer(
#             mega,
#             max_new_tokens=64,
#             min_length=20,
#             do_sample=False,
#         )[0]["summary_text"]

#         final = self._truncate_words(final, FINAL_WORDS)
#         return final

# services/summarizer.py
import os
import re
import logging
from typing import List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

logger = logging.getLogger("summarizer")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(ch)

# Singletons
_SUMMARIZER = None
_DEVICE = None

# Config (override via env)
SUMM_MODEL = os.getenv("SUMM_MODEL", "google/pegasus-xsum")  # better than t5-small for short abstractive
MAX_CHARS_PER_CHUNK = int(os.getenv("SUMM_MAX_CHARS", "1800"))  # rough guard before tokenization
TARGET_WORDS = int(os.getenv("SUMM_TARGET_WORDS", "50"))        # ~50 word summaries
MAX_NEW_TOKENS = int(os.getenv("SUMM_MAX_NEW_TOKENS", "64"))   # keep short
MIN_LEN = int(os.getenv("SUMM_MIN_LEN", "30"))                 # avoid overly short outputs
MAX_LEN = int(os.getenv("SUMM_MAX_LEN", "96"))

FORBIDDEN_PATTERNS = [
    r"\bdeadline\b",
    r"\bapply by\b",
    r"\bclosing date\b",
    r"\bsubmission\b",
]

def _pick_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"

def _clean_summary(text: str) -> str:
    # Remove boilerplate lines (very short fragments, legal footer bits, etc.)
    text = text.strip()
    # Kill explicit deadline-y phrases
    for pat in FORBIDDEN_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    # Collapse whitespace, fix stray punctuation
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    # Trim to ~TARGET_WORDS words without cutting in the middle
    words = text.split()
    if len(words) > TARGET_WORDS:
        text = " ".join(words[:TARGET_WORDS]).rstrip(" ,.;:") + "…"
    return text

class Summarizer:
    """
    GPU-aware abstractive summarizer with:
      - Pegasus-XSum default (short, coherent)
      - chunking for long inputs
      - post-processing to avoid 'deadline' talk
    """
    def __init__(self, model_name: str, device: str):
        self.model_name = model_name
        self.device = device
        logger.info(f"[summarizer] Loading model: {model_name} on {device} (first run can take a bit)…")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        if device != "cpu":
            self.model.to(device)
        logger.info("[summarizer] Model loaded.")

    def _summarize_chunk(self, text: str) -> str:
        if not text:
            return ""
        inputs = self.tokenizer(
            text,
            truncation=True,
            max_length=512,  # XSum encoder limit
            return_tensors="pt"
        )
        if self.device != "cpu":
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=MAX_NEW_TOKENS,
                min_length=MIN_LEN,
                max_length=MAX_LEN,  # ignored when max_new_tokens set, but keep as guard
                num_beams=4,
                length_penalty=0.9,
                early_stopping=True,
                no_repeat_ngram_size=3,
            )
        summary = self.tokenizer.decode(output[0], skip_special_tokens=True).strip()
        return _clean_summary(summary)

    def summarize(self, text: str) -> str:
        if not text:
            return ""
        # Quick pre-trim to avoid silly inputs
        text = text.strip()
        if len(text) <= MAX_CHARS_PER_CHUNK:
            return self._summarize_chunk(text)

        # Chunk by paragraphs to keep coherence; fallback to hard cuts
        paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        chunks: List[str] = []
        buf = ""
        for p in paras:
            if len(buf) + len(p) + 2 <= MAX_CHARS_PER_CHUNK:
                buf = f"{buf}\n\n{p}" if buf else p
            else:
                if buf:
                    chunks.append(buf)
                buf = p
        if buf:
            chunks.append(buf)

        # Summarize each chunk then compress them together
        part_sums = [self._summarize_chunk(c) for c in chunks[:6]]  # cap to avoid very long meta-sum
        joined = " ".join([s for s in part_sums if s]).strip()
        return _clean_summary(joined)

def get_summarizer() -> Summarizer:
    global _SUMMARIZER, _DEVICE
    if _SUMMARIZER is None:
        _DEVICE = _pick_device()
        _SUMMARIZER = Summarizer(SUMM_MODEL, _DEVICE)
    return _SUMMARIZER
