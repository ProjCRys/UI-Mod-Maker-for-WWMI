import os
import subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import argparse

# Path to Texconv executable
TEXCONV_PATH = 'General_UI_Tool/texconv.exe'

def convert_batch_to_dds(batch_folder, output_folder, gpu_id):
    """Convert images from a specific batch folder to DDS format using the -srgbi option."""
    # Convert paths to Path objects
    batch_folder = Path(batch_folder)
    output_folder = Path(output_folder)

    # Create output directory if it doesn't exist
    output_folder.mkdir(parents=True, exist_ok=True)

    # List all files to convert
    input_files = list(batch_folder.glob('*'))  # Get all files in the batch folder

    # Build the command for the Texconv tool to process all compatible images in the batch folder
    command = [
        TEXCONV_PATH,
        '-f', 'BC7_UNORM',  # Specify the format as BC7_UNORM
        '-srgbi',           # Use the -srgbi option
        '-gpu', str(gpu_id),   # Use specified GPU
        '-bc', 'x',           # Maximum quality
        '-o', str(output_folder),    # Output folder
        str(batch_folder) + '/*'     # Input folder, all files in batch
    ]

    try:
        # Execute the command
        subprocess.run(command, check=True)
        print(f"Converted images in {batch_folder} successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion of {batch_folder}: {e}")

    # Return the number of input files and the number of converted files
    converted_files = list(output_folder.glob('*'))  # Get all converted files
    return len(input_files), len(converted_files)

def main():
    # Define input and output paths
    parser = argparse.ArgumentParser(description='Convert images to DDS format using Texconv with -srgbi option.')
    parser.add_argument('input_folder', type=str, help='Path to the base input folder containing batch folders.')
    parser.add_argument('output_folder', type=str, help='Path to the output folder for converted DDS files.')
    parser.add_argument('--gpu', type=int, default=0, help='ID of the GPU to use (default: 0)')
    args = parser.parse_args()

    base_input_folder = Path(args.input_folder)
    output_folder = Path(args.output_folder)

    # Identify all batch folders (e.g., batch1, batch2, ...)
    batch_folders = [str(folder) for folder in base_input_folder.iterdir() if folder.is_dir() and folder.name.startswith("batch")]

    total_files = 0
    total_converted = 0

    # Use ProcessPoolExecutor to run conversion on each batch folder in parallel
    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(convert_batch_to_dds, batch_folder, output_folder, args.gpu) for batch_folder in batch_folders]

        # Collect results as they complete
        for future in futures:
            try:
                files_to_convert, converted = future.result()  # This will block until the conversion is done
                total_files += files_to_convert
                total_converted += converted
            except Exception as e:
                print(f"Error occurred during processing: {e}")

    print(f"Total files: {total_files}, Total converted: {total_converted}")

if __name__ == '__main__':
    main()