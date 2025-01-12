import json
import spacy
from pathlib import Path

# This process references the following two docs and post
# https://spacy.io/usage/linguistic-features#tokenization
# https://towardsdatascience.com/setting-up-text-preprocessing-pipeline-using-scikit-learn-and-spacy-e09b9b76758f

# First we need to import the spacy English library
nlp = spacy.load("en_core_web_sm")

def lemmatize_string(given_string):
    # then we split into spacy tokens object called a doc
    doc = nlp(given_string)
    # next step is removing stop words with spacy's language model
    # We also want to remove anything that looks like a url
    # Or anything that looks like an email
    # Next get rid of new line characters and spaces, and finally punctuation
    lemma_tokens = [x.lemma_ for x in doc if 
            not x.is_stop
            and not x.like_url
            and not x.like_email
            and not x.is_space
            and not x.is_punct]
    return lemma_tokens

