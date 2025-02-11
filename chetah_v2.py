# this file is the main BM25F algorithm, for user searches
import pandas as pd
from configparser import ConfigParser
import pathlib
import json

# load the inverted index and table
directory_path = pathlib.Path(__file__).parent.resolve()
configuration = ConfigParser()
configuration.read(f'{directory_path}/configuration.ini')

with open(configuration.get('chetah','inv_path'),'r') as f:
    inv_index = json.load(f)
print(inv_index)

# load the excel file
