import requests
import pandas as pd
import re
from sklearn.model_selection import train_test_split

# The official disaster categories that ReliefWeb references.
disaster_types = ['Cold Wave', 'Complex Emergency', 'Drought', 'Earthquake', 'Epidemic', 'Extratropical Cyclone',
                  'Fire', 'Flash Flood', 'Flood', 'Heat Wave', 'Insect Infestation', 'Land Slide', 'Mud Slide',
                  'Other', 'Severe Local Storm', 'Snow Avalanche', 'Storm Surge', 'Technological Disaster',
                  'Tropical Cyclone', 'Tsunami', 'Volcano', 'Wild Fire']
refs = set()
base_url = 'https://api.reliefweb.int/v1/reports?appname=apidoc&query[fields][]=language&query[value]=English'

for disaster_type in disaster_types:
    url = base_url + f'&filter[field]=disaster_type&filter[value]=={disaster_type}&limit=100'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()["data"]
        refs.update([i['href'] for i in data])
        # process and store the report data as needed
    else:
        print(f"Failed to retrieve data for {disaster_type}")


def clean_text(text):
    # Define a string containing all special characters to remove
    special_chars = '@#$%^&*()_-+={}[]|\:;"<>/~`'
    # Create a translation table that removes all special characters
    translator = str.maketrans(special_chars, ' ' * len(special_chars))
    # Use the translation table to remove all special characters from the text
    text = text.translate(translator)

    # Remove all occurrences of '\n' and replace with whitespace
    text = text.replace('\n', ' ')
    # Convert bullet points to sentences
    text = re.sub(r'\n•', '. ', text)
    # Convert numbered lists to sentences
    text = re.sub(r'\n\d+\.?', '. ', text)
    # Remove two/more whitespace characters
    text = re.sub(r'\s{2,}', ' ', text)
    # Remove any extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Add a period at the end of the text if one is not already present
    if text[-1] != '.':
        text += '.'
    return text


contents = []
disasters = []

for ref in refs:
    data = requests.get(ref).json()
    try:
        content = clean_text(data['data'][0]['fields']['body'])
        disaster = data['data'][0]['fields']['disaster_type']
        contents.append(content)
        disasters.append([i['name'] for i in disaster])
    except KeyError:
        continue


df = pd.DataFrame({'content': contents, 'disaster_types': disasters})
train_set, test_set = train_test_split(df, test_size=0.25, random_state=42)
train_set.to_csv('training_set.csv', index=False)
test_set.to_csv('test_set.csv', index=False)
# print(df)