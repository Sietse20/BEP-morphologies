import Converter_utils
import API_bulk
import API_neuronid
import Validate_nml

import json
import pprint
import numpy as np
import time
import sys
import pickle
import os


def convert_file(path, validate=True, output_dir=''):
    '''
    This function converts a single file to a neuroml file and saves it to an optionally specified output directory.
    It prints a conversion message and the error dictionary.
    '''

    swc_file = os.path.basename(path)

    try:
        nml_file, errors = Converter_utils.construct_nml(path, output_dir=output_dir)
        print(f'Converted {swc_file} to the following file: {nml_file}')
        if errors:
            print(json.dumps(errors, indent=2, separators=(',', ': ')))
        if validate:
            Validate_nml.validate_single_file(nml_file)
    except Converter_utils.ConversionException as e:
        print(f'Error converting {swc_file}: {e}')
        print(json.dumps(e.errors, indent=2, separators=(',', ': ')))
    except Exception as e:
        print(f'Error converting {swc_file}: {e}')


def clear_screen():
    '''
    This function is used to clear the terminal screen.
    '''

    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix-based systems (Linux, macOS)
        os.system('clear')


def convert_directory(path_swc, validate=True, print_errors=False, path_nml=''):
    '''
    This function converts all the SWC files in a given directory to neuroml files and saves them to an optionally specified output directory.
    It shows the progress of the conversion and prints the error dictionaries if indicated through print_errors.
    It prints a summary of the errors encountered and the amount of files (un)successfully converted.
    '''

    # Create dictionaries for summary of converted files
    summary = {}
    summary['Successful conversions'] = 0
    summary['Unsuccessful conversions'] = 0
    summary['Errors'] = {}
    errors_per_file = {}
    unsuccessful_files = {}
    errors = {}

    # Iterating through all directories and subdirectories
    file_paths = []
    for root, dirs, files in os.walk(path_swc):
        for file in files:
            if file.endswith('.swc'):
                file_paths.append(os.path.join(root, file))

    for i, file_path in enumerate(file_paths):
        swc_file = os.path.basename(file_path)
        clear_screen()
        print(f'Converting {swc_file}... (File {i + 1}/{len(file_paths)})')

        try:
            nml_file, errors = Converter_utils.construct_nml(file_path, output_dir=path_nml)
            summary['Successful conversions'] += 1
        except Converter_utils.ConversionException as e:
            errors = e.errors
            summary['Unsuccessful conversions']['Conversion exception'] += 1
            unsuccessful_files[swc_file] = errors
            print(f'Error converting {swc_file}: {e}\n')
            time.sleep(2)
        except Exception as e:
            errors = e
            summary['Unsuccessful conversions']['Other exception'] += 1
            unsuccessful_files[swc_file] = e
            print(f'Error converting {swc_file}: {e}')
            time.sleep(2)

        if print_errors:
            errors_per_file[swc_file] = errors

        for error in errors:
            if error not in summary['Errors']:
                summary['Errors'][error] = 1
            else:
                summary['Errors'][error] += 1

        if validate:
            validate_nml.validate_single_file(nml_file)

    clear_screen()
    print('Conversion complete!')
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


def convert_api_neuronid(range_api, validate=True, print_errors=False, output_dir_swc='', output_dir_nml=''):
    '''
    This function fetches the neurons given by range_api from the neuromorpho API and converts the fetched SWC files to neuroml files.
    It saves them to an optionally specified output directory.
    It shows the progress of the conversion and prints the error dictionaries if indicated through print_errors.
    It prints a summary of the errors encountered and the amount of files (un)successfully converted.
    '''

    # Create dictionaries for summary of converted files
    summary = {}
    summary['Successful conversions'] = 0
    summary['Unsuccessful conversions'] = 0
    summary['Errors'] = {}
    unsuccessful_files = {}
    errors_per_file = {}
    fetch_time = []
    conversion_time = []

    for i, neuron_id in enumerate(range(*range_api)):
        try:
            clear_screen()
            print(f'Fetching neuron {neuron_id}... (File {i + 1}/{len(range(*range_api))})')

            path, fetch_time, write_time = API_neuronid.create_swc_file(neuron_id, output_dir=output_dir_swc)

            swc_file = os.path.basename(path)
            clear_screen()
            print(f'Converting {swc_file}... (File {i + 1}/{len(range(*range_api))})')

            try:
                start_conversion = time.time()
                nml_file, errors = Converter_utils.construct_nml(path, output_dir=output_dir_nml)
                conversion_time.append(time.time() - start_conversion)
                summary['Successful conversions'] += 1
            except Converter_utils.ConversionException as e:
                errors = e.errors
                summary['Unsuccessful conversions'] += 1
                unsuccessful_files[swc_file] = errors
                print(f'Error converting {swc_file}: {e}\n')
                time.sleep(2)
            except Exception as e:
                print(f'Error converting {swc_file}: {e}\n')
                time.sleep(2)

            if print_errors and errors:
                errors_per_file[swc_file] = errors

            for error in errors:
                if error not in summary['Errors']:
                    summary['Errors'][error] = 1
                else:
                    summary['Errors'][error] += 1

            if validate:
                validate_nml.validate_single_file(nml_file)

        except Exception:
            if 'Unsuccessful fetch' not in summary:
                summary['Unsuccessful fetch'] = 1
            else:
                summary['Unsuccessful fetch'] += 1
            print(f"Unsuccessful fetch for neuron {neuron_id}")
            time.sleep(2)

    clear_screen()
    print('Conversion complete!')
    print("\nSummary:")
    pprint.pprint(summary)

    print(f"\nAverage fetching time: {np.mean(fetch_time)}")
    print(f"Average writing time: {np.mean(write_time)}")
    print(f"Average conversion time: {np.mean(conversion_time)}")

    if unsuccessful_files:
        print("\nErrors for unsuccessfully converted files:")
        for file, errors in unsuccessful_files.items():
            print(f"{file}: {json.dumps(errors, indent=2, separators=(',', ': '))}")

    if print_errors:
        print("\nErrors per file:")
        for file, errors in errors_per_file.items():
            print(f"{file}: {json.dumps(errors, indent=2, separators=(',', ': '))}")


def clear_line(line_number):
    '''
    This function clears the line given by the line number.
    '''

    sys.stdout.write(f"\033[{line_number};0H\033[K")
    sys.stdout.flush()


def convert_api_bulk(page_range, size, validate=True, print_errors=False, output_dir_nml=''):
    '''
    This function fetches the neurons in bulk given by page_range and size (amount of neurons per page) from the neuromorpho API and converts the fetched SWC files to neuroml files.
    It saves them to an optionally specified output directory.
    It shows the progress of the conversion and prints the error dictionaries if indicated through print_errors.
    It prints a summary of the errors encountered and the amount of files (un)successfully converted.
    '''

    # Create dictionaries for summary of converted files
    summary = {}
    summary['Successful conversions'] = 0
    summary['Unsuccessful conversions'] = 0
    summary['Errors'] = {}
    unsuccessful_files = {}
    errors_per_file = {}

    for i, page_num in enumerate(range(*page_range)):
        clear_screen()
        print(f"Fetching page {page_num}... (Page {i + 1}/{len(range(*page_range))})")

        swc_contents = API_bulk.create_swc_files(page_num, size)

        clear_screen()
        print(f"Converting page {page_num}... (Page {i + 1}/{len(range(*page_range))})")
        for i, (swc_file, swc_content) in enumerate(swc_contents.items()):
            clear_line(2)
            print(f'Converting {swc_file}... (File {i + 1}/{len(swc_contents)})')

            try:
                nml_file, errors = Converter_utils.construct_nml((swc_file, swc_content), output_dir=output_dir_nml)
                summary['Successful conversions'] += 1
            except Converter_utils.ConversionException as e:
                errors = e.errors
                summary['Unsuccessful conversions']['Conversion exception'] += 1
                unsuccessful_files[swc_file] = errors
                print(f'Error converting {swc_file}: {e}\n')
                time.sleep(2)
            except Exception as e:
                errors = e
                summary['Unsuccessful conversions']['Other exception'] += 1
                unsuccessful_files[swc_file] = e
                print(f'Error converting {swc_file}: {e}\n')
                time.sleep(2)

            if print_errors and errors:
                errors_per_file[swc_file] = errors

            for error in errors:
                if error not in summary['Errors']:
                    summary['Errors'][error] = 1
                else:
                    summary['Errors'][error] += 1

            if validate:
                validate_nml.validate_single_file(nml_file)

    clear_screen()
    print('Conversion complete!')

    # Save summary to file
    start_page = page_range[0]
    end_page = page_range[1] - 1
    file_path = f"summaries/pages_{start_page}-{end_page}"
    with open(file_path, 'wb') as f:
        pickle.dump(summary, f)

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


if __name__ == '__main__':
    # Converting single file:
    path = "swc_api/0-2a.swc"
    output_dir = ''

    convert_file(path, validate=True, output_dir=output_dir)

    # Converting from a directory:
    # path_swc = "Padraig"
    # path_nml = 'Padraig_nml'
    # print_errors = True

    # convert_directory(path_swc, print_errors, path_nml=path_nml)


    # Converting from the API (neuron_id):
    # range_api = (700, 800)
    # output_dir_swc = 'swc_api'
    # output_dir_nml = 'nml_api'
    # print_errors = False

    # convert_api_neuronid(range_api, output_dir_swc, output_dir_nml, print_errors)


    # Converting from the API (bulk):
    # page_range = (0, 1)
    # size = 50
    # output_dir_nml = '
    # print_errors = False

    # convert_api_bulk(page_range, size, print_errors, output_dir_nml=output_dir_nml)
