# THEME DETECTION
# @author: Hina Joshua

import pandas as pd
import numpy as np
import pickle
import joblib

#list of all themes
themes = ['Gender',
       'Peacekeeping and Peacebuilding', 'Agriculture', 'Food and Nutrition',
       'Contributions', 'Coordination', 'Health', 'Water Sanitation Hygiene',
       'Protection and Human Rights', 'Mine Action',
       'Shelter and Non-Food Items', 'Climate Change and Environment',
       'Logistics and Telecommunications', 'Recovery and Reconstruction',
       'Safety and Security', 'Education', 'Humanitarian Financing',
       'Disaster Management', 'HIV/Aids',
       'Camp Coordination and Camp Management']

def themes_list():
    return themes


def detect_theme(text, model, vectorizer, themes):
    '''
    @type text: str
    @param content text 
    @type model: str (pickled model file path)
    @param (pickled model filename) multilabel classification model fitted on 92,000 ReliefWeb report content (F1 Score = 0.71)
    @type vectorizer: str
    @param (pickled vectorizer file path) Tfidf vectorizer fitted on 92,000 Relief Web report content
    @type themes: list
    @param list of 20 strings - names of unique Relief Web report themes
    @rtype themes_detected: list 
    @rparam list of Relief Web themes detected in the input text 
    '''
    # load the model from disk
    model_name = model
    # loaded_model = pickle.load(open(model_name, 'rb'))
    loaded_model = joblib.load(model_name)

    #load vectorizer
    vec_name = vectorizer
    # loaded_vectorizer = pickle.load(open(vec_name, 'rb'))
    loaded_vectorizer = joblib.load(vec_name)

    # Vectorize the text
    vector = loaded_vectorizer.transform([text])

    #make prediction
    preds = loaded_model.predict(vector).toarray()

    #map result on theme name list to get theme names detected
    themes = themes_list()
    theme_indices = list(np.where(preds == 1)[1])
    return [themes[index] for index in theme_indices]
