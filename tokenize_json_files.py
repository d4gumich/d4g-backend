import json
import re
import spacy
import pandas as pd
from pathlib import Path
from collections import Counter, defaultdict

# Set your path to the json files resulting from navigate_reports.py
process_dir = Path("E:/process_output")

# Set your path to the original PDF files
report_dir = "E:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021"

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
    # r"(\(?([0-9]+)-?\)?)"
    pattern = r"(\(?([0-9]+)-?\)?)|[\u200b]|[$+●]|^[a-zA-Z]$|[@/\\<>]|\\{2}"
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
    doc_ids = {}
    termId_i = 0
    term_ids = {}
    doc_prop = {}
    tup_lst = []
    for path in output_dir.iterdir():
        # with each path, filter any with an error key
        with path.open("r",encoding='utf-8') as f:
            data = json.load(f)
            if 'Error' in data:
                pass
            else:
                # valid file, retrieve doc length information
                if path.name in doc_ids.values():
                    # doc encountered before
                    print(f"Encountered document: {path.name} previously")
                else:
                    # new doc, add to dictionary 
                    doc_ids[docId_i] = data['metadata']['File name']
                    #print(f"doc_ids:{docId_i} + {doc_ids[docId_i]} + {path.name}")
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
                        location_string_accum = []
                        for element in data['document_summary_parameters']['top_locations']:
                            if isinstance(element,str):
                                # item is string, just append
                                location_string_accum.append(element)
                            elif isinstance(element,dict):
                                # item is a dictionary, extract the name
                                location_string_accum.append(element.get('name'))
                        meta_data_str = meta_data_str + " " + " ".join(location_string_accum)
                    if data['document_summary_parameters']['_detected_disasters'] is not None:
                        meta_data_str = meta_data_str + " " + " ".join(data['document_summary_parameters']['_detected_disasters'])
                    if meta_data_str:
                        meta_data_tokens = meta_data_tokens + lemmatize_string(meta_data_str)

                    # we are also going to pull important docproperties for BM25F
                    doc_prop[docId_i] = {}
                    doc_prop[docId_i]['content_length'] = len(doc_tokens)
                    doc_prop[docId_i]['metadata_length'] = len(meta_data_tokens)

                    # checking content tokens against term ids (could do this faster with defaultdict, but needs research)
                    fields = [doc_tokens, meta_data_tokens]
                    for field in fields:
                        for term_str in field:
                            if term_str not in term_ids:
                                term_ids[term_str] = termId_i
                                termId_i = termId_i + 1

                    # then produce a tuple based on field, 1 - content, 2 - metadata
                    content_counts = Counter(doc_tokens)
                    metadata_counts = Counter(meta_data_tokens)
                    doc_specific_content_tup_lst = [(term_ids[x[0]],1,docId_i,x[1]) for x in content_counts.items()]
                    doc_specific_metadata_tup_lst = [(term_ids[x[0]],2,docId_i,x[1]) for x in metadata_counts.items()]
                    tup_lst = tup_lst + doc_specific_content_tup_lst + doc_specific_metadata_tup_lst
    return (doc_prop,doc_ids,term_ids,tup_lst)

def sort_combine_tuples(process_items:tuple):
    # This function sorts and create the inverted index
    # process_items's element order is doc_prop, doc_ids, term_ids and then the big tup_lst
    process_items.sort(key=lambda x: (x[0],x[1],-x[3]))
    # nested default, allows a tree-leaf pattern for the lists (we have 2 fields recall)
    inv_index = defaultdict(lambda: defaultdict(list))
    for termID,fieldID,docID,freq in process_items:
        inv_index[termID][fieldID].append((docID,freq))
    inv_index = {term: dict(fields) for term, fields in inv_index.items()}
    return inv_index

def find_organization(file_name):
    # this function identifies the organization based on the file
    #dirs = str_path.split("\\")
    root_folder = Path(report_dir)
    path = str(list(root_folder.glob(f"**/clean_eng_docs/{file_name}"))[0])
    dirs = path.split("\\")
    for ind,dir in enumerate(dirs):
        if ind>0:
            if dirs[ind-1] == "Chetah_data_2021":
                org = dirs[ind]
    # org may be a string split by _
    org = org.replace("_"," ").title()
    return org

def detect_year_of_report(given_filename):
    # this function identifies
    match = re.search("[1-2]{1}[0-9]{3}",given_filename)
    if match:
        return match.group(0)
    else:
        return None
    return x



def create_dataframe(output_dir,doc_ids):
    # This function combines all fields into a single dataframe for a csv
    lst = []
    for path in output_dir.iterdir():
        filt_dict = {}
        # now pull out the necessary metadata minus
        with path.open("r",encoding='utf=8') as f:
            data = json.load(f)
            if 'Error' not in data:
                # first look up the file's ID with a generator that returns the first match, otherwise None
                filt_dict['docID'] = [key for key,value in doc_ids.items() if value == data['metadata']['File name']]
                # No date of web access, data based on relief web
                filt_dict['report_title'] = data['document_title'] #may be null, list of lists (inner list is font size,string)
                filt_dict['report_author'] = data['metadata']['Author']
                # organization data comes from the path, 
                filt_dict['organization_name'] = find_organization(data['metadata']['File name'])
                # date_of_report (originally published), not in hangul output
                filt_dict['doc_creation_date'] = data['metadata']['doc_created_date'] 
                filt_dict['doc_modified_date'] = data['metadata']['doc_modified_date']
                filt_dict['year_of_report'] = detect_year_of_report(data['metadata']['File name'])
                filt_dict['report_type'] = data['report_type']
                filt_dict['pages_in_report'] = data['metadata']['No.of Pages']
                filt_dict['language_of_doc'] = data['document_language']['language']
                location_string_accum = []
                for element in data['document_summary_parameters']['top_locations']:
                    if isinstance(element,str):
                        # item is string, just append
                        location_string_accum.append(element)
                    elif isinstance(element,dict):
                        # item is a dictionary, extract the name
                        location_string_accum.append(element.get('name'))
                filt_dict['locations_report'] = location_string_accum
                filt_dict['themes'] = data['document_summary_parameters']['themes_detected']
                filt_dict['summary'] = data['generated_summary']
                # No report download date available from hangul our dataset currently
                # No link to google drive storage currently (may be able to fix this one?)
                filt_dict['file_name'] = data['metadata']['File name']
                filt_dict['cleaned_text_content'] = data['content']
                filt_dict['key_phrases_words'] = data['keywords']
                lst.append(filt_dict)
    df = pd.DataFrame.from_records(lst)
    return df

# So we require 3 different lookups for this inverted index and a global of constants
# 1) The length of each field in the doc, average length 
process_results = process_jsons(process_dir)
sorted_results = sort_combine_tuples(process_results[3])
results_to_store = {}
results_to_store['doc_prop'] = process_results[0]
results_to_store['doc_ids'] = process_results[1]
results_to_store['term_ids'] = process_results[2]
results_to_store['inv_index'] = sorted_results
# save the inverted index to file
with open("dataset/inv_index.json","w")as file:
    json.dump(results_to_store,file)

# next create the dense dataframe
with open("dataset/inv_index.json","r")as file:
    data = json.load(file)
frame = create_dataframe(process_dir,data['doc_ids'])
frame.to_csv('doc_table.csv',encoding='utf-8',index=False)