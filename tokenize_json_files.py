import json
import re
import spacy
from pathlib import Path

# Set your path to the json files resulting from navigate_reports.py
process_dir = Path("E:/process_output")

# local tuple collection
tuples = []
vocab = {}

# This process references the following two docs and post
# https://spacy.io/usage/linguistic-features#tokenization
# https://towardsdatascience.com/setting-up-text-preprocessing-pipeline-using-scikit-learn-and-spacy-e09b9b76758f

# First we need to import the spacy English library
nlp = spacy.load("en_core_web_sm")

def lemmatize_string(given_string):
    # then we split into spacy tokens object called a doc
    doc = nlp(given_string)
    # next step is removing stop words with spacy's language model
    # We also want to remove anything that looks like a url, email
    # Next get rid of new line characters and spaces, and finally punctuation
    # and anything that is like a phone number
    pattern = r"(\(?([0-9]+)-?\)?)"
    lemma_tokens = [x.lemma_.lower() for x in doc if 
    not x.is_stop
    and not x.like_url
    and not x.like_email
    and not x.is_space
    and not x.is_punct
    and not x.like_num
    and not re.match(pattern,x.text)]
    return lemma_tokens

def process_jsons(output_dir):
    # directory of process output
    docId_i = 0
    termId_i = 0
    doc_dict = {}
    doc_ids = {}
    for path in output_dir.iterdir():
        # with each path, filter any with an error key
        with path.open("r",encoding='utf-8') as f:
            data = json.load(f)
            if 'Error' in data:
                print(path)
            else:
                # valid file, retrieve doc length information
                if path.name in doc_ids.values():
                    # doc encountered before
                    print(f"Encountered document: {path.name} previously")
                else:
                    # new doc, add to dictionary 
                    doc_ids[docId_i] = data['metadata']['File name']
                    print(f"doc_ids:{docId_i} + {doc_ids[docId_i]} + {path.name}")
                    docId_i = docId_i+1
                    # then pull out, the lemmatized tokens
                    doc_tokens = lemmatize_string(data['full_content'])
                    # and also the metadata tokens, they may not all be present
                    meta_data_str = ""
                    meta_data_tokens = []
                    # first author
                    if data['metadata']['Author'] is not None:
                        meta_data_str = meta_data_str + " " + data['metadata']['Author']
                    # summary parameters
                    if data['document_summary_parameters']['themes_detected'] is not None:
                        meta_data_str = meta_data_str + " " + " ".join(data['document_summary_parameters']['themes_detected'])
                    if data['document_summary_parameters']['top_locations'] is not None:
                        # Some times it is a dictionary instead of a list, check res-1.json
                        meta_data_str = meta_data_str + " " + " ".join(data['document_summary_parameters']['top_locations'])
                    if data['document_summary_parameters']['_detected_disasters'] is not None:
                        meta_data_str = meta_data_str + " " + " ".join(data['document_summary_parameters']['_detected_disasters'])
                    if meta_data_str:
                        meta_data_tokens = meta_data_tokens + lemmatize_string(meta_data_str)
                    print(f"doc_tokens: {doc_tokens}")
                    print(f"meta_data_tokens: {meta_data_tokens}")
                    



# So we require 3 different lookups for this inverted index and a global of constants
# 1) The length of each field in the doc, average length 
process_jsons(process_dir)


# Will need to figure out a way for unicode 8 issues, for spanish text and non-breaking whitespace
#test_path = process_dir / "res-824.json"
#result = generate_doc_tuples(test_path)
#print(tokens)