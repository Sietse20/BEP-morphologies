from neuromorpho_api import requestor as requests
import time
import os


def clear_screen():
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix-based systems (Linux, macOS)
        os.system('clear')


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


def create_swc_files(page_range, size, output_dir=''):
    '''
    This function writes the SWC contents to a new SWC file in an optionally specified output directory.

    Input: - neuron_id: id of neuron on neuromorpho.org (int)
           - output_dir (optional):  directory in which the SWC file will be saved (str)

    Returns: name of the newly created neuroml file (str)
    '''

    swc_content = []
    swc_paths = []

    for i, page_num in enumerate(range(*page_range)):
        clear_screen()
        print(f"Fetching page {page_num}... (Page {i + 1}/{len(range(*page_range))})")
        data = fetch_metadata(page_num, size)

        for j, neuron in enumerate(data['_embedded']['neuronResources']):
            clear_screen()
            print(f"Fetching neuron {neuron['neuron_name']} (Page {i + 1}/{len(range(*page_range))}, neuron {j + 1}/{len(data['_embedded']['neuronResources'])})")
            swc_content, swc_name = fetch_swc(neuron)

            if swc_content:
                if output_dir:
                    with open(f"{output_dir}/{swc_name}.swc", "wb") as f:
                        f.write(swc_content)
                    swc_paths.append(f"{output_dir}/{swc_name}.swc")

                else:
                    with open(f"{swc_name}.swc", "wb") as f:
                        f.write(swc_content)
                    swc_paths.append(f"{swc_name}.swc")

    return swc_paths


if __name__ == "__main__":
    page_range = (1, 3)
    size = 20
    output_dir = 'swc_try'
    create_swc_files(page_range, size, output_dir=output_dir)
