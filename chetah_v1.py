import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from configparser import SafeConfigParser
import pathlib


directory_path = pathlib.Path(__file__).parent.resolve()
configuration = SafeConfigParser()
configuration.read(f'{directory_path}/configuration.ini')

df_pdfs = pd.read_csv(configuration.get('chetah', 'dataset_path'))

# Extract summaries from PDFs
summaries = [x for x in df_pdfs.summary]


class BM25(object):
    def __init__(self, b=0.75, k1=1.6):
        self.vectorizer = TfidfVectorizer(
            norm=None, smooth_idf=False)
        self.b = b
        self.k1 = k1

    def fit(self, X):
        """ Fit IDF to documents X """
        self.vectorizer.fit(X)
        y = super(TfidfVectorizer, self.vectorizer).transform(X)
        self.avdl = y.sum(1).mean()

    def transform(self, q, X):
        """ Calculate BM25 between query q and documents X """
        b, k1, avdl = self.b, self.k1, self.avdl

        # apply CountVectorizer
        X = super(TfidfVectorizer, self.vectorizer).transform(X)
        len_X = X.sum(1).A1
        q, = super(TfidfVectorizer, self.vectorizer).transform([q])

        # convert to csc for better column slicing
        X = X.tocsc()[:, q.indices]
        denom = X + (k1 * (1 - b + b * len_X / avdl))[:, None]
        idf = self.vectorizer._tfidf.idf_[None, q.indices] - 1.
        numer = X.multiply(np.broadcast_to(idf, X.shape)) * (k1 + 1)
        return (numer / denom).sum(1).A1


bm25 = BM25()
bm25.fit(summaries)


def search(query: str) -> list:
    '''
    This is the Chetah V1 search function. It takes in a single str query and outputs a list of results
    '''
    query_sample = bm25.transform(query, summaries)

    weights = []
    for i in query_sample:
        if i > 1:
            weights.append(i)

    sorted_top = sorted(weights, key=lambda x: x, reverse=True)[:10]

    sorted_top_i = [np.where(query_sample == i) for i in sorted_top]
    top_indexes = [x[0][0] for x in sorted_top_i]

    results = []
    for i in top_indexes:
        # Process the clusters associated with the PDF
        # Create a new PDF dictionary and add it to the list of search results
        pdf = {
            'title': str(df_pdfs.Title[i]),
            'date': df_pdfs.Date[i],
            'link': str(df_pdfs.URL[i]),
            'cluster': str(df_pdfs.cluster[i]),
            # Truncate summary after 450 characters
            'summary_short': str(df_pdfs.summary[i])[:450],
            'summary_full': str(df_pdfs.summary[i]),
        }
        results.append(pdf)
    return results
