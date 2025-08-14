from flask import Flask, render_template, request
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime
from urllib.parse import urlparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer, util
import spacy
import logging
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ----- CONFIGURATION -----
MAX_TEXT_LENGTH = 15000  # Increased slightly for more context
SIMILARITY_WEIGHTS = {
    "embedding_sim": 0.4,
    "tfidf_sim": 0.2,
    "keyword_overlap": 0.1,
    "sector_match": 0.15,
    "target_population_match": 0.15,
    "geographic_match_boost": 0.1,
}

# --- EXAMPLE GRANTS ---
GRANTS = [
    {
        "title": "Youth Empowerment Grant for East Africa",
        "description": "Funding to support youth-led initiatives focused on education, vocational training, and leadership development in East African countries. Aims to build capacity and foster sustainable community change.",
        "application_deadline": "2025-12-31",
        "focus_areas": ["Youth", "Education", "Vocational Training", "Leadership Development"],
        "target_beneficiaries_focus": ["Young people (15-30 years)", "Adolescents", "Youth organizations"],
        "eligibility_criteria_text": "Registered NGOs in Kenya, Uganda, or Tanzania. Minimum 3 years of experience in youth development. Annual budget must be between $50,000 and $500,000. Must have local community partnerships.",
        "geographic_eligibility": ["Kenya", "Uganda", "Tanzania", "East Africa"],
        "min_budget": 50000,
        "max_budget": 500000,
        "link": "https://example.com/youth-grant",
        "keywords": ["youth", "education", "empowerment", "africa", "training", "leadership"]
    },
    {
        "title": "Community Health & Wellness Initiative (Sub-Saharan Africa)",
        "description": "Supports non-profits providing primary healthcare services, health education, and medical supplies to underserved rural communities in Sub-Saharan Africa. Emphasizes community health workers and mobile clinics for preventative care.",
        "application_deadline": "2025-07-15",
        "focus_areas": ["Healthcare", "Community Health", "Wellness", "Public Health", "Maternal Health"],
        "target_beneficiaries_focus": ["Rural communities", "Underserved populations", "Women", "Children"],
        "eligibility_criteria_text": "NGOs operating directly in Sub-Saharan African rural areas. Must demonstrate strong community engagement and long-term sustainability plans. Minimum 5 years operational experience.",
        "geographic_eligibility": ["Sub-Saharan Africa", "Africa"],
        "min_budget": 100000,
        "max_budget": 1000000,
        "link": "https://example.com/health-grant",
        "keywords": ["health", "rural", "africa", "medical", "wellness", "community"]
    },
    {
        "title": "Women in Tech & Entrepreneurship Global Fund",
        "description": "Grants for organizations empowering women through digital literacy, tech education, small business development, and microfinance in developing countries globally. Encourages innovative use of technology.",
        "application_deadline": "2025-09-01",
        "focus_areas": ["Women Empowerment", "Technology", "Entrepreneurship", "Economic Development", "Digital Literacy", "Gender Equality"],
        "target_beneficiaries_focus": ["Women", "Girls", "Female entrepreneurs", "STEM students"],
        "eligibility_criteria_text": "International NGOs with a proven track record in gender equality and economic empowerment. Focus on innovative tech solutions is a plus. Open to organizations with budgets over $200,000.",
        "geographic_eligibility": ["Global", "Developing Countries"],
        "min_budget": 200000,
        "max_budget": None,
        "link": "https://example.com/women-tech-grant",
        "keywords": ["women", "tech", "entrepreneurship", "gender", "digital", "global"]
    },
    {
        "title": "Urban Green Spaces Development Grant (Local Impact)",
        "description": "Funding for environmental NGOs creating and maintaining green spaces, urban gardens, and promoting biodiversity in densely populated urban areas. Priority given to projects with direct community involvement.",
        "application_deadline": "2025-06-20",
        "focus_areas": ["Environmental Conservation", "Urban Planning", "Biodiversity", "Sustainability", "Community Gardens"],
        "target_beneficiaries_focus": ["Urban communities", "City residents", "Local government"],
        "eligibility_criteria_text": "Local or national environmental NGOs. Projects must be within city limits. Partnerships with local authorities preferred. Budget range up to $150,000.",
        "geographic_eligibility": ["Global", "Urban Centers", "Specific City Names (e.g., Nairobi, Lagos, Mumbai)"],
        "min_budget": 10000,
        "max_budget": 150000,
        "link": "https://example.com/urban-green-grant",
        "keywords": ["green", "urban", "environment", "biodiversity", "sustainability", "community"]
    },
    {
        "title": "Disaster Preparedness & Response Fund (Global Reach)",
        "description": "Supports NGOs working on disaster risk reduction, emergency response, and post-disaster recovery in high-risk regions worldwide. Focus on community resilience building and early warning systems.",
        "application_deadline": "2025-11-01",
        "focus_areas": ["Disaster Relief", "Emergency Response", "Community Resilience", "Humanitarian Aid", "Risk Reduction"],
        "target_beneficiaries_focus": ["Disaster-affected communities", "Vulnerable populations", "Refugees"],
        "eligibility_criteria_text": "International or national NGOs with active disaster response programs and established emergency protocols. Capacity for rapid deployment required. No budget limits specified.",
        "geographic_eligibility": ["Global", "High-Risk Regions"],
        "min_budget": None,
        "max_budget": None,
        "link": "https://example.com/disaster-grant",
        "keywords": ["disaster", "emergency", "resilience", "humanitarian", "relief"]
    }
]

# ----- NLP MODELS -----
try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    logging.info("SentenceTransformer model loaded successfully.")
except Exception as e:
    logging.error(f"Error loading SentenceTransformer model: {e}. Semantic similarity might be affected.", exc_info=True)
    sentence_model = None

try:
    nlp = spacy.load("en_core_web_sm")
    logging.info("spaCy model 'en_core_web_sm' loaded successfully.")
except OSError:
    logging.warning("spaCy model 'en_core_web_sm' not found. Attempting to download...")
    try:
        from spacy.cli import download
        download("en_core_web_sm")
        nlp = spacy.load("en_core_web_sm")
        logging.info("spaCy model downloaded and loaded successfully.")
    except Exception as e:
        logging.error(f"Could not download or load spaCy model: {e}. Some NLP features may be limited.", exc_info=True)
        nlp = None


# ----- UTILITY FUNCTIONS -----

def validate_url(url: str) -> bool:
    """Validates if the URL is well-formed and uses allowed schemes."""
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False

async def extract_text_from_url_async(url: str) -> str:
    """
    Asynchronously fetches content from a URL and extracts clean text.
    Handles various request-related errors.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=15, headers=headers) as response:
                response.raise_for_status()
                soup = BeautifulSoup(await response.text(), "html.parser")
                for tag in soup(["script", "style", "noscript", "header", "footer", "nav", "aside", "form"]):
                    tag.extract()
                text = soup.get_text(separator=" ", strip=True)
                return text[:MAX_TEXT_LENGTH]
    except aiohttp.ClientTimeout:
        logging.error(f"Timeout error fetching URL: {url}")
        return "Error: Request to the website timed out. The website might be slow or unresponsive."
    except aiohttp.ClientConnectionError:
        logging.error(f"Connection error fetching URL: {url}")
        return "Error: Could not connect to the website. Please check the URL or your internet connection."
    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP error {e.status} fetching URL: {url}")
        return f"Error: Received HTTP {e.status} from the website. Check if the URL is correct or if the website is accessible."
    except Exception as e:
        logging.error(f"An unexpected error occurred during URL extraction for {url}: {e}", exc_info=True)
        return f"Error: An unexpected issue occurred while processing the website. Please try again."

def extract_text_from_url(url: str) -> str:
    """Synchronous wrapper for async URL extraction."""
    return asyncio.run(extract_text_from_url_async(url))

def preprocess_text(text: str) -> str:
    """
    Cleans and preprocesses text using spaCy for lemmatization and stop word removal.
    If spaCy is not loaded, falls back to basic regex cleaning.
    """
    if not isinstance(text, str):
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.lower()
    if nlp:
        doc = nlp(text)
        tokens = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct and not token.is_space and token.is_alpha]
        return " ".join(tokens)
    else:
        text = re.sub(r'[^a-z0-9\s]', '', text)
        return ' '.join(text.split()).lower()

def extract_keywords_from_doc(spacy_doc) -> set:
    """Extracts relevant keywords (lemmas of alpha tokens) from a spaCy Doc object."""
    return set(token.lemma_ for token in spacy_doc if not token.is_stop and token.is_alpha and not token.is_punct)

def compute_tfidf_similarity(text1: str, text2: str) -> float:
    """Computes TF-IDF cosine similarity between two preprocessed text strings."""
    if not text1 or not text2:
        return 0.0
    try:
        tfidf = TfidfVectorizer(stop_words='english', max_features=5000)
        tfidf_matrix = tfidf.fit_transform([text1, text2])
        return float(cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0])
    except Exception as e:
        logging.warning(f"Error computing TF-IDF similarity: {e}")
        return 0.0

def match_grant(website_raw_text: str, website_doc_for_nlp, grant: dict) -> dict:
    """
    Calculates a match score and eligibility for a given grant against NGO website content.
    """
    match_details = {
        "score": 0.0,
        "color": "gray",
        "is_eligible": True,
        "reasons_for_ineligibility": [],
        "link": grant.get("link")
    }

    website_text_clean = website_doc_for_nlp.text if nlp else preprocess_text(website_raw_text) # use nlp from sacpy , if fail, use regex
    website_keywords = extract_keywords_from_doc(website_doc_for_nlp) if nlp else set(re.findall(r'\b\w+\b', website_text_clean))

    # --- Eligibility Checks ---
    try:
        deadline = datetime.strptime(grant['application_deadline'], "%Y-%m-%d")
        if deadline < datetime.now():  # check deadline with current date
            match_details["is_eligible"] = False
            match_details["reasons_for_ineligibility"].append("Deadline has passed.")
    except (ValueError, TypeError):
        match_details["is_eligible"] = False
        match_details["reasons_for_ineligibility"].append("Invalid or missing deadline format for grant.")

    if not match_details["is_eligible"]:
        return match_details

    grant_geo_eligible = [preprocess_text(loc) for loc in grant.get("geographic_eligibility", [])]
    ngo_locations = []
    if nlp:
        ngo_locations = [ent.text.lower() for ent in website_doc_for_nlp.ents if ent.label_ in ["GPE", "LOC"]] # geoplitical entitiy or physical location

    geo_match_found = False
    # clean up the code below - geolocation elgibilty 
    if grant_geo_eligible:
        if "global" in grant_geo_eligible or "worldwide" in grant_geo_eligible or  \
        "global" in website_text_clean or "worldwide" in website_text_clean:
            geo_match_found = True
        else:
            for grant_loc_kw in grant_geo_eligible:
                if grant_loc_kw in website_text_clean:
                    geo_match_found = True
                    break
                for ngo_loc_entity in ngo_locations:
                    if sentence_model and util.cos_sim(sentence_model.encode(ngo_loc_entity), sentence_model.encode(grant_loc_kw)) > 0.75:
                        geo_match_found = True
                        break
                if geo_match_found:
                    break

        if not geo_match_found and "global" not in grant_geo_eligible:
            match_details["is_eligible"] = False
            match_details["reasons_for_ineligibility"].append("Geographic focus mismatch.")

    if not match_details["is_eligible"]:
        return match_details

    ngo_estimated_budget = 250000
    min_budget = grant.get("min_budget")
    max_budget = grant.get("max_budget")

    if min_budget is not None and ngo_estimated_budget < min_budget:
        match_details["is_eligible"] = False
        match_details["reasons_for_ineligibility"].append(f"NGO budget (${ngo_estimated_budget}) is below grant's minimum required (${min_budget}).")
    if max_budget is not None and ngo_estimated_budget > max_budget:
        match_details["is_eligible"] = False
        match_details["reasons_for_ineligibility"].append(f"NGO budget (${ngo_estimated_budget}) exceeds grant's maximum allowed (${max_budget}).")

    if not match_details["is_eligible"]:
        return match_details

    # --- Similarity Scoring ---
    grant_combined_text = f"{grant.get('title', '')} {grant.get('description', '')} " \
                         f"{' '.join(grant.get('focus_areas', []))} " \
                         f"{' '.join(grant.get('target_beneficiaries_focus', []))} " \
                         f"{grant.get('eligibility_criteria_text', '')}"
    grant_text_clean = preprocess_text(grant_combined_text)

    embedding_sim = 0.0
    if sentence_model:
        try:
            embeddings = sentence_model.encode([website_text_clean, grant_text_clean], convert_to_tensor=True)
            embedding_sim = float(util.cos_sim(embeddings[0], embeddings[1]))
        except Exception as e:
            logging.warning(f"Error computing embedding similarity for grant {grant.get('title')}: {e}")
            embedding_sim = 0.0

    tfidf_score = compute_tfidf_similarity(website_text_clean, grant_text_clean)
    grant_keywords_processed = set(preprocess_text(kw) for kw in grant.get('keywords', []))
    overlap_score = len(website_keywords.intersection(grant_keywords_processed)) / len(grant_keywords_processed) if grant_keywords_processed else 0.0

    sector_score = 0.0
    ngo_themes = [ent.text.lower() for ent in website_doc_for_nlp.ents if ent.label_ in ["ORG", "PRODUCT", "WORK_OF_ART", "EVENT", "NORP"]]
    if not ngo_themes:
        common_words = [word for word in website_text_clean.split() if len(word) > 3 and word not in nlp.Defaults.stop_words][:50]
        ngo_themes.extend(common_words)

    for grant_focus_area in grant.get('focus_areas', []):
        if preprocess_text(grant_focus_area) in website_text_clean:
            sector_score = 1.0
            break

    pop_score = 0.0
    for grant_target_pop in grant.get('target_beneficiaries_focus', []):
        if preprocess_text(grant_target_pop) in website_text_clean:
            pop_score = 1.0
            break

    raw_final_score = (
        embedding_sim * SIMILARITY_WEIGHTS["embedding_sim"] +
        tfidf_score * SIMILARITY_WEIGHTS["tfidf_sim"] +
        overlap_score * SIMILARITY_WEIGHTS["keyword_overlap"] +
        sector_score * SIMILARITY_WEIGHTS["sector_match"] +
        pop_score * SIMILARITY_WEIGHTS["target_population_match"]
    )

    if geo_match_found and (grant_geo_eligible and "global" not in grant_geo_eligible):
        raw_final_score += SIMILARITY_WEIGHTS["geographic_match_boost"]

    final_score_percentage = round(min(1.0, max(0.0, raw_final_score)) * 100, 2)
    match_details["score"] = final_score_percentage

    if final_score_percentage >= 80:
        match_details["color"] = "green"
    elif final_score_percentage >= 50:
        match_details["color"] = "yellow"
    else:
        match_details["color"] = "gray"

    return match_details

# ----- FLASK APP -----
app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    match_results = []
    error_message = None

    if request.method == "POST":
        url = request.form.get("url", "").strip()
        if not validate_url(url):
            return render_template("index.html", error="Invalid URL. Please enter a valid HTTP/HTTPS URL.")

        logging.info(f"Received request for URL: {url}")
        website_raw_text = extract_text_from_url(url)
        if website_raw_text.startswith("Error"):
            error_message = website_raw_text
            logging.error(f"Scraping failed for {url}: {error_message}")
        else:
            website_processed_text = preprocess_text(website_raw_text)
            website_doc_for_nlp = None
            if nlp:
                website_doc_for_nlp = nlp(website_processed_text)
            else:
                logging.warning("spaCy model not loaded, proceeding with limited NLP features.")
                website_doc_for_nlp = type('obj', (object,), {'text': website_processed_text, 'ents': []})()

            eligible_grants_found = False
            for grant in GRANTS: # use a database here/ scalable / psql
                match_data = match_grant(website_raw_text, website_doc_for_nlp, grant)
                match_results.append({
                    "title": grant["title"],
                    "description": grant["description"],
                    "score": match_data["score"],
                    "color": match_data["color"],
                    "link": match_data["link"],
                    "is_eligible": match_data["is_eligible"],
                    "reasons_for_ineligibility": match_data["reasons_for_ineligibility"]
                })
                if match_data["is_eligible"]:
                    eligible_grants_found = True
                else:
                    logging.info(f"Grant '{grant['title']}' is ineligible for '{url}'. Reasons: {', '.join(match_data['reasons_for_ineligibility'])}")

            if not eligible_grants_found and not error_message:
                error_message = "No eligible grants found based on your NGO's profile. Please ensure the URL is correct or try a different one."

            match_results.sort(key=lambda x: (x["is_eligible"], x["score"]), reverse=True)

    return render_template("index.html", matches=match_results, error=error_message)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
# port 5000