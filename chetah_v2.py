import pandas as pd
import numpy as np

from configparser import ConfigParser
# this could go in the above block
# provides a library for deadling with .ini files, a sort of config windows
# file that is standard on other languages. Here it is to retrieve data
import pathlib
# library that turns string paths into "path" objects, wild honestly

directory_path = pathlib.Path(__file__).parent.resolve()
# the __file__ is the name of the currently executing code file, chained, it
# looks at the parent directory of it, then resolves???
configuration = ConfigParser() # instance
configuration.read(f'{directory_path}/configuration.ini')

# to read in the clusters csv
df = pd.read_csv(configuration.get('chetah', 'dataset_path'))

print(df.head(5))
print(df.columns)
