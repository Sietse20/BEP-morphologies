import pickle
import os

d = {'Successful conversions': 0,
     'Unsuccessful conversions': {'API error': 0, 'Internal error': 0},
     'Errors': {}}


# Step 1: Open the pickle file in binary read mode
for filename in os.listdir('new_summaries'):
    with open(f'new_summaries/{filename}', 'rb') as f:
        # Step 2: Load the dictionary from the file
        dictionary = pickle.load(f)
        d['Successful conversions'] += dictionary['Successful conversions']
        for error_type, count in dictionary['Unsuccessful conversions'].items():
            d['Unsuccessful conversions'][error_type] += count
        for key, value in dictionary['Errors'].items():
            if key not in d['Errors']:
                d['Errors'][key] = value
            else:
                d['Errors'][key] += value

print(d)
