import json
import spacy
from pathlib import Path

# Set your path to the json files resulting from navigate_reports.py
process_dir = Path("E:/process_output")

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
    # Or anything that looks like an email, may need for html tags stuff
    # Next get rid of new line characters and spaces, and finally punctuation
    print("beginning of lemmatize string")
    print(doc)
    lemma_tokens = [x.lemma_ for x in doc if 
    not x.is_stop
    and not x.like_url
    and not x.like_email
    and not x.is_space
    and not x.is_punct]
    return lemma_tokens

def generate_doc_tuples(path:Path):
    # this function is given a path to a json
    # and returns a list of tuples generated
    with path.open("r",encoding='utf-8') as f:
        data = json.load(f)
        # first, let's combine the data which is a list into a single string
        content = data['full_content']
    return content

#def generate_doc_tag_tuples(path:Path):
    

# Will need to figure out a way for unicode 8 issues, for spanish text and non-breaking whitespace
test_path = process_dir / "res-824.json"
result = generate_doc_tuples(test_path)
tokens = lemmatize_string(result)
print(tokens)