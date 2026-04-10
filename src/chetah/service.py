import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from typing import List, Dict, Any
from sklearn.feature_extraction.text import TfidfVectorizer
from configparser import ConfigParser
from src.core.config import settings
from chetah_utils import lemmatize_string

# Base directory for the project
BASE_DIR = Path(__file__).parent.parent.parent

# Load configuration
config = ConfigParser()
config.read(BASE_DIR / "configuration.ini")

# --- Chetah V1 Setup ---
df_pdfs = pd.read_csv(BASE_DIR / config.get('chetah', 'dataset_path'))
summaries = [x for x in df_pdfs.summary]

class BM25:
    def __init__(self, b=0.75, k1=1.6):
        self.vectorizer = TfidfVectorizer(norm=None, smooth_idf=False)
        self.b = b
        self.k1 = k1
        self.avdl = 0.0

    def fit(self, X):
        self.vectorizer.fit(X)
        y = self.vectorizer.transform(X)
        self.avdl = y.sum(1).mean()

    def transform(self, q, X):
        b, k1, avdl = self.b, self.k1, self.avdl
        X = self.vectorizer.transform(X)
        len_X = X.sum(1).A1
        q_vec, = self.vectorizer.transform([q])
        X = X.tocsc()[:, q_vec.indices]
        denom = X + (k1 * (1 - b + b * len_X / avdl))[:, None]
        idf = self.vectorizer._tfidf.idf_[None, q_vec.indices] - 1.
        numer = X.multiply(np.broadcast_to(idf, X.shape)) * (k1 + 1)
        return (numer / denom).sum(1).A1

bm25_v1 = BM25()
bm25_v1.fit(summaries)

# --- Chetah V2 Setup ---
with open(BASE_DIR / config.get('chetah', 'inv_path'), 'r') as f:
    inv_index = json.load(f)

with open(BASE_DIR / config.get('chetah', 'doc_path'), 'r') as f:
    doc_dict = json.load(f)

class BM25F:
    def __init__(self, b_meta=0.75, b_content=0.5, k1=1.2, v_content=1, v_meta=2):
        self.b_meta = b_meta
        self.b_content = b_content
        self.k1 = k1
        self.v_content = v_content
        self.v_meta = v_meta

    def calculate_bm25F(self, query_term_ids: List[str]) -> List[tuple]:
        postings = [inv_index['inv_index'][x]['fields'] for x in query_term_ids]
        docs_set = list(set([key for fields_dict in postings for _, doc_freq_dict in fields_dict.items() for key, _ in doc_freq_dict.items()]))
        N = inv_index['corpus_prop']['number_of_doc_corpus']
        num_query_terms = len(query_term_ids)
        
        scores_lst = []
        for doc_id in docs_set:
            inner_lst = []
            for q_i in range(num_query_terms):
                tf_cont = postings[q_i].get('0', {}).get(doc_id, 0)
                tf_meta = postings[q_i].get('1', {}).get(doc_id, 0)
                inner_lst.append([tf_cont, tf_meta])
            scores_lst.append(inner_lst)
        
        scores = np.array(scores_lst).astype(float)
        lenz = [[inv_index['doc_prop'][x]['content_length'], inv_index['doc_prop'][x]['metadata_length']] for x in docs_set]
        bz = np.array(lenz).astype(float)
        avglen_cont = inv_index['corpus_prop']['content_avdl']
        avglen_meta = inv_index['corpus_prop']['metadata_avdl']
        bz[:, 0] = bz[:, 0] / self.b_content * avglen_cont + (1 - self.b_content)
        bz[:, 1] = bz[:, 1] / self.b_meta * avglen_meta + (1 - self.b_meta)
        
        scores[:, :, 0] = scores[:, :, 0] * self.v_content / bz[:, 0][:, np.newaxis]
        scores[:, :, 1] = scores[:, :, 1] * self.v_meta / bz[:, 1][:, np.newaxis]
        scores = np.sum(scores, axis=-1)
        
        for q_i in range(num_query_terms):
            term = str(query_term_ids[q_i])
            df = inv_index['inv_index'][term].get('df', 0)
            idf = np.log((N - df + 0.5) / (df + 0.5) + 1.0)
            scores *= idf
            
        scores = (scores * (self.k1 + 1)) / (self.k1 + scores)
        scores = np.sum(scores, axis = -1)
        return list(zip(docs_set, scores.tolist()))

bm25f_v2 = BM25F()

def search_v1(query: str) -> List[Dict[str, Any]]:
    query_sample = bm25_v1.transform(query, summaries)
    weights = [i for i in query_sample if i > 1]
    sorted_top = sorted(weights, reverse=True)[:10]
    top_indexes = [np.where(query_sample == i)[0][0] for i in sorted_top]
    
    results = []
    for i in top_indexes:
        results.append({
            'title': str(df_pdfs.Title[i]),
            'date': str(df_pdfs.Date[i]),
            'link': str(df_pdfs.URL[i]),
            'cluster': str(df_pdfs.cluster[i]),
            'summary_short': str(df_pdfs.summary[i])[:450],
            'summary_full': str(df_pdfs.summary[i]),
        })
    return results

def search_v2(query: str) -> List[Dict[str, Any]]:
    if not query:
        return []
    
    tokens = lemmatize_string(query)
    if not tokens:
        return []
        
    query_term_ids = [str(inv_index['term_ids'][x]) for x in tokens if x in inv_index['term_ids']]
    if not query_term_ids:
        return []
        
    scores = bm25f_v2.calculate_bm25F(query_term_ids)
    sorted_docs = sorted(scores, key=lambda x: x[1], reverse=True)[:10]
    doc_ids = [x[0] for x in sorted_docs]
    return [doc_dict[str(doc_id)] for doc_id in doc_ids]
