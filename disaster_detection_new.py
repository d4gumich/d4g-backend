# NEW DISASTER DETECTION
# @author: Takao Kakegawa

import pickle
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
import re
import pandas as pd
import numpy as np
import scipy.sparse as sp
from tensorflow import keras
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

import nltk
nltk.download('stopwords')
from nltk.corpus import stopwords

# Helper functions that pre-process raw text before we input into model classifiers.

def cleanHtml(text):
    '''
    @type text: str
    @rtype: str  
    @rparam string with HTLM tags removed.
    '''
    # removes any HTML tags.
    cleantext = re.sub(re.compile('<.*?>'), ' ', str(text))
    return cleantext

def cleanPunc(text):
    '''
    @type text: str 
    @rtype: str 
    @rparam string with punctuation or special characters removed.
    '''
    # further cleaning of any punctuation or special characters
    res = re.sub(r'[?|!|\'|"|#]',r'',text)
    res = re.sub(r'[.|,|)|(|\|/]',r' ',res)
    res = res.strip()
    res = res.replace("\n"," ")
    return res

def cleanAbbrev(text):
    '''
    @type text: str
    @rtype: str  
    @rparam string with abbreviated texts fixed to non-abbreviated format.
    '''
    text = re.sub(r"what's", "what is ", text)
    text = re.sub(r"\'s", " ", text)
    text = re.sub(r"\'ve", " have ", text)
    text = re.sub(r"can't", "cannot ", text)
    text = re.sub(r"n't", " not ", text)
    text = re.sub(r"i'm", "i am ", text)
    text = re.sub(r"\'re", " are ", text)
    text = re.sub(r"\'d", " would ", text)
    text = re.sub(r"\'ll", " will ", text)
    text = re.sub(r"\'scuse", " excuse ", text)
    text = re.sub('\W', ' ', text)
    text = re.sub('\s+', ' ', text)
    text = text.strip(' ')
    return text

def clean_text(text):
    '''
    @type text: str
    @rtype: str 
    @rparam string with cleanHtml, cleanAbbrev, cleanPunc applied.
    '''
    text = text.lower()
    text = cleanHtml(text)
    text = cleanAbbrev(text)
    text = cleanPunc(text)
    return text

disaster_types = ['Cold Wave','Drought','Earthquake','Epidemic','Extratropical Cyclone',
 'Fire','Flash Flood','Flood','Heat Wave','Insect Infestation','Land Slide','Mud Slide',
 'Other','Severe Local Storm','Snow Avalanche','Storm Surge','Technological Disaster',
 'Tropical Cyclone','Tsunami','Volcano','Wild Fire']

# Model prediction function.
def disaster_prediction(text, vectorizer, model_name):
  ''' returns predicted disaster type labels from trained NN classifier model.
      @type text: str
      @param vectorizer: (pickled vectorizer file path) Tfidf vectorizer fitted on 113,000 Relief Web report content
      @param model_name: (pickled model file path) Keras NN multilabel classification model fitted on 113,000 Relief Web report content
      @rtype: list
      @rparam: list of disaster types from disaster_types list predicted by NN model.
    '''    
    tfidf = joblib.load(vectorizer)
    model = keras.models.load_model(model_name)
    text_vec = tfidf.transform([clean_text(text)])
    y_hat = model.predict(text_vec.toarray())
    y_hat = np.round(y_hat)
    disasters = [disaster for disaster, val in zip(disaster_types, y_hat[0]) if val == 1]
    return disasters