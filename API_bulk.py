from neuromorpho_api import requestor as requests
import time
import os
import sys


def clear_screen():
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix-based systems (Linux, macOS)
        os.system('clear')


def clear_line(line_number):
    # Move cursor to the beginning of the specified line and clear it
    sys.stdout.write(f"\033[{line_number};0H\033[K")
    sys.stdout.flush()


def fetch_metadata(page_num, size):
    '''
    This function fetches the information about the specified neuron id and fetches the corresponding SWC file using the generated url.

    Input: neuron_id: id of neuron on neuromorpho.org (int)

    Returns: - SWC file contents (bytes)
             - swc_name: name of swc file (str)
    '''

    endpoint = "https://neuromorpho.org/api/neuron"
    start = time.time()
    r = requests.get(f"{endpoint}?page={page_num}&size={size}")

    if r.status_code != 200:
        raise Exception("Failed to fetch SWC file:", r.text)

    data = r.json()

    if time.time() - start < 1/3:
        time.sleep(1/3 - (time.time() - start))

    return data


def fetch_swc(data):
    # Construct and fetch the SWC URL

    swc_url = f"https://neuromorpho.org/dableFiles/{data['archive'].lower()}/CNG%20version/{data['neuron_name']}.CNG.swc"
    swc_name = data['neuron_name']

    start = time.time()
    swc_response = requests.get(swc_url)
    if swc_response.status_code != 200:
        raise Exception("Failed to fetch SWC file:", swc_response.text)
    if time.time() - start < 1/3:
        time.sleep(1/3 - (time.time() - start))

    return swc_response.content, swc_name


def create_swc_files(page_num, size):
    '''
    This function writes the SWC contents to a new SWC file in an optionally specified output directory.

    Input: - neuron_id: id of neuron on neuromorpho.org (int)
           - output_dir (optional):  directory in which the SWC file will be saved (str)

    Returns: name of the newly created neuroml file (str)
    '''

    swc_contents = {}

    data = fetch_metadata(page_num, size)

    for j, neuron in enumerate(data['_embedded']['neuronResources']):
        clear_line(2)
        print(f"Fetching neuron {neuron['neuron_name']}... (Neuron {j + 1}/{len(data['_embedded']['neuronResources'])})")
        swc_content, swc_name = fetch_swc(neuron)
        
        if swc_content:
            swc_contents[swc_name] = swc_content

    return swc_contents


if __name__ == "__main__":
    page_num = 1
    size = 20
    create_swc_files(page_num, size)
