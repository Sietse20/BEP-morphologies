import subprocess
import glob
import os
import eden_simulator


def validate_single_file(file_path):
    try:
        # Construct the command for each file
        command = ['pynml', '-validate', file_path]

        # Execute the command
        result = subprocess.run(command, capture_output=True, text=True, check=True)

        validate_eden(file_path)

        # Print the output
        if result.returncode == 0:
            print(f"Validation succeeded for file: {os.path.basename(file_path)}")
        else:
            print(f"Validation failed for file: {os.path.basename(file_path)}")
            print(result.stdout)
            print(result.stderr)

    except subprocess.CalledProcessError as e:
        # Handle errors in the command execution
        print(f"An error occurred while validating the file: {file_path}")
        print(f"Error: {e.stderr}")
    except FileNotFoundError:
        print("pynml is not installed or not found in the PATH.")


def validate_neuroml_files(directory):
    # Find all .cell.nml files in the specified directory
    file_pattern = os.path.join(directory, '*.cell.nml')
    files = glob.glob(file_pattern)

    if not files:
        print("No .cell.nml files found in the directory.")
        return
    
    total_files = len(files)
    total_errors = 0

    for file_path in files:
        try:
            # Construct the command for each file
            command = ['pynml', '-validate', file_path]

            # Execute the command
            result = subprocess.run(command, capture_output=True, text=True, check=True)

            validate_eden(file_path)

            # Print the output
            if result.returncode == 0:
                print(f"Validation succeeded for file: {os.path.basename(file_path)}")
            else:
                print(f"Validation failed for file: {os.path.basename(file_path)}")
                print(result.stdout)
                print(result.stderr)
                total_errors += 1

        except subprocess.CalledProcessError as e:
            # Handle errors in the command execution
            print(f"An error occurred while validating the file: {file_path}")
            print(f"Error: {e.stderr}")
            total_errors += 1
        except FileNotFoundError:
            print("pynml is not installed or not found in the PATH.")
    
    return total_files, total_errors


def validate_eden(file):
    eden_simulator.experimental.explain_cell(file)


# Validate files in directory:

# directory = "nml_api"
# total_files, total_errors = validate_neuroml_files(directory)
# print(f'\nFrom {total_files} total files: \nValidation successful for {total_files - total_errors} files. \nValidation unsuccessful for {total_errors} files.')

# Validate single file:

file = "nml_api\_10_6vkd1m_converted.cell.nml"
validate_single_file(file)
