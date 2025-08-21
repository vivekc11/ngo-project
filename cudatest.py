from transformers import AutoModelForSeq2SeqLM

try:
    AutoModelForSeq2SeqLM.from_pretrained("google/pegasus-xsum", local_files_only=True)
    print("✅ Model already downloaded")
except Exception as e:
    print("❌ Not cached locally:", e)
