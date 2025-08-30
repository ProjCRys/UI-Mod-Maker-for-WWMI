import os
import cv2
import numpy as np
import multiprocessing

def convert_video_fps(input_path, output_path, target_fps):
    """Convert video FPS while maintaining original speed"""
    cap = cv2.VideoCapture(input_path)
    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / original_fps
    
    target_total_frames = int(duration * target_fps)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(
        output_path,
        fourcc,
        target_fps,
        (int(cap.get(3)), int(cap.get(4)))
    )
    
    original_timestamps = np.linspace(0, duration, total_frames)
    target_timestamps = np.linspace(0, duration, target_total_frames)
    
    frame_buffer = None
    next_frame_idx = 0
    
    for target_time in target_timestamps:
        while (next_frame_idx < total_frames - 1 and 
               abs(original_timestamps[next_frame_idx + 1] - target_time) < 
               abs(original_timestamps[next_frame_idx] - target_time)):
            ret, frame_buffer = cap.read()
            next_frame_idx += 1
            
        if frame_buffer is None:
            ret, frame_buffer = cap.read()
            next_frame_idx += 1
            
        if frame_buffer is not None:
            out.write(frame_buffer)
    
    cap.release()
    out.release()
    return output_path

def process_video_fps(file_path, target_fps, temp_folder):
    os.makedirs(temp_folder, exist_ok=True)
    converted_video_path = os.path.join(temp_folder, "converted_fps.mp4")
    return convert_video_fps(file_path, converted_video_path, target_fps)