import json
import re
from chetah_utils import lemmatize_string

from pathlib import Path
from collections import Counter, defaultdict

PROCESS_DIR = "E:/process_output"
REPORT_DIR = "E:/Chetah_data_2021-20241103T230242Z-001/Chetah_data_2021"

# local tuple collection
tuples = []
vocab = {}

def process_jsons(output_dir):
    # directory of process output
    docId_i = 0
    doc_ids = {}
    termId_i = 0
    term_ids = {}
    doc_prop = {}
    tup_lst = []
    # given a dictory of the process output, turns into tuples
    for path in output_dir.iterdir():
        with path.open("r",encoding='utf-8') as f:
            data=json.load(f)
            if 'Error' in data:
                pass
            else:
                # valid file, retrieve doc length information
                if path.name in doc_ids.values():
                    # doc encountered before
                    print(f"Encountered document: {path.name} previously")
                else:
                    print(path.name)
                 











# So we require 3 different lookups for this inverted index and a global of constants
# 1) The length of each field in the doc, average length
process_dir = Path(PROCESS_DIR)
process_results = process_jsons(process_dir)