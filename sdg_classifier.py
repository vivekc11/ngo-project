# sdg_classifier.py
import yaml
import re
from collections import defaultdict
from typing import List, Dict # Corrected and added typing imports
from utils import preprocess_text, nlp

class SDGClassifier:
    def __init__(self, sdg_seeds_path: str = "sdg_seeds.yml"):
        self.sdg_keywords = self._load_sdg_seeds(sdg_seeds_path)

    def _load_sdg_seeds(self, sdg_seeds_path: str) -> Dict[str, List[str]]:
        """
        Loads SDG goals and their example phrases from the YAML file,
        preprocessing them into a searchable keyword structure.
        """
        sdg_map = defaultdict(list)
        try:
            with open(sdg_seeds_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)
                if data and 'nlu' in data:
                    for item in data['nlu']:
                        intent_name = item.get('intent')
                        examples_raw = item.get('examples', '')
                        if intent_name and examples_raw:
                            examples_list = [line.strip() for line in examples_raw.split('\n') if line.strip()]
                            preprocessed_examples = [preprocess_text(ex) for ex in examples_list]
                            sdg_map[intent_name].extend(preprocessed_examples)
        except FileNotFoundError:
            print(f"Error: {sdg_seeds_path} not found. Please ensure the file exists.")
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {sdg_seeds_path}: {e}")
        return sdg_map

    def classify_text(self, text: str) -> List[str]:
        """
        Classifies the given text into relevant SDG goals based on keyword matching.
        Returns a list of matching SDG intents.
        """
        if not self.sdg_keywords:
            return []

        preprocessed_text = preprocess_text(text)
        found_sdgs = set()

        for sdg_intent, examples in self.sdg_keywords.items():
            for example_phrase in examples:
                pattern = r'\b' + re.escape(example_phrase) + r'\b'
                if re.search(pattern, preprocessed_text):
                    found_sdgs.add(sdg_intent)
                    break
        return list(found_sdgs)

# The __main__ block is for testing this module directly, not used by the main app flow
if __name__ == "__main__":
    classifier = SDGClassifier()
    test_texts = [
        "Our project focuses on providing clean drinking water to rural communities and building new sanitation facilities.",
        "We empower women through vocational training and support female entrepreneurs in tech.",
        "Working to end extreme poverty and provide social protection for vulnerable populations, while also promoting sustainable agriculture.",
        "This initiative promotes sustainable agriculture practices and food security for all.",
        "Our work involves climate change adaptation strategies and reducing carbon emissions.",
        "We are building resilient infrastructure in urban areas and fostering local innovation.",
        "General text without clear SDG keywords."
    ]
    for i, text in enumerate(test_texts):
        print(f"\nText {i+1}: '{text}'")
        matched_sdgs = classifier.classify_text(text)
        if matched_sdgs:
            print("Matched SDGs:", matched_sdgs)
        else:
            print("No specific SDG matched.")