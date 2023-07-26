import torch
from transformers import BertTokenizer, BertForTokenClassification
from torch.utils.data import DataLoader, Dataset
from torch.nn import CrossEntropyLoss
from tqdm import tqdm
from collections import defaultdict
import pandas as pd
import numpy as np

# ReliefWeb disaster categories:
disaster_types = ['Cold Wave', 'Complex Emergency', 'Drought', 'Earthquake', 'Epidemic', 'Extratropical Cyclone',
                  'Fire', 'Flash Flood', 'Flood', 'Heat Wave', 'Insect Infestation', 'Land Slide', 'Mud Slide',
                  'Other', 'Severe Local Storm', 'Snow Avalanche', 'Storm Surge', 'Technological Disaster',
                  'Tropical Cyclone', 'Tsunami', 'Volcano', 'Wild Fire']

training_df = pd.read_csv('training_set.csv')  # training_df.shape[0] = 1378
test_df = pd.read_csv('test_set.csv')  # test_df.shape[0] = 460

train_texts = training_df['content']
train_labels = training_df['disaster_types']

labels_binary_array = np.array([np.isin(disaster_types, input_list).astype(int) for input_list in train_labels])

# def get_disasters(content):
#     disasters = []
#     content = content.lower()
#     if any(word in content for word in ['covid', 'coronavirus']):
#         # disasters.append('COVID-19')
#         disasters.append('Pandemic')
#     if 'hurricane' in content:
#         disasters.append('Hurricane')
#     if 'earthquake' in content:
#         disasters.append('Earthquake')
#     if 'flood' in content:
#         disasters.append('Flood')
#     if 'tsunami' in content:
#         disasters.append('Tsunami')
#     if 'wildfire' in content:
#         disasters.append('Wildfire')
#     if 'cyclone' in content:
#         disasters.append('Cyclone')
#     if 'tornado' in content:
#         disasters.append('Tornado')
#     if 'drought' in content:
#         disasters.append('Drought')
#     if 'landslide' in content:
#         disasters.append('Landslide')
#     if 'typhoon' in content:
#         disasters.append('Typhoon')
#     if len(disasters) == 0:
#         return None
#     else:
#         # return dict(Counter(disasters)) #no point counting it because it is only added to list once
#         return disasters
