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

        except subprocess.CalledProcessError as e:
            # Handle errors in the command execution
            print(f"An error occurred while validating the file: {file_path}")
            print(f"Error: {e.stderr}")
        except FileNotFoundError:
            print("pynml is not installed or not found in the PATH.")


def validate_eden(file):
    eden_simulator.experimental.explain_cell(file)


# Example usage:
# directory = "NML_files_working"
# validate_neuroml_files(directory)

file = "NMLCL000813-NeuroML/cNAC187_L23_NGC_3c9a6fcd96_0_0.cell.nml"
validate_single_file(file)
