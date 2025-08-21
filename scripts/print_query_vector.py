from data_enrichment.embedder import Embedder
import sys, json

if __name__ == "__main__":
    text = sys.argv[1] if len(sys.argv) > 1 else "women empowerment in Africa"
    emb = Embedder().embed_batch([text])[0]
    print(json.dumps(emb.tolist()))
