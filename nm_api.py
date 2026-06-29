import requests
import time
import random
from utils import clear_line


class APITimeoutException(Exception):
    pass


class APIException(Exception):
    pass


def rate_limited_get(url, timeout=10, attempts=3, backoff=5):
    '''
    Performs a rate-limited GET request with automatic retries on failure.

    Input: - url: URL to fetch (str)
           - timeout: request timeout in seconds (int)
           - attempts: number of attempts (int)
           - backoff: seconds to wait between attempts (int)

    Returns: response object
    '''

    for attempt in range(attempts):
        try:
            start = time.time()
            r = requests.get(url, timeout=timeout)
            if time.time() - start < 1/3:
                time.sleep(1/3 - (time.time() - start))  # Ensure we don't exceed 3 requests/sec

            if r.status_code == 200:
                return r
            else:
                raise APIException(f"Bad status {r.status_code}: {r.text}")

        except requests.exceptions.Timeout:
            print(f"Timeout on attempt {attempt + 1}/{attempts} for {url}")
            if attempt < attempts - 1:
                time.sleep(backoff)
            else:
                raise APITimeoutException(f"All {attempts} attempts timed out for: {url}")

        except requests.exceptions.RequestException as e:
            print(f"Request error on attempt {attempt + 1}/{attempts}: {e}")
            if attempt < attempts - 1:
                time.sleep(backoff)
            else:
                raise APIException(f"All {attempts} attempts failed for {url}: {e}")


def fetch_swc(neuron_data):
    '''
    Fetches the SWC file for a neuron given its metadata dict.

    Input: - neuron_data: dict containing metadata (dict)

    Returns: - swc_content: SWC file contents (bytes)
             - swc_name: name of the neuron (str)
    '''

    swc_url = f"https://neuromorpho.org/dableFiles/{neuron_data['archive'].lower()}/CNG%20version/{neuron_data['neuron_name']}.CNG.swc"
    r = rate_limited_get(swc_url)
    return r.content, neuron_data['neuron_name']


def fetch_neuron_by_id(neuron_id, output_dir=''):
    '''
    Fetches a single neuron by ID and writes it to a SWC file.

    Input: - neuron_id: id of neuron on neuromorpho.org (int)
           - output_dir (optional): directory to save the SWC file (str)

    Returns: - path: path to the created SWC file (str)
             - fetch_time: time taken to fetch (float)
             - write_time: time taken to write (float)
    '''

    start_fetch = time.time()
    r = rate_limited_get(f"https://neuromorpho.org/api/neuron/id/{neuron_id}")
    neuron_data = r.json()
    swc_content, swc_name = fetch_swc(neuron_data)
    fetch_time = time.time() - start_fetch

    path = f"{output_dir}/{swc_name}.swc" if output_dir else f"{swc_name}.swc"

    start_write = time.time()
    with open(path, "wb") as f:
        f.write(swc_content)
    write_time = time.time() - start_write

    return path, fetch_time, write_time


def fetch_neurons_by_page(page_num, size):
    '''
    Fetches all neurons on a given page from the NeuroMorpho repository.

    Input: - page_num: page number in the repository (int)
           - size: number of neurons per page (int)

    Returns: - swc_contents: {neuron_name: {"content": swc_content, "metadata": neuron_data}} (dict)
             - failed_fetches: {neuron_name: reason (str)} (dict)
    '''

    swc_contents = {}
    failed_fetches = {}

    r = rate_limited_get(f"https://neuromorpho.org/api/neuron?page={page_num}&size={size}")
    neurons = r.json()['_embedded']['neuronResources']

    for j, neuron in enumerate(neurons):
        clear_line(2)
        print(f"Fetching neuron {neuron['neuron_name']}... (Neuron {j + 1}/{len(neurons)})")

        try:
            swc_content, swc_name = fetch_swc(neuron)

            swc_contents[swc_name] = {
                "content": swc_content,
                "metadata": neuron
            }

        except APITimeoutException as e:
            print(f"Timeout fetching {neuron['neuron_name']}, skipping: {e}")
            failed_fetches[neuron['neuron_name']] = 'API timeout'

        except APIException as e:
            print(f"API error fetching {neuron['neuron_name']}, skipping: {e}")
            failed_fetches[neuron['neuron_name']] = 'API error'

    return swc_contents, failed_fetches


if __name__ == "__main__":
    id = random.randint(0, 286626 - 1)
    fetch_neuron_by_id(neuron_id=id)
