# scripts/run_ngo_profile_and_search.py
"""
Test script: profile an NGO url, then search grants by vector similarity.
Usage:
    python scripts/run_ngo_profile_and_search.py https://example.org --k 10
"""

import sys
import argparse
from search_service.ngo_profiler import profile_url_and_save
from search_service.vector_search import search_by_embedding

def main():
    p = argparse.ArgumentParser()
    p.add_argument("url", help="NGO website URL to profile")
    p.add_argument("--k", type=int, default=10, help="Top-K results")
    args = p.parse_args()

    profile = profile_url_and_save(args.url)
    emb = profile["embedding"]
    print("[test] Searching grants by embedding ...")
    res = search_by_embedding(emb, top_k=args.k)
    for i, r in enumerate(res, 1):
        print(f"{i}. [{r['similarity']:.4f}] {r['title']}\n   {r['link']}\n   {r['description_short']}\n")

if __name__ == "__main__":
    main()
