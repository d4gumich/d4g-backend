import pandas as pd
import ast
import numpy as np

# def evaluate_string(value):
#     if isinstance(value, str) and value != 'nan' and value != '':
#         return ast.literal_eval(value)
#     else:
#         return np.nan

df = pd.read_csv('disaster_detection/dummy_set.csv')
training_df = pd.read_csv('disaster_detection/training_set.csv')
# df['disaster_types'] = df['disaster_types'].apply(evaluate_string)
# df['themes'] = df['themes'].apply(evaluate_string)
# df['locations'] = df['locations'].apply(evaluate_string)

content1 = df['content'][0]
print(training_df.shape[0])

# some don't have themes. Instead of not adding in the thing. Set up try-exception blocks to take disaster_types
# and content. So we will not have full dataset, some incomplete data, but at least I can have more data.
# Hina mentioned doing something like semi-supervised learning methods that can possibly incorporate both
# unlabeled/labeled data.

# consider also adding locations columns when scraping as that is a variable returned in detect() in hangul.py

# after scraping raw data, might add columns for keywords.