from neuromorpho_api import requestor as requests


def fetch_swc_file(neuron_id):
    endpoint = "https://neuromorpho.org/api/"
    response = requests.get(endpoint + f"neuron/id/{neuron_id}")

    if response.status_code != 200:
        raise("Failed to fetch SWC file:", response.text)

    data = response.json()

    # Construct the SWC URL
    swc_url = f"https://neuromorpho.org/dableFiles/{data['archive'].lower()}/CNG%20version/{data['neuron_name']}.CNG.swc"
    print(swc_url)
    # Fetch the SWC file without modifying its contents
    swc_response = requests.get(swc_url)
    
    if swc_response.status_code != 200:
        raise("Failed to fetch SWC file:", swc_response.text)

    return swc_response.content


def create_swc_file(neuron_id, swc_dir):
    swc_content = fetch_swc_file(neuron_id)
    if swc_content:
        with open(f"{swc_dir}/neuron_{neuron_id}.swc", "wb") as f:
            f.write(swc_content)
    return f"{swc_dir}/neuron_{neuron_id}.swc"


if __name__ == "__main__":
    neuron_id = 2
    create_swc_file(neuron_id, '')
