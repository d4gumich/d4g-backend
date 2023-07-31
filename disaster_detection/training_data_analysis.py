from itertools import combinations
import pandas as pd
import itertools
import seaborn as sns
import matplotlib.pyplot as plt
import ast

# load in training data
df = pd.read_csv('training_set.csv')

# Convert the 'disaster_types' values to lists
df['disaster_types'] = df['disaster_types'].apply(ast.literal_eval)

# observe sample of training data. Two columns, content (str) and disaster_types (list: [str]).
print(df.head())

# Explode the 'disaster types' column into separate rows for each disaster type
disaster_types = df.explode('disaster_types')

# Count the frequency of each disaster type, as well as the mean and median
disaster_type_counts = disaster_types['disaster_types'].value_counts()
mean_count = disaster_type_counts.mean()
median_count = disaster_type_counts.median()

# Create a bar chart of the disaster type counts
fig, ax = plt.subplots()
ax.bar(disaster_type_counts.index, disaster_type_counts.values)
# Add horizontal lines for the mean and median counts
ax.axhline(mean_count, color='r', linestyle='--', label=f'Mean: {mean_count:.2f}')
ax.axhline(median_count, color='k', linestyle='--', label=f'Median: {median_count:.2f}')

# Set the title and axis labels, and add a legend
ax.set_title(f"Disaster type count. Total number of reports: {len(df)}")
ax.set_xlabel('Disaster type')
ax.set_ylabel('Count')
ax.legend()
plt.xticks(rotation=45, ha='right')

# save the plot
ax.legend()
# plt.savefig('disaster_counts.png')
plt.clf()

# Get the frequency of how many disaster types each report includes
df['num_disaster_types'] = df['disaster_types'].apply(len)
num_disaster_type_counts = df['num_disaster_types'].value_counts()
num_disaster_type_counts

mean = num_disaster_type_counts.mean()
median = num_disaster_type_counts.median()

# Create plot
fig, ax = plt.subplots()
bar_container = num_disaster_type_counts.plot(kind='bar', ax=ax)
ax.axhline(mean, color='r', linestyle='--', label=f'Mean: {mean:.2f}')
ax.axhline(median, color='k', linestyle='--', label=f'Median: {median:.2f}')
ax.set_xlabel('Number of disaster types')
ax.set_ylabel('Frequency')
ax.set_title('Frequency of # of disaster types included by individual reports')
ax.legend()

for i in bar_container.patches:
    ax.text(i.get_x() + i.get_width() / 2, i.get_height(), i.get_height(), ha='center', va='bottom')

# plt.savefig('num_disaster_freqs.png')
plt.clf()

# Filter the dataframe to include only reports with disaster_type lists of size 7 and greater
df_large = df[df['num_disaster_types'] >= 7][['disaster_types']]
disaster_types_large = df_large.explode('disaster_types')
disaster_type_counts_large = disaster_types_large['disaster_types'].value_counts()

# Compute the percentage of the frequency of each disaster type in disaster_type_counts_large
disaster_type_pcnts_large = pd.Series()

for index, value in disaster_type_counts_large.iteritems():
    disaster_type_pcnts_large.at[index] = 100 * value / disaster_type_counts[index]

disaster_type_pcnts_large.sort_values(ascending=False, inplace=True)

# Create plot
fig, ax = plt.subplots()
ax.bar(disaster_type_pcnts_large.index, disaster_type_counts_large[disaster_type_pcnts_large.index], color='orange')

# Draw the bars for disaster_type_counts
ax.bar(disaster_type_pcnts_large.index, disaster_type_counts[disaster_type_pcnts_large.index], color='blue', alpha=0.4)

# Set the title and axis labels and text
ax.set_title("Percent Makeup of disaster types in reports with 7 or more disasters recognized")
ax.set_xlabel("Disaster Type")
ax.set_ylabel("Frequency")

for i, v in disaster_type_pcnts_large.items():
    ax.text(i, disaster_type_counts[i] + 1, f"{v:.2f}%", ha='center')

plt.xticks(rotation=90, ha='right')

# plt.savefig('percent_makeup_large.png')


# Get the count distribution for disaster types pairings

# Sort disaster_types lists first in alphabetical order to itertools.combinations will not have swapped combinations
# later. Like ('Flood', 'Virus') and ('Virus', 'Flood')
df['disaster_types'] = df['disaster_types'].apply(lambda x: sorted(x))

pair_counts = {}
for types in df['disaster_types']:
    if len(types) < 2:
        continue
    for pair in itertools.combinations(types, 2):
        if pair not in pair_counts:
            pair_counts[pair] = 1
        else:
            pair_counts[pair] += 1

# Convert the pair counts to a Pandas DataFrame

type1s = [i[0] for i in pair_counts.keys()]
type2s = [i[1] for i in pair_counts.keys()]
pair_count_df = pd.DataFrame({'disaster type 1': type1s,
                              'disaster type 2': type2s,
                              'value': pair_counts.values()})


# Create a pivot table to format the data for the heatmap
all_disaster_types = ['Cold Wave', 'Complex Emergency', 'Drought', 'Earthquake', 'Epidemic', 'Extratropical Cyclone',
                  'Fire', 'Flash Flood', 'Flood', 'Heat Wave', 'Insect Infestation', 'Land Slide', 'Mud Slide',
                  'Other', 'Severe Local Storm', 'Snow Avalanche', 'Storm Surge', 'Technological Disaster',
                  'Tropical Cyclone', 'Tsunami', 'Volcano', 'Wild Fire']

df_heatmap = pd.DataFrame(index=all_disaster_types, columns=all_disaster_types)
df_heatmap = df_heatmap.fillna(0)

for index, row in pair_count_df.iterrows():
    val = row['value']
    df_heatmap.loc[row['disaster type 1'], row['disaster type 2']] = val
    df_heatmap.loc[row['disaster type 2'], row['disaster type 1']] = val

# Create the heatmap
sns.heatmap(df_heatmap, annot=True, cmap='Blues')

# Set the title and axis labels
plt.title("Distribution of Pairs of Disaster Types Discussed")
plt.xlabel("Disaster Type 2")
plt.ylabel("Disaster Type 1")

# Save the plot
# plt.savefig('pair_distribution.png')
plt.clf()


sorted_pair_counts = pair_count_df.sort_values('value', ascending=False)
sorted_pair_counts.to_csv('pair_count_sorted.csv', index=False)
print('mean pair count: ', pair_count_df['value'].mean())
print('median pair count: ', pair_count_df['value'].median())