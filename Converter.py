import converter_utils
import nm_api
import validate_nml
from nm_api import APIException, APITimeoutException
from utils import clear_screen, clear_line

import json
import pprint
import numpy as np
import time
import pickle
import os
import traceback
import random


def make_summary():
    '''
    Returns a fresh summary dictionary.
    '''

    return {
        'Successful conversions': 0,
        'Unsuccessful conversions': {},
        'Errors': {}
    }


def print_summary(summary, unsuccessful_files, errors_per_file, print_errors):
    '''Prints the conversion summary, unsuccessful files, and per-file errors.'''

    print("\nSummary:")
    pprint.pprint(summary)

    if unsuccessful_files:
        print("\nErrors for unsuccessfully converted files:")
        for file, errors in unsuccessful_files.items():
            print(f"{file}: {json.dumps(errors, indent=2, separators=(',', ': '))}")

    if print_errors:
        print("\nErrors per file:")
        for file, errors in errors_per_file.items():
            print(f"{file}: {json.dumps(errors, indent=2, separators=(',', ': '))}")


def convert_single(input_data, summary, unsuccessful_files, errors_per_file, print_errors=False, validate=False, write_nml=True, output_dir=''):
    '''
    Converts a single SWC file to neuroml and updates the summary in place.

    Input: - input_data: filepath (str) or (neuron_name, swc_content) tuple
           - summary: summary dict to update in place
           - unsuccessful_files: dict to update in place
           - errors_per_file: dict to update in place
           - print_errors (optional): whether to store per-file errors (bool)
           - validate (optional): whether to validate the output file (bool)
           - write_nml (optional): whether to write the nml file to disk (bool)
           - output_dir (optional): directory to write the nml file to (str)

    Returns: None
    '''

    swc_file = input_data[0] if isinstance(input_data, tuple) else os.path.basename(input_data)
    errors = {}
    nml_file = None

    try:
        nml_file, nml_doc, errors = converter_utils.construct_nml(input_data, write_nml=write_nml, output_dir=output_dir)
        summary['Successful conversions'] += 1
    except converter_utils.ConversionException as e:
        errors = e.errors
        summary['Unsuccessful conversions']['Conversion exception'] = summary['Unsuccessful conversions'].get('Conversion exception', 0) + 1
        unsuccessful_files[swc_file] = errors
        print(f'Error converting {swc_file}: {e}')
    except Exception as e:
        summary['Unsuccessful conversions']['Internal error'] = summary['Unsuccessful conversions'].get('Internal error', 0) + 1
        unsuccessful_files[swc_file] = str(e)
        print(f'UNEXPECTED ERROR for {swc_file}: {type(e).__name__}: {e}')
        traceback.print_exc()

    if print_errors and errors:
        errors_per_file[swc_file] = errors

    for error in errors:
        summary['Errors'][error] = summary['Errors'].get(error, 0) + 1

    if validate and nml_file:
        validate_nml.validate_single_file(nml_file)


def convert_file(path, validate=True, output_dir=''):
    '''
    This function converts a single file to a neuroml file and saves it to an optionally specified output directory.
    It prints a conversion message and the error dictionary.
    '''

    swc_file = os.path.basename(path)

    try:
        nml_file, nml_doc, errors = converter_utils.construct_nml(path, write_nml=True, output_dir=output_dir)
        print(f'Converted {swc_file} to {nml_file}')
        if errors:
            print(json.dumps(errors, indent=2, separators=(',', ': ')))
        if validate:
            full_path = os.path.join(output_dir, nml_file)
            validate_nml.validate_single_file(full_path)
    except converter_utils.ConversionException as e:
        print(f'Error converting {swc_file}: {e}')
        print(json.dumps(e.errors, indent=2, separators=(',', ': ')))
    except Exception as e:
        print(f'Unexpected error converting {swc_file}: {e}')
        traceback.print_exc()


def convert_directory(path_swc, validate=True, print_errors=False, path_nml=''):
    '''
    This function converts all the SWC files in a given directory to neuroml files and saves them to an optionally specified output directory.
    It shows the progress of the conversion and prints the error dictionaries if indicated through print_errors.
    It prints a summary of the errors encountered and the amount of files (un)successfully converted.
    '''

    # Create dictionaries for summary of converted files
    summary = make_summary()
    errors_per_file = {}
    unsuccessful_files = {}

    # Iterating through all directories and subdirectories
    file_paths = []
    for root, dirs, files in os.walk(path_swc):
        for file in files:
            if file.endswith('.swc'):
                file_paths.append(os.path.join(root, file))

    for i, file_path in enumerate(file_paths):
        clear_screen()
        print(f'Converting {os.path.basename(file_path)}... (File {i + 1}/{len(file_paths)})')

        convert_single(file_path, summary, unsuccessful_files, errors_per_file, print_errors=print_errors, validate=validate, output_dir=path_nml)

    clear_screen()
    print_summary(summary, unsuccessful_files, errors_per_file, print_errors)


def convert_api_neuronid(range_api, validate=True, print_errors=False, output_dir_swc='', output_dir_nml=''):
    '''
    This function fetches the neurons given by range_api from the neuromorpho API and converts the fetched SWC files to neuroml files.
    It saves them to an optionally specified output directory.
    It shows the progress of the conversion and prints the error dictionaries if indicated through print_errors.
    It prints a summary of the errors encountered and the amount of files (un)successfully converted.
    '''

    # Create dictionaries for summary of converted files
    summary = make_summary()
    unsuccessful_files = {}
    errors_per_file = {}
    fetch_times = []
    conversion_times = []
    write_times = []

    neuron_ids = list(range(*range_api))

    for i, neuron_id in enumerate(neuron_ids):
        clear_screen()
        print(f'Fetching neuron {neuron_id}... (File {i + 1}/{len(neuron_ids)})')

        try:
            path, fetch_time, write_time = nm_api.fetch_neuron_by_id(neuron_id, output_dir=output_dir_swc)
            fetch_times.append(fetch_time)
            write_times.append(write_time)
        except APITimeoutException as e:
            summary['Unsuccessful conversions']['API timeout'] = summary['Unsuccessful conversions'].get('API timeout', 0) + 1
            print(f'Timeout fetching neuron {neuron_id}: {e}')
            time.sleep(5)
            continue
        except APIException as e:
            summary['Unsuccessful conversions']['API error'] = summary['Unsuccessful conversions'].get('API error', 0) + 1
            print(f'API error fetching neuron {neuron_id}: {e}')
            continue

        clear_screen()
        print(f'Converting {os.path.basename(path)}... (File {i + 1}/{len(neuron_ids)})')

        start = time.time()
        convert_single(path, summary, unsuccessful_files, errors_per_file, print_errors=print_errors, validate=validate, output_dir=output_dir_nml)
        conversion_times.append(time.time() - start)

    clear_screen()
    print('Conversion complete!')

    print(f"\nAverage fetching time: {np.mean(fetch_times)}")
    print(f"Average writing time: {np.mean(write_times)}")
    print(f"Average conversion time: {np.mean(conversion_times)}")
    print_summary(summary, unsuccessful_files, errors_per_file, print_errors)


def convert_api_bulk(page_range, size, validate=False, print_errors=False, write_nml=False, output_dir_nml=''):
    '''
    This function fetches the neurons in bulk given by page_range and size (amount of neurons per page) from the neuromorpho API and converts the fetched SWC files to neuroml files.
    It saves them to an optionally specified output directory.
    It shows the progress of the conversion and prints the error dictionaries if indicated through print_errors.
    It prints a summary of the errors encountered and the amount of files (un)successfully converted.
    '''

    # Create dictionaries for summary of converted files
    summary = make_summary()
    unsuccessful_files = {}
    errors_per_file = {}

    for i, page_num in enumerate(range(*page_range)):
        clear_screen()
        print(f"Fetching page {page_num}... (Page {i + 1}/{len(range(*page_range))})")

        try:
            swc_contents, failed_fetches = nm_api.fetch_neurons_by_page(page_num, size)
        except APITimeoutException as e:
            summary['Unsuccessful conversions']['API timeout'] = summary['Unsuccessful conversions'].get('API timeout', 0) + 1
            print(f'Timeout fetching page {page_num}: {e}')
            time.sleep(5)
            continue
        except APIException as e:
            summary['Unsuccessful conversions']['API error'] = summary['Unsuccessful conversions'].get('API error', 0) + 1
            print(f'API error fetching page {page_num}: {e}')
            continue

        for neuron_name, reason in failed_fetches.items():
            summary['Unsuccessful conversions'][reason] = summary['Unsuccessful conversions'].get(reason, 0) + 1
            unsuccessful_files[neuron_name] = reason

        clear_screen()
        print(f"Converting page {page_num}... (Page {i + 1}/{len(range(*page_range))})")

        for j, (swc_file, swc_content) in enumerate(swc_contents.items()):
            clear_line(2)
            print(f'Converting {swc_file}... (File {j + 1}/{len(swc_contents)})')

            convert_single((swc_file, swc_content), summary, unsuccessful_files, errors_per_file, print_errors=print_errors, validate=validate, write_nml=write_nml, output_dir=output_dir_nml)

    clear_screen()
    print('Conversion complete!')

    # Save summary to file
    start_page = page_range[0]
    end_page = page_range[1] - 1
    file_path = f"summaries/pages_{start_page}-{end_page}"
    with open(file_path, 'wb') as f:
        pickle.dump(summary, f)

    print_summary(summary, unsuccessful_files, errors_per_file, print_errors)


def convert_api_random(validate = True, output_dir_swc='', output_dir_nml=''):
    neuron_id = random.randint(0, 286626 - 1)

    print(f'Fetching neuron {neuron_id}...')
    try:
        path, fetch_time, write_time = nm_api.fetch_neuron_by_id(neuron_id, output_dir=output_dir_swc)
    except APITimeoutException as e:
        print(f'Timeout fetching neuron {neuron_id}: {e}')
    except APIException as e:
        print(f'API error fetching neuron {neuron_id}: {e}')

    print(f'Converting {os.path.basename(path)}...')
    start = time.time()
    convert_file(path, validate=validate, output_dir=output_dir_nml)
    conversion_time = time.time() - start
    print('Conversion complete!')

    print(f"\nFetching time: {fetch_time}")
    print(f"Writing time: {write_time}")
    print(f"Conversion time: {conversion_time}")


if __name__ == '__main__':
    # Converting single file:
    # path = "swc_api/0-2a.swc"
    # output_dir = ''

    # convert_file(path, validate=True, output_dir=output_dir)

    # Converting from a directory:
    # path_swc = "Padraig"
    # path_nml = 'Padraig_nml'
    # print_errors = True

    # convert_directory(path_swc, print_errors, path_nml=path_nml)


    # Converting from the API (neuron_id):
    # range_api = (700, 710)
    # output_dir_swc = 'swc_api'
    # output_dir_nml = 'nml_api'
    # print_errors = False
    # validate = False

    # convert_api_neuronid(range_api, validate=validate, print_errors=print_errors, output_dir_swc=output_dir_swc, output_dir_nml=output_dir_nml)


    # Converting from the API (bulk):
    # page_range = (2115, 2120)
    # size = 20
    # output_dir_nml = 'nml_api'
    # print_errors = False
    # validate = False
    # write_nml = False

    # convert_api_bulk(page_range, size, validate=validate, print_errors=print_errors, write_nml=write_nml, output_dir_nml=output_dir_nml)


    # Converting from the API (random):
    output_dir_swc = 'swc_random'
    output_dir_nml = 'nml_random'
    validate = False

    convert_api_random(validate=validate, output_dir_swc=output_dir_swc, output_dir_nml=output_dir_nml)
