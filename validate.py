import subprocess
import glob
import os
import eden_simulator
import time
import pprint


def validate_single_file(file_path):
    try:
        file_name = os.path.basename(file_path)

        # Construct the command and execute it
        command = ['pynml', '-validate', file_path]
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        # Validate files with eden
        validate_eden(file_path)

        # Print the output
        if result.returncode == 0:
            print(f"Validation succeeded for file: {file_name}")
        else:
            print(f"Validation failed for file: {file_name}")
            print(result.stdout)
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        # Handle errors in the command execution
        print(f"An error occurred while validating the file: {file_path}")
        print(f"Error: {e.stderr}")


def clear_screen():
    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix-based systems (Linux, macOS)
        os.system('clear')


def validate_directory(directory):
    # Find all .nml files in the specified directory
    file_pattern = os.path.join(directory, '*.nml')
    files = glob.glob(file_pattern)

    if not files:
        print("No .nml files found in the directory.")
        return

    unsuccessful_files = {}

    for i, file_path in enumerate(files):
        try:
            file_name = os.path.basename(file_path)
            clear_screen()
            print(f'Validating {file_name}... (File {i + 1}/{len(files)})')

            # Construct the command and execute it
            command = ['pynml', '-validate', file_path]
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            # Validate files with eden
            validate_eden(file_path)

            # Print the output
            if result.returncode == 0:
                print(f"Validation succeeded for file: {file_name}")
            else:
                unsuccessful_files[file_name] = {"stdout": result.stdout,
                                                 "stderr": result.stderr}
                print(f"Validation failed for file: {file_name}")
                time.sleep(2)

        except subprocess.CalledProcessError as e:
            unsuccessful_files[file_name] = {"error": e}
            print(f"An error occurred while validating the file: {file_name}")
            time.sleep(2)

    # Printing summary:
    clear_screen()
    print(f"Validation succeeded for {len(files) - len(unsuccessful_files)} files.")
    print(f"Validation failed for {len(unsuccessful_files)} files.")

    if unsuccessful_files:
        print("\nErrors per file:")
        pprint.pprint(unsuccessful_files)


def validate_eden(file):
    eden_simulator.experimental.explain_cell(file)


# Validate files in directory:
directory = "test_nml"

validate_directory(directory)


# Validate single file:
# file = "_10_6vkd1m_converted.cell.nml"

# validate_single_file(file)
