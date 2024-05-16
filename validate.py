import subprocess
import glob
import os

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
            
            # Print the output
            print(result.stdout)
            print(result.stderr)
            
            if result.returncode == 0:
                print(f"Validation succeeded for file: {file_path}")
            else:
                print(f"Validation failed for file: {file_path}")
        
        except subprocess.CalledProcessError as e:
            # Handle errors in the command execution
            print(f"An error occurred while validating the file: {file_path}")
            print(f"Error: {e.stderr}")
        except FileNotFoundError:
            print("pynml is not installed or not found in the PATH.")

# Example usage:
directory = "map_nml_files"
validate_neuroml_files(directory)
