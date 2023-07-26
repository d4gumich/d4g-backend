import pandas as pd
import numpy as np
import spacy
import requests
import re
from disaster_method import get_disasters

# url = "https://api.reliefweb.int/v1/reports?appname=apidoc&profile=list&preset=latest&limit=5&language=en"
# response = requests.get(url)
#
# if response.status_code == 200:
#     data = response.json()
#     text = data['data'][0]['fields']['body']
# else:
#     print("Failed to retrieve data")
#
# # text cleaning as done in hangul.py
# text = re.sub(r'(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)', ' ',
#               text).strip()
# text = re.sub(u"(\u2018|\u2019|\u201c|\u201d|\u2013|\u2020|\u2022)", "'", text)
# text = re.sub(r'\n', ' ', text)

# print(text)
# print(get_disasters(text))