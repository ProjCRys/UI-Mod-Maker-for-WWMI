import os
from PIL import Image
from concurrent.futures import ProcessPoolExecutor
import argparse
import shutil

# Global variables
new_dimensions = None  # To store the new width and height after first image processing

def calculate_new_dimensions(img_width, img_height, scale_factor):
    """Calculate and return new width and height, scaled and adjusted to be divisible by 4."""
    new_width = int(img_width * scale_factor)
    new_height = int(img_height * scale_factor)

    # Ensure dimensions are divisible by 4
    new_width = new_width if new_width % 4 == 0 else new_width + (4 - new_width % 4)
    new_height = new_height if new_height % 4 == 0 else new_height + (4 - new_height % 4)

    return (new_width, new_height)

def scale_image(file_path, batch_folder, dimensions):
    """Function to scale a single image and save it, using predetermined dimensions."""
    try:
        # Open the original image
        with Image.open(file_path) as img:
            # Define output file path
            filename = os.path.basename(file_path)
            output_path = os.path.join(batch_folder, filename)

            # Check if the scaled image already exists and matches the target size
            if os.path.exists(output_path):
                with Image.open(output_path) as scaled_img:
                    if scaled_img.size == dimensions:
                        print(f'Skipping already scaled image: {filename}')
                        return  # Skip processing this image if already scaled

            # Scale and save the image
            scaled_img = img.resize(dimensions, Image.LANCZOS)
            scaled_img.save(output_path)
            print(f'Scaled and saved: {filename}')
    except Exception as e:
        print(f'Error processing {file_path}: {e}')

def move_images_to_output(input_folder, output_folder, images_per_batch):
    """Move images to output folder without processing, organized in batches."""
    os.makedirs(output_folder, exist_ok=True)
    image_files = [
        os.path.join(input_folder, filename)
        for filename in os.listdir(input_folder)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
    ]

    total_batches = (len(image_files) + images_per_batch - 1) // images_per_batch
    for batch_index in range(total_batches):
        batch_folder = os.path.join(output_folder, f"batch{batch_index + 1}")
        os.makedirs(batch_folder, exist_ok=True)

        start_index = batch_index * images_per_batch
        end_index = min(start_index + images_per_batch, len(image_files))
        current_batch_files = image_files[start_index:end_index]

        for file_path in current_batch_files:
            shutil.move(file_path, batch_folder)
            print(f'Moved {os.path.basename(file_path)} to {batch_folder}')
        
        print(f"Processed batch {batch_index + 1}/{total_batches} for non-scaling case.")

    print("All images moved to 'scaled-output' in batches without scaling!")

def scale_images_in_batches(input_folder, output_folder, scale_factor, images_per_batch):
    """Function to scale all images in the input folder and save to output folders in batches based on IMAGES_PER_BATCH."""
    os.makedirs(output_folder, exist_ok=True)
    image_files = [
        os.path.join(input_folder, filename)
        for filename in os.listdir(input_folder)
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
    ]

    # Determine new dimensions based on the first image
    global new_dimensions
    if image_files:
        with Image.open(image_files[0]) as img:
            new_dimensions = calculate_new_dimensions(img.width, img.height, scale_factor)

    # Process images in batches based on images_per_batch
    total_batches = (len(image_files) + images_per_batch - 1) // images_per_batch
    for batch_index in range(total_batches):
        batch_folder = os.path.join(output_folder, f"batch{batch_index + 1}")
        os.makedirs(batch_folder, exist_ok=True)

        start_index = batch_index * images_per_batch
        end_index = min(start_index + images_per_batch, len(image_files))
        current_batch_files = image_files[start_index:end_index]

        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(scale_image, file_path, batch_folder, new_dimensions): file_path for file_path in current_batch_files}
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    print(f'Error occurred while processing {futures[future]}: {e}')

        print(f"Processed batch {batch_index + 1}/{total_batches}")

    print("All batches processed!")

def main():
    parser = argparse.ArgumentParser(description='Scale images in a folder.')
    parser.add_argument('folderpath', type=str, help='Path to the folder containing images.')
    parser.add_argument('scale', type=float, help='Scale value (e.g., 0.25 for 25%).')
    parser.add_argument('images_per_batch', type=int, help='Number of images to process in each batch.')

    args = parser.parse_args()

    input_folder = args.folderpath
    scale_factor = args.scale
    images_per_batch = args.images_per_batch

    output_folder = os.path.join(input_folder, "scaled-output")
    
    if scale_factor == 1:
        print("Scale factor is 1 (100%), moving images without scaling.")
        move_images_to_output(input_folder, output_folder, images_per_batch)
    else:
        scale_images_in_batches(input_folder, output_folder, scale_factor, images_per_batch)
        print(f'All images have been scaled down and saved in batches in: {output_folder}')

if __name__ == "__main__":
    main()