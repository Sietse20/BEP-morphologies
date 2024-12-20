import pickle
import os

d = {'Successful conversions': 0,
     'Unsuccessful conversions': 0,
     'Errors': {}}


# Step 1: Open the pickle file in binary read mode
for filename in os.listdir('summaries'):
    with open(f'summaries/{filename}', 'rb') as f:
        # Step 2: Load the dictionary from the file
        dictionary = pickle.load(f)
        d['Successful conversions'] += dictionary['Successful conversions']
        d['Unsuccessful conversions'] += dictionary['Unsuccessful conversions']
        for key, value in dictionary['Errors'].items():
            if key not in d['Errors']:
                d['Errors'][key] = value
            else:
                d['Errors'][key] += value

print(d)
