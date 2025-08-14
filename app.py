from flask import Flask, render_template, request
from grant_matcher import match_all_grants
from utils import extract_text_from_url, preprocess_text, nlp, validate_url
from typing import List, Dict, Optional, Tuple

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index() -> str:
    match_results: List[Dict] = []
    error_message: Optional[str] = None

    if request.method == "POST":
        url: str = request.form.get("url", "").strip()
        if not validate_url(url):
            return render_template("index.html", error="Invalid URL. Please enter a valid HTTP/HTTPS URL.")

        website_raw_text: str = extract_text_from_url(url)
        if website_raw_text.startswith("Error"):
            error_message = website_raw_text
        else:
            website_processed_text: str = preprocess_text(website_raw_text)
            website_doc = nlp(website_processed_text) if nlp else None

            match_results, error_message = match_all_grants(website_raw_text, website_doc)

    return render_template("index.html", matches=match_results, error=error_message)