# this file is the main BM25F algorithm, for user searches
import numpy as np
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
    def __init__(self,b_meta=0.75,b_content=0.5,k1=1.2,v_content=1,v_meta=2):
        self.b_meta = b_meta
        self.b_content = b_content
        self.k1 = k1
        self.v_content = v_content
        self.v_meta = v_meta

    def calculate_bm25F(self,query_term_ids):
        # find the relevant posting from the IDs
        postings = [inv_index['inv_index'][x]['fields'] for x in query_term_ids]
        #  next initialize numpy arrays by finding the set of documents from the postings
        docs_set = list(set([key for fields_dict in postings for _, doc_freq_dict in fields_dict.items() for key,_ in doc_freq_dict.items()]))
        num_of_docs = len(docs_set)
        N = inv_index['corpus_prop']['number_of_doc_corpus']
        # then created a nested list
        num_query_terms = len(query_term_ids)
        scores_lst = []
        for doc_id in docs_set:
            inner_lst = []
            for q_i in range(num_query_terms):
                # find the term freq in the first zone
                if ('0' in postings[q_i]) and (doc_id in postings[q_i]['0']):
                    tf_cont = postings[q_i]['0'][doc_id]
                else:
                    tf_cont = 0
                if ('1' in postings[q_i]) and (doc_id in postings[q_i]['1']):
                    tf_meta = postings[q_i]['1'][doc_id]
                else:
                    tf_meta = 0
                inner_lst.append([tf_cont,tf_meta])
            scores_lst.append(inner_lst)
        scores = np.array(scores_lst).astype(float)
        # next calculate Bz for each field, 1st - make an array of lenz
        lenz = [[inv_index['doc_prop'][x]['content_length'],inv_index['doc_prop'][x]['metadata_length']] for x in docs_set]
        bz = np.array(lenz).astype(float)
        avglen_cont = inv_index['corpus_prop']['content_avdl']
        avglen_meta = inv_index['corpus_prop']['metadata_avdl']
        bz[:,0] = bz[:,0] / self.b_content * avglen_cont + (1-self.b_content)
        bz[:,1] = bz[:,1] / self.b_meta * avglen_meta + (1-self.b_meta)
        # next is the calculation of the term frequency estimate for each in zone, already calculated in scores
        scores[:,:,0] = scores[:,:,0] * self.v_content / bz[:,0][:,np.newaxis]
        scores[:,:,1] = scores[:,:,1] * self.v_meta / bz[:,1][:,np.newaxis]
        # Now with np.sum we reduce the scores to a single value, the summation
        scores = np.sum(scores, axis=-1)
        # idf
        for q_i in range(num_query_terms):
            term = str(query_term_ids[q_i])
            df = inv_index['inv_index'][term].get('df', 0)
            idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)
            scores *= idf
        # with the estimate, now we calculate the main equation
        scores = (scores*(self.k1 + 1)) / (self.k1 + scores)
        scores = np.sum(scores,axis=-1)
        scores_lst = scores.tolist()
        result = list(zip(docs_set,scores_lst))
        return result
    
    def sort_scores(self,scores):
        # this function sorts the list of tuples
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
        return sorted_scores
    
    def retrieve_data(self,sorted_scores):
        # this function takes the sorted scores and take the top ten as a lst
        doc_lst = [x[0] for x in sorted_scores][:10]
        result_lst = [doc_dict[str(x)] for x in doc_lst]
        return result_lst

# search
bm25f = BM25F()

def search(query: str) -> list:
    # Chetah 2.0 search function, input is a single string query, returns a list of results
    # first step is transforming the query
    if query:
        try:
            result = lemmatize_string(query)
            # then find the ids in the inverted index
            query_term_ids = [str(inv_index['term_ids'][x]) for x in result]
            # list of IDs, one for each query term, next is retrieve all documents where those terms occur (the union)
            scores = bm25f.calculate_bm25F(query_term_ids)
            # then sort
            sorted_docs = bm25f.sort_scores(scores)
            # then look up
            table_results = bm25f.retrieve_data(sorted_docs)
        except Exception as e:
            print(e)
            no_res = {}
            no_res['report_title'] = "Error Occurred"
            no_res['report_author'] = e
            table_results = [no_res]
    else:
        # no query string given by user
        no_res = {}
        no_res['report_title'] = "No query provided"
        table_results = [no_res]
    return table_results
