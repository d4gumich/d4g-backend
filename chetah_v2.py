# this file is the main BM25F algorithm, for user searches
import pandas as pd
from configparser import ConfigParser
import pathlib
import json
from chetah_utils import lemmatize_string

# load the inverted index and table
directory_path = pathlib.Path(__file__).parent.resolve()
configuration = ConfigParser()
configuration.read(f'{directory_path}/configuration.ini')

with open(configuration.get('chetah','inv_path'),'r') as f:
    inv_index = json.load(f)

with open(configuration.get('chetah','doc_path'),'r') as f:
    doc_dict = json.load(f)

# define the BM25F class
class BM25F():
    def __init__(self,b_meta=0.75,b_content=0.5,k1=1.2):
        self.b_meta = b_meta
        self.b_content = b_content
        self.k1 = k1


# search
def search(query: str) -> list:
    # Chetah 2.0 search function, input is a single string query, returns a list of results
    # first step is transforming the query
    result = lemmatize_string(query)
    print(result)
    # then find the ids in the inverted index
    query_term_ids = [inv_index['term_ids'][x] for x in result]
    print(query_term_ids)
    # list of IDs, one for each query term, next is retrieve all documents where those terms occur (the union)
    print(inv_index['inv_index'][str(query_term_ids[1])])