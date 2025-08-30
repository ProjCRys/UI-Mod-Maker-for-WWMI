import os
import cv2
import glob
import multiprocessing
from PIL import Image

def extract_frames(segment_file, frame_output_folder, start_frame):
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
        
        # Save the frame in 32-bit integer linear light format
        frame_path = os.path.join(frame_output_folder, f'{frame_count}.png')
        pil_image.save(frame_path, 'PNG', bits=32)
        
        frame_count += 1
        extracted_frames += 1
    
    cap.release()
    return extracted_frames

def extract_frames_from_segments(segment_folder, frame_output_folder):
    """Extract frames from video segments in sequential order using multiprocessing"""
    os.makedirs(frame_output_folder, exist_ok=True)
    
    # Get segment files and sort them to ensure correct order
    segment_files = sorted(glob.glob(os.path.join(segment_folder, '*.mp4')))
    
    # Prepare arguments for parallel processing
    extraction_args = []
    current_frame = 0
    for segment_file in segment_files:
        extraction_args.append((segment_file, frame_output_folder, current_frame))
        # Update current_frame for next segment
        current_frame += int(cv2.VideoCapture(segment_file).get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Use multiprocessing Pool to process segments
    with multiprocessing.Pool() as pool:
        results = pool.starmap(extract_frames, extraction_args)
    
    return sum(results)