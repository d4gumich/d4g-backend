import logging
import re
from typing import Optional

import spacy

logger = logging.getLogger(__name__)

class Sanitizer:
    """
    Utility class for redacting Personally Identifiable Information (PII) from text.
    Combines Regex for structured patterns (emails, phones) and SpaCy NER for entities (names, locations).
    """
    
    def __init__(self, model: str = "en_core_web_sm"):
        self.nlp: Optional[spacy.language.Language] = None
        try:
            self.nlp = spacy.load(model)

        except Exception as e:
            logger.warning(f"Could not load SpaCy model {model}. Entity-based redaction will be disabled. Error: {e}")
            self.nlp = None

        # Regex patterns for various PII
        self.regex_patterns = {
            "EMAIL": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            "PHONE": r'(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}',
            "POSTAL_CODE": r'\b\d{5}(?:-\d{4})?\b', # US Zip
            "IP_ADDRESS": r'\b\d{1,3}(?:\.\d{1,3}){3}\b',
            "URL": r'https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)',
            "SOCIAL_LINK": r'(?:www\.)?(?:linkedin\.com|github\.com|twitter\.com|x\.com|facebook\.com|instagram\.com|youtube\.com|tiktok\.com)(?:[-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
        }

    def redact(self, text):
        """
        Redacts PII from the given text.
        
        Args:
            text (str): Input text to sanitize.
            
        Returns:
            str: Sanitized text with placeholders.
        """
        if not text:
            return ""

        sanitized_text = text

        # 1. Redact via Regex
        for label, pattern in self.regex_patterns.items():
            sanitized_text = re.sub(pattern, f"[{label}]", sanitized_text)

        # 2. Redact via SpaCy NER
        if self.nlp:
            doc = self.nlp(sanitized_text)
            # We iterate in reverse to avoid index shifts if we were doing string replacements,
            # but here we'll collect spans and then replace at once.
            
            # Entities to redact
            redact_labels = ["PERSON", "GPE", "LOC", "FAC"]
            
            # Collect spans to redact
            spans_to_redact = []
            for ent in doc.ents:
                if ent.label_ in redact_labels:
                    spans_to_redact.append((ent.start_char, ent.end_char, ent.label_))
            
            # Sort spans by start_char descending to replace without messing up indices
            spans_to_redact.sort(key=lambda x: x[0], reverse=True)
            
            for start, end, label in spans_to_redact:
                # Map SpaCy labels to user-friendly placeholders
                placeholder = f"[{label}]"
                if label == "PERSON": placeholder = "[NAME]"
                elif label in ["GPE", "LOC", "FAC"]: placeholder = "[LOCATION]"
                
                sanitized_text = sanitized_text[:start] + placeholder + sanitized_text[end:]

        return sanitized_text

# Singleton instance for easy reuse
_sanitizer_instance = None

def get_sanitizer():
    global _sanitizer_instance
    if _sanitizer_instance is None:
        _sanitizer_instance = Sanitizer()
    return _sanitizer_instance
