from neuromorpho_api import requestor as requests
import time


def fetch_swc_file(neuron_id):
    '''
    This function fetches the information about the specified neuron id and fetches the corresponding SWC file using the generated url.

    Input: neuron_id: id of neuron on neuromorpho.org (int)

    Returns: - SWC file contents (bytes)
             - swc_name: name of swc file (str)
    '''

    endpoint = "https://neuromorpho.org/api/"
    start = time.time()
    response = requests.get(endpoint + f"neuron/id/{neuron_id}")

    if response.status_code != 200:
        raise ("Failed to fetch SWC file:", response.text)

    data = response.json()

    # Construct and fetch the SWC URL
    swc_url = f"https://neuromorpho.org/dableFiles/{data['archive'].lower()}/CNG%20version/{data['neuron_name']}.CNG.swc"
    swc_name = data['neuron_name']

    if time.time() - start < 1/3:
        time.sleep(1/3 - (time.time() - start))

    start2 = time.time()
    swc_response = requests.get(swc_url)

    if swc_response.status_code != 200:
        raise ("Failed to fetch SWC file:", swc_response.text)

    if time.time() - start2 < 1/3:
        time.sleep(1/3 - (time.time() - start2))

    return swc_response.content, swc_name


def create_swc_file(neuron_id, output_dir=''):
    '''
    This function writes the SWC contents to a new SWC file in an optionally specified output directory.

    Input: - neuron_id: id of neuron on neuromorpho.org (int)
           - output_dir (optional):  directory in which the SWC file will be saved (str)

    Returns: name of the newly created neuroml file (str)
    '''
    start_fetch = time.time()
    swc_content, swc_name = fetch_swc_file(neuron_id)
    fetch_time = time.time() - start_fetch

    start_write = time.time()
    if swc_content:
        if output_dir:
            with open(f"{output_dir}/{swc_name}.swc", "wb") as f:
                f.write(swc_content)
            write_time = time.time() - start_write
            return f"{output_dir}/{swc_name}.swc", fetch_time, write_time

        else:
            with open(f"{swc_name}.swc", "wb") as f:
                f.write(swc_content)
            write_time = time.time() - start_write
            return f"{swc_name}.swc", fetch_time, write_time


if __name__ == "__main__":
    neuron_id = 2
    output_dir = ''
    create_swc_file(neuron_id, output_dir=output_dir)
