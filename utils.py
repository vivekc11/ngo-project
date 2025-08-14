import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import spacy
import hashlib
from typing import List, Dict, Optional

# Setup models
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"Warning: spaCy model 'en_core_web_sm' not loaded. Please run 'python -m spacy download en_core_web_sm'. Error: {e}")
    nlp = None

try:
    sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
except Exception as e:
    print(f"Warning: SentenceTransformer model 'all-MiniLM-L6-v2' not loaded. Error: {e}")
    sentence_model = None

SIMILARITY_WEIGHTS: Dict[str, float] = {
    "embedding_sim": 0.4,
    "tfidf_sim": 0.2,
    "keyword_overlap": 0.1,
    "sector_match": 0.15,
    "target_population_match": 0.15,
    "geographic_match_boost": 0.1,
}

def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def generate_link_hash(link: str) -> str:
    return hashlib.md5(link.encode('utf-8')).hexdigest()

async def extract_text_from_url_async(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36)"}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20, headers=headers) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), "html.parser")
                for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                    tag.decompose()
                return soup.get_text(separator=" ", strip=True)[:15000]
    except aiohttp.ClientError as e:
        return f"Error: Network or client issue during scraping: {e}"
    except Exception as e:
        return f"Error: Could not scrape site. Reason: {e}"

def extract_text_from_url(url: str) -> str:
    return asyncio.run(extract_text_from_url_async(url))

def preprocess_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text).lower()
    if nlp:
        doc = nlp(text)
        tokens = [token.lemma_ for token in doc if not token.is_stop and token.is_alpha]
        return " ".join(tokens)
    return re.sub(r"[^a-z0-9\s]", "", text).lower()

def extract_keywords_from_doc(doc) -> set:
    relevant_pos = {"NOUN", "PROPN", "ADJ"}
    return set(token.lemma_ for token in doc if not token.is_stop and token.is_alpha and token.pos_ in relevant_pos)

def compute_tfidf_similarity(text1: str, text2: str) -> float:
    try:
        tfidf = TfidfVectorizer(stop_words="english")
        matrix = tfidf.fit_transform([text1, text2])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except Exception as e:
        print(f"Error computing TF-IDF similarity: {e}")
        return 0.0