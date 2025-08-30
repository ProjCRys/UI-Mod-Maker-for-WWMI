import os
import shutil
import sys
from pathlib import Path

def generate_ini_content(folder_name, hash_value, num_frames, file_type):
    ini_content = f"""[Constants]
global $framevar = 0
global $active
global $fpsvar = 0
global $speedtoggle

[Present]
post $active = 0
if $active == 1 && $fpsvar < 60
    $fpsvar = $fpsvar + 24
    $speedtoggle = 0
endif
if $fpsvar >= 60
    $fpsvar = $fpsvar - 60
    $speedtoggle = 1
endif
if $framevar < {num_frames} && $speedtoggle == 1
    $framevar = $framevar + 1
else if $framevar == {num_frames}
    $framevar = 0
endif

[TextureOverrideFrame]
hash = {hash_value}
run = CommandlistFrame
$active = 1

[CommandlistFrame]"""

    # Build frame conditions
    frame_conditions = []
    for i in range(num_frames + 1):
        if i == 0:
            frame_conditions.append(f"""
if $framevar == 0
    this = ResourceFrame0""")
        else:
            frame_conditions.append(f"""
else if $framevar == {i}
    this = ResourceFrame{i}""")
    
    ini_content += ''.join(frame_conditions)
    ini_content += "\nendif\n\n"
    
    # Add resource frames
    resource_frames = []
    for i in range(num_frames + 1):
        resource_frames.append(f"""[ResourceFrame{i}]
filename = {hash_value} - {folder_name}/{i}.{file_type}""")
    
    ini_content += '\n'.join(resource_frames)
    return ini_content

def generate_package(input_folder, hash_value, output_folder):
    try:
        folder_name = os.path.basename(input_folder)
        dds_folder = os.path.join(input_folder, "dds")
        
        # Determine source folder and file type
        if os.path.exists(dds_folder):
            source_folder = dds_folder
            files = [f for f in os.listdir(source_folder) if f.lower().endswith('.dds')]
            file_type = "dds"
        else:
            source_folder = input_folder
            files = [f for f in os.listdir(source_folder) 
                    if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.dds'))]
            file_type = os.path.splitext(files[0])[1][1:] if files else None

        # Filter and sort frame files
        frame_files = [f for f in files if os.path.splitext(f)[0].isdigit()]
        frame_files.sort(key=lambda x: int(os.path.splitext(x)[0]))
        
        if not frame_files:
            raise Exception("No valid frame files found!")

        num_frames = len(frame_files) - 1
        
        # Generate INI content
        ini_content = generate_ini_content(folder_name, hash_value, num_frames, file_type)
        ini_filename = f"{folder_name}.ini"
        
        # Write INI file
        with open(ini_filename, 'w') as f:
            f.write(ini_content)
        
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)
        
        # Create subfolder named after the hash value
        hash_folder = os.path.join(output_folder, hash_value)
        os.makedirs(f"{hash_folder} - {folder_name}", exist_ok=True)
        
        # Copy frame files to the hash subfolder
        for file in frame_files:
            file_path = os.path.join(source_folder, file)
            shutil.copy(file_path, os.path.join(f"{hash_folder} - {folder_name}", file))
        
        # Copy INI file to the output folder
        shutil.copy(ini_filename, os.path.join(output_folder, ini_filename))
        
        # Cleanup
        os.remove(ini_filename)
        print(f"Package generated successfully: {output_folder}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

def main():
    if len(sys.argv) != 4:
        print("Usage: python ini_maker.py <hash_value> <input_folder> <output_folder>")
        print("Example: python ini_maker.py 1234abcd ./extracted_frames/character1 ./output_folder")
        sys.exit(1)
    
    hash_value = sys.argv[1]
    input_folder = sys.argv[2]
    output_folder = sys.argv[3]
    
    if not os.path.exists(input_folder):
        print(f"Error: Input folder '{input_folder}' does not exist")
        sys.exit(1)
        
    generate_package(input_folder, hash_value, output_folder)

if __name__ == "__main__":
    main()