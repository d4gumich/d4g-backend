# this file is the main BM25F algorithm, for user searches
import pandas as pd
from configparser import SafeConfigParser
import pathlib

# load the inverted index and table
directory_path = pathlib.Path(__file__).parent.resolve()
configuration = SafeConfigParser()
configuration.read(f'{directory_path}/configuration.ini')

inv_index = configuration.get('chetah','inv_path')
print(inv_index)