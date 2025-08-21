# data_enrichment/summarizer.py
import re
from typing import Optional
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import torch

# Single small model is fine; it's dev-only visibility
_SUMM_MODEL = "t5-small"

# Precompile filters
_DROP_LINE_PATTERNS = [
    r'\bdeadline\b',
    r'\bclosing date\b',
    r'\bapply by\b',
    r'\bfunding\b',
    r'\bbudget\b',
    r'\beligibility\b',
    r'\bgrant amount\b',
    r'\bcontributions\b',
    r'\bcall for proposals\b',
    r'\bexpected outcomes?\b',
    r'\bfunding information\b',
]
_DROP_LINE_RE = re.compile("|".join(_DROP_LINE_PATTERNS), re.IGNORECASE)

# crude date-like tokens to avoid leaking dates into the summary
_DATE_TOKEN_RE = re.compile(r'\b(\d{1,2}[-/]\d{1,2}([-/]\d{2,4})?|\d{4})\b')

# hard input safety cap
_MAX_INPUT_CHARS = 6000

class Summarizer:
    def __init__(self, device: Optional[str] = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = 0 if device == "cuda" else -1

        self.tokenizer = AutoTokenizer.from_pretrained(_SUMM_MODEL)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(_SUMM_MODEL)
        self.pipe = pipeline(
            "summarization",
            model=self.model,
            tokenizer=self.tokenizer,
            device=self.device
        )

    def _preclean(self, text: str) -> str:
        # drop boilerplate lines
        kept = []
        for line in text.splitlines():
            l = line.strip()
            if not l:
                continue
            if _DROP_LINE_RE.search(l):
                continue
            kept.append(l)
        cleaned = " ".join(kept)

        # remove date-like tokens
        cleaned = _DATE_TOKEN_RE.sub("", cleaned)

        # collapse whitespace, cap size
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) > _MAX_INPUT_CHARS:
            cleaned = cleaned[:_MAX_INPUT_CHARS]
        return cleaned

    def summarize(self, text: str, target_words: int = 50) -> str:
        if not text:
            return ""

        cleaned = self._preclean(text)
        if not cleaned:
            return ""

        # ~50 words target → approximate tokens; then trim to ~50 words post-gen
        res = self.pipe(
            cleaned,
            max_new_tokens=120,   # allow enough room
            min_length=20,
            do_sample=False,
        )[0]["summary_text"].strip()

        # Post-trim to ~50 words (hard cap)
        words = res.split()
        if len(words) > target_words:
            res = " ".join(words[:target_words])

        # tidy punctuation spacing
        res = re.sub(r"\s+([,.;:])", r"\1", res)
        return res
