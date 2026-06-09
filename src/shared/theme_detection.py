# THEME DETECTION
# @author: Hina Joshua

import logging
from typing import Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

# list of all themes
themes = [
    "Gender",
    "Peacekeeping and Peacebuilding",
    "Agriculture",
    "Food and Nutrition",
    "Contributions",
    "Coordination",
    "Health",
    "Water Sanitation Hygiene",
    "Protection and Human Rights",
    "Mine Action",
    "Shelter and Non-Food Items",
    "Climate Change and Environment",
    "Logistics and Telecommunications",
    "Recovery and Reconstruction",
    "Safety and Security",
    "Education",
    "Humanitarian Financing",
    "Disaster Management",
    "HIV/Aids",
    "Camp Coordination and Camp Management",
]

# Cache for models
_model_cache: dict[str, Any] = {}


def themes_list():
    return themes


def detect_theme(text, model_path, vectorizer_path, themes):
    """
    @type text: str
    @param content text
    @type model_path: str (pickled model file path)
    @param (pickled model filename) multilabel classification model fitted on 92,000 ReliefWeb report content
    @type vectorizer_path: str
    @param (pickled vectorizer file path) Tfidf vectorizer fitted on 92,000 Relief Web report content
    @type themes: list
    @param list of 20 strings - names of unique Relief Web report themes
    @rtype themes_detected: list
    @rparam list of Relief Web themes detected in the input text
    """
    # Load model (cached)
    if model_path not in _model_cache:
        logger.info(f"Loading Theme Detection model from {model_path}...")
        _model_cache[model_path] = joblib.load(model_path)
    loaded_model = _model_cache[model_path]

    # Load vectorizer (cached)
    if vectorizer_path not in _model_cache:
        logger.info(f"Loading Theme Detection vectorizer from {vectorizer_path}...")
        _model_cache[vectorizer_path] = joblib.load(vectorizer_path)
    loaded_vectorizer = _model_cache[vectorizer_path]

    # Vectorize the text
    vector = loaded_vectorizer.transform([text])

    # make prediction
    preds = loaded_model.predict(vector).toarray()

    # map result on theme name list to get theme names detected
    themes = themes_list()
    theme_indices = list(np.where(preds == 1)[1])
    return [themes[index] for index in theme_indices]
