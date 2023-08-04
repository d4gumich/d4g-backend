import requests
import pandas as pd
import math
import re
from sklearn.model_selection import train_test_split
import csv


# The official disaster categories that ReliefWeb references.
disaster_types = ['Cold Wave', 'Complex Emergency', 'Drought', 'Earthquake', 'Epidemic', 'Extratropical Cyclone',
                  'Fire', 'Flash Flood', 'Flood', 'Heat Wave', 'Insect Infestation', 'Land Slide', 'Mud Slide',
                  'Other', 'Severe Local Storm', 'Snow Avalanche', 'Storm Surge', 'Technological Disaster',
                  'Tropical Cyclone', 'Tsunami', 'Volcano', 'Wild Fire']
ids = set()
base_url = 'https://api.reliefweb.int/v1/reports?appname=apidoc&query[fields][]=language&query[value]=English'
report_url_base = 'https://api.reliefweb.int/v1/reports/'

# because of API request limits. 1000 calls/day, 1000 queries/call.
for disaster_type in disaster_types:
    for _ in range(45):
        url = base_url + f'&filter[field]=disaster_type&filter[value]=={disaster_type}&limit=10'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()["data"]
            ids.update([i['id'] for i in data if 'body' in requests.get(report_url_base + i['id']).json()['data'][0]['fields']])
            # process and store the report data as needed
        else:
            print(f"Failed to retrieve data for {disaster_type}")

# might just save the ids first and run the processes down below in another script
with open('ids.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id'])
    for id in ids:
        w.writerow([id])

def clean_text(text):
    # # Define a string containing all special characters to remove
    # special_chars = '@#$%^&*()_-+={}[]|\:;"<>/~`'
    # # Create a translation table that removes all special characters
    # translator = str.maketrans(special_chars, ' ' * len(special_chars))
    # # Use the translation table to remove all special characters from the text
    # text = text.translate(translator)

    # # Remove all occurrences of '\n' and replace with whitespace
    # text = text.replace('\n', ' ')
    # # Convert bullet points to sentences
    # text = re.sub(r'\n•', '. ', text)
    # # Convert numbered lists to sentences
    # text = re.sub(r'\n\d+\.?', '. ', text)
    # # Remove two/more whitespace characters
    # text = re.sub(r'\s{2,}', ' ', text)
    # # Remove any extra whitespace
    # text = re.sub(r'\s+', ' ', text)
    # # Add a period at the end of the text if one is not already present
    # if text[-1] != '.':
    #     text += '.'
    
    # text cleaning process the same way text is cleaned in hangul.py
    text = re.sub(
        r'(http(s)?:\/\/.)?(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)', ' ',
        text).strip()
    text = re.sub(u"(\u2018|\u2019|\u201c|\u201d|\u2013|\u2020|\u2022)", "'", text)
    text = re.sub(r'\n', ' ', text)
    return text


contents = []
disasters = []
themes = []
locations = []
formats = []

for id in ids:
    data = requests.get(report_url_base + id).json()
    content = clean_text(data['data'][0]['fields']['body'])
    contents.append(content)
    
    try:
        disaster = data['data'][0]['fields']['disaster_type']
        disasters.append([i['name'] for i in disaster])
    except KeyError:
        disasters.append(math.nan)
    
    try:
        theme = data['data'][0]['fields']['theme']
        themes.append([i['name'] for i in theme])
    except KeyError:
        themes.append(math.nan)
        
    try:
        location = data['data'][0]['fields']['country']
        locations.append([i['name'] for i in location])
    except KeyError:
        locations.append(math.nan)
        
    try:
        format = data['data'][0]['fields']['format']
        formats.append(format[0]['name'])
    except KeyError:
        formats.append(math.nan)


print("themes length: ", len(themes))
print("contents length: ", len(contents))
print("disasters length: ", len(disasters))
print("locations length: ", len(locations))
print("ids length: ", len(list(map(int, list(ids)))))
print("formats length: ", len(formats))


df = pd.DataFrame({'id': list(map(int, list(ids))),
                   'content': contents,
                   'disaster_types': disasters,
                   'themes': themes,
                   'locations': locations,
                   'format': formats})
# train_set, test_set = train_test_split(df, test_size=0.25, random_state=42)
df.to_csv('disaster_detection/collective_set.csv', index=False)
# test_set.to_csv('disaster_detection/test_set.csv', index=False)
# df.to_csv('disaster_detection/dummy_set.csv', index=False)
# print(themes)