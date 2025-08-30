import os
import cv2
import multiprocessing
import math

def process_segment(args):
    """Process a single video segment"""
    file_path, start_frame, segment_count, frames_per_segment, fps, padding_width = args
    # Format the segment filename with dynamic zero-padded numbering
    segment_file_path = os.path.join(
        os.path.dirname(file_path), 
        "video_segments", 
        f'segment_{segment_count:0{padding_width}}.mp4'
    )
    
    cap = cv2.VideoCapture(file_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    out = cv2.VideoWriter(
        segment_file_path,
        fourcc,
        fps,
        (width, height)
    )
    
    frames_written = 0
    while frames_written < frames_per_segment:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        frames_written += 1
    
    out.release()
    cap.release()
    return segment_count

def segment_video(file_path, segment_length, output_folder):
    """Segment the video into fixed-length segments"""
    os.makedirs(output_folder, exist_ok=True)
    
    cap = cv2.VideoCapture(file_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames_per_segment = int(segment_length * fps)
    total_segments = (total_frames + frames_per_segment - 1) // frames_per_segment
    
    # Determine the padding width based on the total number of segments
    padding_width = math.ceil(math.log10(total_segments)) if total_segments > 1 else 1
    
    # Create segment information for parallel processing
    segment_infos = [
        (file_path, i * frames_per_segment, i, frames_per_segment, fps, padding_width)
        for i in range(total_segments)
    ]
    
    # Use multiprocessing Pool
    with multiprocessing.Pool() as pool:
        results = pool.map(process_segment, segment_infos)
    
    cap.release()
    return len(results)
