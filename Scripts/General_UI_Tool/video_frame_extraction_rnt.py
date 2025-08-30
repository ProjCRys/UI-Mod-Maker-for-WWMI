import os
import cv2
import glob
import multiprocessing
from PIL import Image, ImageDraw

def extract_frames(segment_file, frame_output_folder, start_frame, corner_roundness=0, transparency=100):
    """Extract frames from a single video segment and save them in 32-bit integer linear light format"""
    cap = cv2.VideoCapture(segment_file)
    frame_count = start_frame
    extracted_frames = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Convert the frame from BGR to RGB (OpenCV uses BGR by default)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Convert the frame to a PIL Image
        pil_image = Image.fromarray(frame_rgb)
        
        # Apply corner roundness
        if corner_roundness > 0:
            rounded_image = round_corners(pil_image, corner_roundness)
        else:
            rounded_image = pil_image
        
        # Apply transparency
        if transparency < 100:
            alpha = int(transparency * 2.55)  # Convert percentage to alpha value (0-255)
            rounded_image = rounded_image.convert("RGBA")
            data = rounded_image.getdata()
            new_data = []
            for item in data:
                new_data.append((item[0], item[1], item[2], alpha))
            rounded_image.putdata(new_data)
        
        # Save the frame in 32-bit integer linear light format
        frame_path = os.path.join(frame_output_folder, f'{frame_count}.png')
        rounded_image.save(frame_path, 'PNG', bits=32)
        
        frame_count += 1
        extracted_frames += 1
    
    cap.release()
    return extracted_frames

def round_corners(image, percent=0):
    """Rounds the corners of the image by the given percentage"""
    if percent == 0:
        return image
    
    width, height = image.size
    radius = int((percent / 100) * min(width, height) / 2)
    
    # Create a mask with rounded corners
    mask = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), (width, height)], radius, fill=255)
    
    # Apply the mask to the image
    result = Image.new("RGBA", (width, height))
    result.paste(image, mask=mask)
    
    return result

def extract_frames_from_segments(segment_folder, frame_output_folder, corner_roundness=0, transparency=100):
    """Extract frames from video segments in sequential order using multiprocessing"""
    os.makedirs(frame_output_folder, exist_ok=True)
    
    # Get segment files and sort them to ensure correct order
    segment_files = sorted(glob.glob(os.path.join(segment_folder, '*.mp4')))
    
    # Prepare arguments for parallel processing
    extraction_args = []
    current_frame = 0
    for segment_file in segment_files:
        extraction_args.append((segment_file, frame_output_folder, current_frame, corner_roundness, transparency))
        # Update current_frame for next segment
        current_frame += int(cv2.VideoCapture(segment_file).get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Use multiprocessing Pool to process segments
    with multiprocessing.Pool() as pool:
        results = pool.starmap(extract_frames, extraction_args)
    
    return sum(results)