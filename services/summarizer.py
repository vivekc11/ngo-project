# services/summarizer.py
from __future__ import annotations
import re
from typing import List
from transformers import pipeline, AutoTokenizer

PEGASUS_MODEL = "google/pegasus-xsum"
MAX_TOKENS = 400        # per chunk
OVERLAP = 50
FINAL_WORDS = 50        # ~50 words target

_DEADLINE_PAT = re.compile(r"\b(deadline|apply by|closing date)\b", re.IGNORECASE)
_DATEY_PAT = re.compile(r"\b(\d{1,2}\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4})\b")

class Summarizer:
    def __init__(self, device: str = None):
        print("[summarizer] Loading Pegasus-XSum...")
        self.summarizer = pipeline(
            "summarization",
            model=PEGASUS_MODEL,
            tokenizer=PEGASUS_MODEL,
            device=-1,  # CPU
        )
        self.tokenizer = AutoTokenizer.from_pretrained(PEGASUS_MODEL, use_fast=True)
        print("[summarizer] Model loaded.")

    def _token_len(self, text: str) -> int:
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def _split(self, text: str, max_tokens=MAX_TOKENS, overlap=OVERLAP) -> List[str]:
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
            chunk_text = self.tokenizer.decode(tokens[start:end], skip_special_tokens=True)
            chunks.append(chunk_text)
            if end == n:
                break
            start = max(0, end - overlap)
        return chunks

    def _clean_lines(self, text: str) -> str:
        # drop lines dominated by deadlines/dates
        kept = []
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if _DEADLINE_PAT.search(s):
                continue
            # if >30% tokens are "date-like", skip
            toks = s.split()
            if toks and (len(_DATEY_PAT.findall(s)) / max(1, len(toks))) > 0.3:
                continue
            kept.append(s)
        return " ".join(kept)

    def _truncate_words(self, text: str, max_words=FINAL_WORDS) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words])

    def summarize(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        text = self._clean_lines(text)
        if not text:
            return ""

        chunks = self._split(text)
        if len(chunks) == 1:
            # direct summary
            out = self.summarizer(
                chunks[0],
                max_new_tokens=64,
                min_length=15,
                do_sample=False,
            )[0]["summary_text"]
            return self._truncate_words(out, FINAL_WORDS)

        # summarize each chunk briefly
        chunk_summaries = []
        for ch in chunks:
            cs = self.summarizer(
                ch,
                max_new_tokens=40,
                min_length=12,
                do_sample=False,
            )[0]["summary_text"]
            chunk_summaries.append(cs)

        # summarize the summaries
        mega = " ".join(chunk_summaries)
        final = self.summarizer(
            mega,
            max_new_tokens=64,
            min_length=20,
            do_sample=False,
        )[0]["summary_text"]

        final = self._truncate_words(final, FINAL_WORDS)
        return final
