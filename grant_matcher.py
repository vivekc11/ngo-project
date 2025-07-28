# grant_matcher.py
from utils import preprocess_text, extract_keywords_from_doc, compute_tfidf_similarity, sentence_model, SIMILARITY_WEIGHTS, nlp
from grants_db import fetch_all_grants
from sentence_transformers import util
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import re

def match_grant(website_raw_text: str, website_doc, grant: Dict) -> Dict:
    """
    Matches a single grant against the NGO's website text.
    'grant' dictionary now comes from the database.
    """
    match_details: Dict = {
        "score": 0.0,
        "color": "gray",
        "is_eligible": True,
        "reasons_for_ineligibility": [],
        "link": grant.get("link")
    }

    website_text_clean: str = website_doc.text if website_doc else preprocess_text(website_raw_text)
    website_keywords: set = extract_keywords_from_doc(website_doc) if website_doc else set(re.findall(r'\b\w+\b', website_text_clean))

    deadline: Optional[datetime] = grant.get('application_deadline')
    if deadline:
        now_aware: datetime = datetime.now(timezone.utc).astimezone(deadline.tzinfo) if deadline.tzinfo else datetime.now()
        if deadline < now_aware:
            match_details["is_eligible"] = False
            match_details["reasons_for_ineligibility"].append("Deadline has passed.")
    else:
        match_details["is_eligible"] = False
        match_details["reasons_for_ineligibility"].append("Invalid or missing deadline.")

    if not match_details["is_eligible"]:
        return match_details

    grant_description: str = grant.get('description_long') or grant.get('description_short', '')
    grant_text: str = (
        f"{grant.get('title', '')} {grant_description} "
        f"{' '.join(grant.get('focus_areas', []))} "
        f"{' '.join(grant.get('target_beneficiaries', []))} "
        f"{' '.join(grant.get('geographic_eligibility', []))} "
        f"{' '.join(grant.get('keywords', []))}"
    )
    grant_text_clean: str = preprocess_text(grant_text)

    embedding_sim: float = 0.0
    if sentence_model:
        try:
            embeddings = sentence_model.encode([website_text_clean, grant_text_clean], convert_to_tensor=True)
            embedding_sim = float(util.cos_sim(embeddings[0], embeddings[1]))
        except Exception as e:
            print(f"Error computing embedding similarity: {e}")
            pass

    tfidf_score: float = compute_tfidf_similarity(website_text_clean, grant_text_clean)
    
    db_keywords: set = set(preprocess_text(kw) for kw in grant.get("keywords", []) if kw)
    
    grant_keywords: set = db_keywords
    if not grant_keywords and nlp:
        grant_doc_for_keywords = nlp(preprocess_text(grant_text)) # Use grant_text for keywords if DB is empty
        grant_keywords = extract_keywords_from_doc(grant_doc_for_keywords)

    overlap_score: float = len(website_keywords.intersection(grant_keywords)) / len(grant_keywords) if grant_keywords else 0.0

    sector_match: bool = False
    for area in grant.get("focus_areas", []):
        if preprocess_text(area) in website_text_clean:
            sector_match = True
            break
    
    pop_match: bool = False
    for pop_target in grant.get("target_beneficiaries", []):
        if preprocess_text(pop_target) in website_text_clean:
            pop_match = True
            break

    raw_final_score: float = (
        embedding_sim * SIMILARITY_WEIGHTS["embedding_sim"] +
        tfidf_score * SIMILARITY_WEIGHTS["tfidf_sim"] +
        overlap_score * SIMILARITY_WEIGHTS["keyword_overlap"] +
        float(sector_match) * SIMILARITY_WEIGHTS["sector_match"] +
        float(pop_match) * SIMILARITY_WEIGHTS["target_population_match"]
    )

    final_score_percentage: float = round(min(1.0, max(0.0, raw_final_score)) * 100, 2)
    match_details["score"] = final_score_percentage

    if final_score_percentage >= 80:
        match_details["color"] = "green"
    elif final_score_percentage >= 50:
        match_details["color"] = "yellow"
    else:
        match_details["color"] = "gray"

    match_details["sdg_tags"] = grant.get("sdg_tags", [])
    match_details["title"] = grant.get("title", "N/A")

    return match_details

def match_all_grants(website_raw_text: str, website_doc) -> Tuple[List[Dict], Optional[str]]:
    """
    Fetches all active grants from the database and matches them against the website text.
    """
    match_results: List[Dict] = []
    error_message: Optional[str] = None
    eligible_grants_found: bool = False

    GRANTS_FROM_DB: List[Dict] = fetch_all_grants()
    if not GRANTS_FROM_DB:
        return [], "No grants found in the database. Please run the scraper or populate fake data."

    for grant in GRANTS_FROM_DB:
        match_data = match_grant(website_raw_text, website_doc, grant)
        
        match_results.append({
            "title": grant.get("title", "N/A"),
            "description": grant.get("description_short", ""),
            "score": match_data["score"],
            "color": match_data["color"],
            "link": match_data["link"],
            "is_eligible": match_data["is_eligible"],
            "reasons_for_ineligibility": match_data["reasons_for_ineligibility"],
            "sdg_tags": match_data.get("sdg_tags", [])
        })
        if match_data["is_eligible"]:
            eligible_grants_found = True

    match_results.sort(key=lambda x: (x["is_eligible"], x["score"]), reverse=True)

    if not eligible_grants_found:
        error_message = "No eligible grants found based on your NGO's profile. Please refine your profile or check back later."
    else:
        error_message = None

    return match_results, error_message