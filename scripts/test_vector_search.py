import sys
from search_service.vector_search import VectorSearcher

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.test_vector_search \"your query text here\" [top_k]")
        return
    query = sys.argv[1]
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    searcher = VectorSearcher()
    results = searcher.search(query, top_k=top_k, is_active_only=True)

    print(f"\nTop {len(results)} results for: {query}\n")
    for i, r in enumerate(results, 1):
        print(f"{i:02d}. [{r['cosine_similarity']:.3f}] {r.get('title') or '(no title)'}")
        print(f"    {r.get('url')}")
        if r.get('summary'):
            # show a short preview of the summary
            s = r['summary'].strip().replace('\n', ' ')
            if len(s) > 160: s = s[:160] + '...'
            print(f"    {s}")
        print()

if __name__ == "__main__":
    main()
