import re
import spacy
from pathlib import Path
import requests
import json

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
    # r"(\(?([0-9]+)-?\)?)"
    pattern = r"(\(?([0-9]+)-?\)?)|[\u200b]|[$+●]|^[a-zA-Z]$|[@/\\<>]|\\{2}|~"
    lemma_tokens = [x.lemma_.lower() for x in doc if 
    not x.is_stop
    and not x.like_url
    and not x.like_email
    and not x.is_space
    and not x.is_punct
    and not x.like_num
    and not re.match(pattern,x.text)]
    return lemma_tokens

def find_organization(given_path:Path):
    # this function identifies the organization based on the file
    dirs = given_path.parts #works on more then just windows
    org=None
    for ind,dir in enumerate(dirs):
        if ind>0 and dirs[ind-1] == "Chetah_data_2021":
            org = dir
            break # no need to continue
    if org is None:
        return None
    # org may be a string split by _, also make like a title
    org = org.replace("_"," ").title()
    return org

def detect_year_of_report(given_filename):
    # this function identifies
    match = re.search("[1-2]{1}[0-9]{3}",given_filename)
    if match:
        return match.group(0)
    else:
        return None

def retrieve_report_paths(root_folder):
    # This function will return a list of all file paths of pdf reports
    # matching the conditions of being a PDF and located within
    # a "clean_eng_docs" sub-directory

    # Convert the string path, to a path object
    root_folder = Path(root_folder)

    # Retrieve all Report PDF's from 'clean_eng_docs' directories
    files = list(root_folder.glob("**/clean_eng_docs/*.pdf"))

    return files

def process_pdf_path(report_path: Path,hangul_api_path: str,payload:dict):
    # This function utilizes the constants to make a call to Hangul
    with report_path.open("rb") as f:
        files = {"file":(report_path.name,f)}
        response = requests.post(hangul_api_path, files=files, data=payload)
    return response.json()