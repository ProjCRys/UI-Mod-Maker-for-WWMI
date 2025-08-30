# api.py
import os
import re
import imageio
from typing import List, Tuple

def find_dds_hashes(folder_path: str) -> Tuple[List[str], List[str]]:
    """
    Scans a folder for DDS files with a specific hash pattern in their names,
    verifies they are viewable, and returns their hashes and file paths.

    Args:
        folder_path: The absolute or relative path to the folder to scan.

    Returns:
        A tuple containing two lists:
        - A list of the extracted hashes (strings).
        - A list of the corresponding full file paths (strings).
        Returns empty lists if the folder doesn't exist or no valid files are found.
    """
    if not os.path.isdir(folder_path):
        print(f"Error: Directory not found at '{folder_path}'")
        return [], []

    hashes = []
    dds_file_paths = []
    
    # Regex to capture the first hexadecimal hash in filenames like:
    # '...t0=a1b2c3d4(e5f6g7h8).dds'
    hash_pattern = re.compile(r't0=([a-f0-9]+)\([a-f0-9]+\)')

    print(f"Scanning folder: {folder_path}...")

    # Sort files for consistent ordering
    try:
        filenames = sorted(os.listdir(folder_path))
    except FileNotFoundError:
        print(f"Error: Directory not found at '{folder_path}'")
        return [], []

    for filename in filenames:
        if filename.endswith(".dds"):
            match = hash_pattern.search(filename)
            if match:
                file_path = os.path.join(folder_path, filename)
                
                # --- Verification Step ---
                # Try to read the image data to ensure it's a valid, viewable file.
                # If it causes an error, it's skipped and not included in the results.
                try:
                    imageio.imread(file_path)
                    
                    # If readable, extract hash and add to lists
                    extracted_hash = match.group(1)
                    hashes.append(extracted_hash)
                    dds_file_paths.append(file_path)

                except Exception as e:
                    print(f"Skipping un-viewable file {filename}: {e}")

    return hashes, dds_file_paths