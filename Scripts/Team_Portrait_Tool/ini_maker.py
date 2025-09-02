import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QSlider, QGridLayout, QSizePolicy, QFrame, QCompleter, QDialog, QDialogButtonBox, QCheckBox, QScrollArea)
from PyQt5.QtCore import Qt, QTimer, QEvent, QRect, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QIcon

from PIL import Image, ImageSequence, ImageCms

# For video processing, ensure OpenCV and NumPy are installed.
import cv2
import numpy as np

CONFIG_FILE = "config.json"
TEMPLATE_OPACITY = 255
CUSTOM_STATIC_OPACITY = 255
TEXCONV_PATH = 'General_UI_Tool/texconv.exe'

# All helper functions (load_character_hashes, load_config, save_config, etc.) remain unchanged.
def load_character_hashes(file_path):
    hashes = {}
    try:
        with open(file_path, "r") as file:
            for i, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    name, hash_value = line.split(" --> ")
                    hashes[name.strip()] = hash_value.strip()
                except ValueError:
                    print(f"Warning: Skipping malformed line {i} in '{file_path}': '{line}'")
                    continue
    except FileNotFoundError:
        print(f"Error: Character hashes file not found at '{file_path}'")
    except Exception as e:
        print(f"An unexpected error occurred while loading character hashes: {e}")
    return hashes

CHARACTER_HASHES = load_character_hashes("UI_Hashes.txt")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                return config.get("last_folder_path", "")
        except Exception as e:
            print(f"Error loading config: {e}")
    return ""

def save_config(folder_path):
    config = {"last_folder_path": folder_path}
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file)
    except Exception as e:
        print(f"Error saving config: {e}")

def is_video_file(filepath):
    video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    ext = os.path.splitext(filepath)[1].lower()
    return ext in video_exts

def get_frame_count(filepath):
    try:
        if is_video_file(filepath):
            cap = cv2.VideoCapture(filepath)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            return frame_count if frame_count > 0 else 1
        else:
            with Image.open(filepath) as img:
                if getattr(img, "is_animated", False):
                    return sum(1 for _ in ImageSequence.Iterator(img))
                else:
                    return 1
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

def save_frames_to_folder(filepath, folder_path, template_width, template_height):
    try:
        if is_video_file(filepath):
            cap = cv2.VideoCapture(filepath)
            frame_index = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                pil_frame = Image.fromarray(frame_rgba)
                pil_frame = pil_frame.resize((template_width, template_height), Image.LANCZOS)
                pil_frame = pil_frame.convert("RGBA")
                pil_frame.save(os.path.join(folder_path, f"{frame_index}.png"))
                frame_index += 1
            cap.release()
        else:
            with Image.open(filepath) as img:
                frames = ImageSequence.Iterator(img)
                for i, frame in enumerate(frames):
                    frame_image = frame.convert('RGBA')
                    frame_image = frame_image.resize((template_width, template_height), Image.LANCZOS)
                    if 'icc_profile' in frame_image.info:
                        icc_profile = frame_image.info['icc_profile']
                        srgb_profile = ImageCms.createProfile('sRGB')
                        transform = ImageCms.buildTransformFromOpenProfiles(icc_profile, srgb_profile, 'RGBA', 'RGBA', intent=ImageCms.INTENT_PERCEPTUAL)
                        frame_image = ImageCms.applyTransform(frame_image, transform)
                    frame_image.save(os.path.join(folder_path, f"{i}.png"))
    except Exception as e:
        print(f"Error saving frames to folder: {e}")

def generate_frame_conditions(frame_count, item_index=0):
    conditions = []
    for i in range(1, frame_count):
        conditions.append(f"else if $framevar_{item_index} == {i}")
        conditions.append(f"    this = ResourceFrame_{item_index}_{i}")
    return "\n".join(conditions)

def generate_resource_frames(char_name, hash_value, frame_count, item_index=0, is_multi=False):
    frames = []
    item_folder = f"/Item{item_index+1}" if is_multi else ""
    for i in range(frame_count):
        frames.append(f"[ResourceFrame_{item_index}_{i}]")
        frames.append(f"filename = {hash_value} - {char_name}{item_folder}/{i}.dds")
    return "\n".join(frames)

def generate_ini_file(items_data, is_multi_portrait=False):
    if not items_data:
        return None
    if not is_multi_portrait:
        item = items_data[0]
        char_name, hash_value, frame_count = item['char_name'], item['hash_value'], item['frame_count']
        static_toggle_enabled = item['static_toggle_enabled']
        static_frame_index = item['static_frame_index']
        custom_static_image_path = item['custom_static_image_path']
        resource_frames_str = generate_resource_frames(char_name, hash_value, frame_count)
        if not static_toggle_enabled or frame_count <= 1:
            template = f"""[Constants]
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
if $framevar < {frame_count - 1} && $speedtoggle == 1
    $framevar = $framevar + 1
else if $framevar == {frame_count - 1}
    $framevar = 0
endif
[TextureOverrideFrame]
hash = {hash_value}
run = CommandlistFrame
$active = 1
[CommandlistFrame]
if $framevar == 0
    this = ResourceFrame_0_0
{generate_frame_conditions(frame_count).replace('$framevar_0', '$framevar').replace('ResourceFrame_0_', 'ResourceFrame')}
endif
{resource_frames_str.replace('ResourceFrame_0_', 'ResourceFrame')}
"""
        else:
            static_resource_section = ""
            command_list_static_line = ""
            if custom_static_image_path:
                command_list_static_line = "    this = ResourceStaticThumbnail"
                static_resource_section = f"""
[ResourceStaticThumbnail]
filename = {hash_value} - {char_name}/static_thumbnail.dds"""
            else:
                command_list_static_line = f"    this = ResourceFrame_0_{static_frame_index}"
            template = f"""[Constants]
global $framevar = 0
global $active
global $fpsvar = 0
global $speedtoggle
global $is_paused = 0
global $show_static = 0
[KeyPause]
key = p
type = cycle
$is_paused = 0, 1
condition = $active == 1
[KeyStatic]
key = o
type = cycle
$show_static = 0, 1
condition = $active == 1
[Present]
post $active = 0
if $is_paused == 0 && $show_static == 0
    if $active == 1 && $fpsvar < 60
        $fpsvar = $fpsvar + 24
        $speedtoggle = 0
    endif
    if $fpsvar >= 60
        $fpsvar = $fpsvar - 60
        $speedtoggle = 1
    endif
    if $framevar < {frame_count - 1} && $speedtoggle == 1
        $framevar = $framevar + 1
    else if $framevar == {frame_count - 1}
        $framevar = 0
    endif
endif
[TextureOverrideFrame]
hash = {hash_value}
run = CommandlistFrame
$active = 1
[CommandlistFrame]
if $show_static == 1
{command_list_static_line}
else if $framevar == 0
    this = ResourceFrame_0_0
{generate_frame_conditions(frame_count).replace('$framevar_0', '$framevar')}
endif
{resource_frames_str}{static_resource_section}
"""
    else:
        num_items = len(items_data)
        valid_indices = list(range(num_items))
        constants = ["[Constants]", f"global $portrait_idx = {valid_indices[0]}"]
        constants.extend(["global $is_paused = 0", "global $show_static = 0"])
        for i in range(num_items):
            constants.extend([f"global $framevar_{i} = 0", f"global $active_{i}", f"global $fpsvar_{i} = 0", f"global $speedtoggle_{i}"])
        key_bindings = ["[KeySwitchRight]", "key = right", "type = cycle", f"$portrait_idx = {','.join(map(str, valid_indices))}", "\n[KeySwitchLeft]", "key = left", "type = cycle", f"$portrait_idx = {','.join(map(str, reversed(valid_indices)))}", "\n[KeyPause]", "key = p", "type = cycle", "$is_paused = 0, 1", "\n[KeyStatic]", "key = o", "type = cycle", "$show_static = 0, 1"]
        present_section = ["[Present]"]
        for i, item in enumerate(items_data):
            present_section.append(f"post $active_{i} = 0")
            if item['frame_count'] > 1:
                present_section.append(f"if $is_paused == 0 && $show_static == 0")
                present_section.append(f"    if $active_{i} == 1 && $fpsvar_{i} < 60\n        $fpsvar_{i} = $fpsvar_{i} + 24\n        $speedtoggle_{i} = 0\n    endif")
                present_section.append(f"    if $fpsvar_{i} >= 60\n        $fpsvar_{i} = $fpsvar_{i} - 60\n        $speedtoggle_{i} = 1\n    endif")
                present_section.append(f"    if $framevar_{i} < {item['frame_count'] - 1} && $speedtoggle_{i} == 1\n        $framevar_{i} = $framevar_{i} + 1\n    else if $framevar_{i} == {item['frame_count'] - 1}\n        $framevar_{i} = 0\n    endif")
                present_section.append("endif")
        main_hash = items_data[0]['hash_value']
        texture_override = ["[TextureOverrideFrame]", f"hash = {main_hash}", "run = CommandlistFrame"]
        command_list = ["[CommandlistFrame]"]
        for i, item in enumerate(items_data):
            if_statement = "if" if i == 0 else "else if"
            command_list.append(f"{if_statement} $portrait_idx == {i}")
            command_list.append(f"    $active_{i} = 1")
            command_list.append(f"    if $show_static == 1")
            if item['custom_static_image_path']:
                command_list.append(f"        this = ResourceStaticThumbnail_{i}")
            else:
                static_frame_index = item['static_frame_index'] if item['static_toggle_enabled'] else 0
                command_list.append(f"        this = ResourceFrame_{i}_{static_frame_index}")
            command_list.append(f"    else")
            command_list.append(f"        if $framevar_{i} == 0")
            command_list.append(f"            this = ResourceFrame_{i}_0")
            if item['frame_count'] > 1:
                conditions = generate_frame_conditions(item['frame_count'], item_index=i)
                indented_conditions = "\n".join([f"        {line}" for line in conditions.splitlines()])
                command_list.append(indented_conditions)
            command_list.append(f"        endif")
            command_list.append(f"    endif")
        command_list.append("endif")
        all_resource_frames = []
        for i, item in enumerate(items_data):
            main_char_name = items_data[0]['char_name']
            resources_for_item = [generate_resource_frames(main_char_name, main_hash, item['frame_count'], item_index=i, is_multi=True)]
            if item['custom_static_image_path']:
                item_folder = f"/Item{i+1}"
                resources_for_item.append(f"[ResourceStaticThumbnail_{i}]")
                resources_for_item.append(f"filename = {main_hash} - {main_char_name}{item_folder}/static_thumbnail.dds")
            all_resource_frames.append("\n".join(resources_for_item))
        template = "\n".join(constants) + "\n" + "\n".join(key_bindings) + "\n\n" + "\n".join(present_section) + "\n\n" + "\n".join(texture_override) + "\n\n" + "\n".join(command_list) + "\n\n" + "\n\n".join(all_resource_frames)
    try:
        filename = f"{items_data[0]['char_name']}.ini"
        with open(filename, "w") as file:
            file.write(template)
        return filename
    except Exception as e:
        print(f"Error generating INI file: {e}")
        return None

def find_character_images(character_name):
    media_path = Path("media")
    if not media_path.exists() or not media_path.is_dir():
        return []
    matches = []
    media_exts = ['.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.svg', '.webp', '.raw', '.heif', '.ico', '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    for f in media_path.rglob('*'):
        if f.is_file() and character_name.lower() in f.stem.lower() and f.suffix.lower() in media_exts:
            matches.append(str(f))
    return matches

class ImagePickerDialog(QDialog):
    # This class remains unchanged.
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Character Image")
        self.setMinimumSize(600, 400)
        self.layout = QVBoxLayout(self)
        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(120, 120))
        self.list_widget.setSpacing(10)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.setWordWrap(True)
        self.list_widget.itemDoubleClicked.connect(self.accept)
        self.video_items = {}
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_video_frames)
        for path in image_paths:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.UserRole, path)
            item.setTextAlignment(Qt.AlignCenter)
            pixmap = QPixmap()
            if is_video_file(path):
                try:
                    cap = cv2.VideoCapture(path)
                    ret, frame = cap.read()
                    if ret:
                        pixmap = self.cv_frame_to_pixmap(frame, self.list_widget.iconSize())
                        self.video_items[item] = {'cap': cap}
                    else:
                        cap.release()
                except Exception as e:
                    print(f"Could not open video file {path}: {e}")
            else:
                pixmap = QPixmap(path)
            if not pixmap.isNull():
                item.setIcon(QIcon(pixmap.scaled(self.list_widget.iconSize(), Qt.KeepAspectRatio, Qt.SmoothTransformation)))
            self.list_widget.addItem(item)
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        self.layout.addWidget(self.list_widget)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)
        self.selected_file_path = None
        if self.video_items:
            self.timer.start(66)
    def cv_frame_to_pixmap(self, frame, size):
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(q_img)
            return pixmap.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            print(f"Error converting frame to pixmap: {e}")
            return QPixmap()
    def update_video_frames(self):
        for item, data in self.video_items.items():
            cap = data.get('cap')
            if not cap:
                continue
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = cap.read()
            if ret:
                pixmap = self.cv_frame_to_pixmap(frame, self.list_widget.iconSize())
                if not pixmap.isNull():
                    item.setData(Qt.DecorationRole, QIcon(pixmap))
    def cleanup(self):
        self.timer.stop()
        for data in self.video_items.values():
            if data.get('cap'):
                data['cap'].release()
        self.video_items.clear()
    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_file_path = current_item.data(Qt.UserRole)
        self.cleanup()
        super().accept()
    def reject(self):
        self.cleanup()
        super().reject()
    def get_selected_path(self):
        return self.selected_file_path

class ConversionThread(QThread):
    finished = pyqtSignal()
    def __init__(self, items_data, is_multi_portrait):
        super().__init__()
        self.items_data = items_data
        self.is_multi_portrait = is_multi_portrait
    def run(self):
        if not self.items_data:
            self.finished.emit()
            return
        try:
            first_item = self.items_data[0]
            main_char_name = first_item['char_name']
            main_hash_value = first_item['hash_value']
            ini_file = generate_ini_file(self.items_data, self.is_multi_portrait)
            if not ini_file:
                raise Exception("INI file generation failed.")
            default_folder_name = main_char_name
            folder_path = QFileDialog.getExistingDirectory(None, "Save Folder", default_folder_name)
            if folder_path:
                final_char_folder = Path(folder_path) / main_char_name
                final_char_folder.mkdir(exist_ok=True)
                dds_container_name = f"{main_hash_value} - {main_char_name}"
                dds_container_path = final_char_folder / dds_container_name
                if dds_container_path.exists():
                    shutil.rmtree(dds_container_path)
                dds_container_path.mkdir()
                for i, item_data in enumerate(self.items_data):
                    temp_folder_path = Path(f"temp_frames_{main_char_name or 'item'}_{i}")
                    temp_folder_path.mkdir(exist_ok=True)
                    save_frames_to_folder(item_data['filepath'], str(temp_folder_path), item_data['template_width'], item_data['template_height'])
                    item_subfolder_name = f"Item{i+1}" if self.is_multi_portrait else ""
                    dds_output_folder = dds_container_path / item_subfolder_name
                    dds_output_folder.mkdir(exist_ok=True)
                    convert_pngs_to_dds(str(temp_folder_path), str(dds_output_folder))
                    if item_data['custom_static_image_path']:
                        convert_single_image_to_dds(
                            item_data['custom_static_image_path'],
                            str(dds_output_folder),
                            'static_thumbnail.dds',
                            (item_data['template_width'], item_data['template_height'])
                        )
                    if temp_folder_path.exists():
                        shutil.rmtree(temp_folder_path)
                shutil.move(ini_file, final_char_folder / ini_file)
                instructions_path = final_char_folder / "instructions.txt"
                with open(instructions_path, "w") as f:
                    if self.is_multi_portrait:
                        f.write("Instructions for Switching Portraits:\n")
                        f.write("- Press 'left' arrow key to cycle through portraits backwards.\n")
                        f.write("- Press 'right' arrow key to cycle through portraits forwards.\n\n")
                        f.write("The following keys affect the currently visible portrait:\n")
                        f.write("- Press 'p' to pause/play the animation.\n")
                        f.write("- Press 'o' to switch between the animation and its designated thumbnail frame.\n")
                    elif any(item['static_toggle_enabled'] for item in self.items_data):
                        f.write("Instructions for Thumbnail/Animation Toggle:\n")
                        f.write("- Press 'p' to pause/play the animation.\n")
                        f.write("- Press 'o' to switch between the animation and the thumbnail image.\n")
                
                save_config(folder_path)
        except Exception as e:
            print(f"Error in conversion thread: {e}")
        finally:
            self.finished.emit()

def convert_single_image_to_dds(image_path, output_folder, output_filename, resize_dim):
    try:
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as img:
            resized_img = img.resize(resize_dim, Image.LANCZOS).convert("RGBA")
        temp_dir = Path("./temp_single_conversion")
        temp_dir.mkdir(exist_ok=True)
        temp_png_path = temp_dir / "temp_image.png"
        resized_img.save(temp_png_path)
        command = [
            TEXCONV_PATH,
            '-f', 'BC7_UNORM',
            '-srgbi',
            '-o', str(output_folder),
            str(temp_png_path)
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        converted_dds_path = output_folder / "temp_image.dds"
        final_dds_path = output_folder / output_filename
        if converted_dds_path.exists():
            os.rename(converted_dds_path, final_dds_path)
        shutil.rmtree(temp_dir)
    except FileNotFoundError:
        print(f"Error: Texconv executable not found at '{TEXCONV_PATH}'")
    except subprocess.CalledProcessError as e:
        print(f"Error during DDS conversion of {image_path}: {e.stderr}")
    except Exception as e:
        print(f"An error occurred in convert_single_image_to_dds: {e}")

def convert_pngs_to_dds(input_folder, output_folder, gpu_id=1):
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    input_files = [str(p) for p in input_folder.glob('*.png')]
    if not input_files:
        return
    command = [
        TEXCONV_PATH,
        '-f', 'BC7_UNORM',
        '-srgbi',
        '-bc', 'x',
        '-gpu', str(gpu_id),
        '-o', str(output_folder),
    ] + input_files
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"Error: Texconv executable not found at '{TEXCONV_PATH}'")
    except subprocess.CalledProcessError as e:
        print(f"Error during DDS conversion of {input_folder}: {e.stderr}")

class ItemWidget(QFrame):
    delete_requested = pyqtSignal(QWidget)
    def __init__(self, is_deletable=False, is_main_item=False, parent=None):
        super().__init__(parent)
        self.is_main_item = is_main_item
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,10) 
        self.layout.setSpacing(12)

        if is_deletable:
            top_bar_layout = QHBoxLayout()
            top_bar_layout.addStretch()
            delete_button = QPushButton("X")
            delete_button.setObjectName("RemoveButton")
            delete_button.setToolTip("Delete this item")
            delete_button.clicked.connect(lambda: self.delete_requested.emit(self))
            top_bar_layout.addWidget(delete_button)
            self.layout.addLayout(top_bar_layout)
        else:
            self.layout.addSpacing(10)

        try:
            self.template_img_base = Image.open("templates/team_portrait.png").convert("RGBA")
            self.template_width, self.template_height = self.template_img_base.size
        except Exception as e:
            self.template_img_base = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
            self.template_width, self.template_height = 256, 256
        self.template_img = self.template_img_base.copy()
        
        self.timer = QTimer(self)
        self.current_frame_index = 0
        self.source_frames = []
        self.source_image = None
        self.filepath = None
        self.frame_count = 0
        self.custom_static_image_path = None
        self.custom_static_pil_image = None
        self.current_theme = None 
        
        if self.is_main_item:
            self.char_name_label = QLabel("Character Name:")
            self.char_name_entry = QLineEdit(self)
            self.hash_label = QLabel("Hash Value:")
            self.hash_entry = QLineEdit(self)
            self.suggestion_list = QListWidget(self)
            info_layout = QGridLayout()
            info_layout.setSpacing(10)
            info_layout.addWidget(self.char_name_label, 0, 0)
            info_layout.addWidget(self.char_name_entry, 0, 1)
            info_layout.addWidget(self.hash_label, 1, 0)
            info_layout.addWidget(self.hash_entry, 1, 1)
            info_layout.setColumnStretch(1, 1)
            self.layout.addLayout(info_layout)
        else:
            self.suggestion_list = QListWidget(self)

        self.preview_frame = QFrame(self)
        self.preview_label = QLabel()
        settings_frame = QFrame(self)
        settings_frame.setObjectName("SettingsFrame")
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(10, 5, 10, 10)
        self.opacity_label = QLabel("Template Opacity:")
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.toggle_options_frame = QFrame(self)
        self.static_toggle_button = QCheckBox("Set Thumbnail Frame", self)
        self.static_frame_label = QLabel("Thumbnail Frame: 0")
        self.static_frame_slider = QSlider(Qt.Horizontal, self)
        self.select_custom_image_button = QPushButton("Select Custom Thumbnail Image")
        self.custom_image_label = QLabel("No custom thumbnail selected.")
        self.remove_custom_image_button = QPushButton("[ X ]", self) 
        self.remove_custom_image_button.setObjectName("RemoveButton") 
        self.custom_opacity_label = QLabel("Custom Image Opacity:")
        self.custom_opacity_slider = QSlider(Qt.Horizontal, self)
        
        self.configure_preview_frame()
        preview_wrapper = QWidget()
        preview_layout = QHBoxLayout(preview_wrapper)
        preview_layout.setContentsMargins(0, 10, 0, 10)
        preview_layout.addWidget(self.preview_frame, alignment=Qt.AlignCenter)
        self.layout.addWidget(preview_wrapper)
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        settings_layout.addLayout(opacity_layout)
        
        self.configure_toggle_options_frame()
        settings_layout.addWidget(self.toggle_options_frame)
        self.toggle_options_frame.hide()

        self.configure_elements()
        self.connect_signals()
        self.update_suggestion_theme()
        self.update_template_opacity(TEMPLATE_OPACITY, initial_load=True)

        self.layout.addWidget(settings_frame)

    def get_data(self):
        if not self.filepath:
            self.frame_count = 0
        elif self.frame_count == 0:
            self.frame_count = get_frame_count(self.filepath)
        return {
            'char_name': self.char_name_entry.text() if self.is_main_item else "",
            'hash_value': self.hash_entry.text() if self.is_main_item else "",
            'filepath': self.filepath,
            'frame_count': self.frame_count,
            'template_width': self.template_width,
            'template_height': self.template_height,
            'static_toggle_enabled': self.static_toggle_button.isChecked() and self.toggle_options_frame.isVisible() and self.frame_count > 1,
            'static_frame_index': self.static_frame_slider.value(),
            'custom_static_image_path': self.custom_static_image_path
        }
    
    def configure_preview_frame(self):
        self.preview_frame.setObjectName("PreviewFrameOuter")
        self.preview_frame.setFixedSize(self.template_width + 40, self.template_height + 40)
        self.preview_frame.setCursor(Qt.PointingHandCursor)
        outer_layout = QVBoxLayout(self.preview_frame)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        inner_frame = QFrame(self.preview_frame)
        inner_frame.setObjectName("PreviewFrameInner")
        outer_layout.addWidget(inner_frame)
        inner_layout = QVBoxLayout(inner_frame)
        inner_layout.setContentsMargins(10, 10, 10, 10)
        self.preview_label.setObjectName("PreviewContentLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(self.template_width, self.template_height)
        inner_layout.addWidget(self.preview_label)

    def configure_toggle_options_frame(self):
        toggle_layout = QVBoxLayout(self.toggle_options_frame)
        toggle_layout.setContentsMargins(0, 5, 0, 5)
        toggle_layout.setSpacing(8)
        toggle_layout.addWidget(self.static_toggle_button)
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(self.static_frame_label)
        slider_layout.addWidget(self.static_frame_slider)
        toggle_layout.addLayout(slider_layout)
        toggle_layout.addWidget(self.select_custom_image_button)
        custom_image_info_layout = QHBoxLayout()
        custom_image_info_layout.addWidget(self.custom_image_label, 1)
        custom_image_info_layout.addWidget(self.remove_custom_image_button)
        toggle_layout.addLayout(custom_image_info_layout)
        custom_opacity_layout = QHBoxLayout()
        custom_opacity_layout.addWidget(self.custom_opacity_label)
        custom_opacity_layout.addWidget(self.custom_opacity_slider)
        toggle_layout.addLayout(custom_opacity_layout)
        self.custom_image_label.setWordWrap(True)
        self.custom_opacity_label.hide()
        self.custom_opacity_slider.hide()
        self.remove_custom_image_button.hide()
        self.select_custom_image_button.hide()
        self.custom_image_label.hide()
        self.static_frame_label.hide()
        self.static_frame_slider.hide()

    def configure_elements(self):
        if self.is_main_item:
            self.char_name_entry.installEventFilter(self)
        self.suggestion_list.setFixedWidth(200)
        self.suggestion_list.setMinimumHeight(20)
        self.suggestion_list.setMaximumHeight(100)
        self.suggestion_list.hide()
        self.suggestion_list.installEventFilter(self)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(TEMPLATE_OPACITY)
        self.custom_opacity_slider.setRange(0, 255)
        self.custom_opacity_slider.setValue(CUSTOM_STATIC_OPACITY)

    def connect_signals(self):
        self.timer.timeout.connect(self.update_frame)
        if self.is_main_item:
            self.char_name_entry.textChanged.connect(self.update_suggestions)
            self.suggestion_list.itemClicked.connect(self.select_suggestion)
        self.suggestion_list.verticalScrollBar().valueChanged.connect(self.update_suggestion_theme)
        self.preview_frame.mousePressEvent = self.open_file
        self.opacity_slider.valueChanged.connect(self.update_template_opacity)
        self.static_toggle_button.toggled.connect(self.on_toggle_changed)
        self.static_frame_slider.valueChanged.connect(self.update_static_frame_preview)
        self.select_custom_image_button.clicked.connect(self.select_custom_static_image)
        self.remove_custom_image_button.clicked.connect(self.remove_custom_static_image)
        self.custom_opacity_slider.valueChanged.connect(self.update_custom_static_opacity)

    def _composite_all_layers(self, base_image):
        if not isinstance(base_image, Image.Image):
            base_image = Image.new("RGBA", (self.template_width, self.template_height), (0, 0, 0, 0))
        final_image = base_image.copy()
        if self.custom_static_pil_image and self.static_toggle_button.isChecked():
            img_data = np.array(self.custom_static_pil_image)
            if img_data.shape[2] == 4:
                alpha_channel = img_data[:, :, 3]
                new_alpha = (alpha_channel * (CUSTOM_STATIC_OPACITY / 255.0)).astype(np.uint8)
                img_data[:, :, 3] = new_alpha
                custom_img_with_opacity = Image.fromarray(img_data)
                final_image = Image.alpha_composite(final_image, custom_img_with_opacity)
        final_image = Image.alpha_composite(final_image, self.template_img)
        return final_image

    def _update_preview(self):
        base_image = None
        if self.static_toggle_button.isChecked() and self.source_frames:
            value = self.static_frame_slider.value()
            if 0 <= value < len(self.source_frames):
                base_image = self.source_frames[value]
        elif self.source_frames:
            base_image = self.source_frames[self.current_frame_index]
        elif self.source_image:
            base_image = self.source_image
        composite_image = self._composite_all_layers(base_image)
        self.preview_label.setPixmap(QPixmap.fromImage(self.pil_to_qimage(composite_image)))

    def remove_custom_static_image(self):
        self.custom_static_image_path = None
        self.custom_static_pil_image = None
        self.custom_image_label.setText("No custom thumbnail selected.")
        self.remove_custom_image_button.hide()
        self.custom_opacity_label.hide()
        self.custom_opacity_slider.hide()
        if self.static_toggle_button.isChecked():
            self.static_frame_slider.setEnabled(True)
            self.static_frame_label.setEnabled(True)
        self._update_preview()

    def select_custom_static_image(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Custom Thumbnail Image", "", "Image Files (*.png *.jpg *.bmp *.gif)")
        if filepath:
            self.custom_static_image_path = filepath
            self.custom_image_label.setText(f"Custom: {os.path.basename(filepath)}")
            with Image.open(filepath) as img:
                self.custom_static_pil_image = img.resize((self.template_width, self.template_height), Image.LANCZOS).convert("RGBA")
            self.static_frame_slider.setEnabled(False)
            self.static_frame_label.setEnabled(False)
            self.custom_opacity_label.show()
            self.custom_opacity_slider.show()
            self.remove_custom_image_button.show()
            self._update_preview()

    def on_toggle_changed(self, checked):
        is_custom_img = self.custom_static_image_path is not None
        self.static_frame_slider.setVisible(checked)
        self.static_frame_label.setVisible(checked)
        self.select_custom_image_button.setVisible(checked)
        self.custom_image_label.setVisible(checked)
        self.remove_custom_image_button.setVisible(checked and is_custom_img)
        self.custom_opacity_label.setVisible(checked and is_custom_img)
        self.custom_opacity_slider.setVisible(checked and is_custom_img)
        self.static_frame_slider.setEnabled(checked and not is_custom_img)
        self.static_frame_label.setEnabled(checked and not is_custom_img)
        if checked:
            self.timer.stop()
            self._update_preview()
        elif self.source_frames:
            self.timer.start()
        else:
            self._update_preview()

    def update_static_frame_preview(self, value):
        self.static_frame_label.setText(f"Thumbnail Frame: {value}")
        self._update_preview()
    def update_suggestion_theme(self):
        new_theme = "dark"
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
                new_theme = settings.get("theme", "dark").lower() if "theme" in settings else ("dark" if settings.get("dark_mode", False) else "light")
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        if new_theme == self.current_theme: return
        self.current_theme = new_theme
        stylesheet = """
            QListWidget {{ background-color: {bg}; border: 1px solid {border}; padding: 2px; color: {fg}; }}
            QListWidget::item {{ padding: 4px; border-radius: 2px; }}
            QListWidget::item:hover {{ background-color: {hover_bg}; }}
            QListWidget::item:selected {{ background-color: {select_bg}; color: {select_fg}; }}
        """.format(
            bg="#ffffff" if new_theme == "light" else "#3c3c3c", border="#c0c0c0" if new_theme == "light" else "#555",
            fg="#000000" if new_theme == "light" else "#e0e0e0", hover_bg="#e6e6e6" if new_theme == "light" else "#4a4a4a",
            select_bg="#0078d7" if new_theme == "light" else "#008080", select_fg="#ffffff"
        )
        self.suggestion_list.setStyleSheet(stylesheet)
    def eventFilter(self, obj, event):
        if self.is_main_item and obj == self.char_name_entry:
            if event.type() == QEvent.FocusIn:
                self.update_suggestion_theme()
                self.update_suggestions()
                if self.suggestion_list.count() > 0:
                    self.suggestion_list.show()
                    self.update_suggestion_list_position()
            elif event.type() == QEvent.FocusOut:
                QTimer.singleShot(150, self.suggestion_list.hide)
        if obj == self.suggestion_list and event.type() == QEvent.Enter:
            self.update_suggestion_theme()
        return super().eventFilter(obj, event)
    def update_suggestion_list_position(self):
        main_parent = self.parent() 
        entry_pos = self.char_name_entry.mapTo(main_parent, self.char_name_entry.rect().bottomLeft())
        self.suggestion_list.move(entry_pos)
        self.suggestion_list.setFixedWidth(self.char_name_entry.width())
    def pil_to_qimage(self, pil_image):
        try:
            return QImage(pil_image.tobytes("raw", "RGBA"), pil_image.width, pil_image.height, QImage.Format_RGBA8888)
        except Exception as e:
            print(f"Error converting PIL image to QImage: {e}")
            return QImage()
    def load_media_file(self, filepath):
        try:
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                return
            self.filepath = filepath
            self.frame_count = get_frame_count(filepath)
            is_animated = self.frame_count > 1
            self.remove_custom_static_image()
            if is_animated:
                self.static_toggle_button.setChecked(False) 
                self.static_frame_slider.setRange(0, self.frame_count - 1)
                self.static_frame_slider.setValue(0)
                self.toggle_options_frame.show()
                if is_video_file(filepath): self.show_video(filepath)
                else: self.show_gif(filepath)
            else:
                self.toggle_options_frame.hide()
                self.show_image(filepath)
            self.on_toggle_changed(self.static_toggle_button.isChecked())
        except Exception as e:
            print(f"Error loading media file {filepath}: {e}")
    def open_file(self, event):
        try:
            last_folder = load_config()
            initial_dir = last_folder if last_folder and os.path.exists(last_folder) else os.path.join(os.getcwd(), "media")
            if not os.path.exists(initial_dir): initial_dir = os.getcwd()
            filepath, _ = QFileDialog.getOpenFileName(self, "Open Image, GIF, or Video", initial_dir, "Media Files (*.gif *.png *.jpg *.bmp *.tiff *.svg *.webp *.raw *.heif *.ico *.mp4 *.avi *.mov *.mkv *.flv *.wmv)")
            if filepath:
                self.load_media_file(filepath)
                save_config(os.path.dirname(filepath))
        except Exception as e:
            print(f"Error opening file: {e}")
    def show_gif(self, filepath):
        try:
            self.timer.stop()
            with Image.open(filepath) as gif_image:
                self.source_frames = [frame.copy().convert("RGBA").resize((self.template_width, self.template_height), Image.LANCZOS) for frame in ImageSequence.Iterator(gif_image)]
            self.source_image = None
            if self.source_frames:
                self.current_frame_index = 0
                self.timer.start(100)
        except Exception as e:
            print(f"Error displaying GIF: {e}")
    def show_image(self, filepath):
        try:
            self.timer.stop()
            with Image.open(filepath) as image:
                self.source_image = image.resize((self.template_width, self.template_height), Image.LANCZOS).convert("RGBA")
            self.source_frames = []
            self._update_preview()
        except Exception as e:
            print(f"Error displaying image: {e}")
    def show_video(self, filepath):
        try:
            self.timer.stop()
            cap = cv2.VideoCapture(filepath)
            fps = cap.get(cv2.CAP_PROP_FPS)
            interval = int(1000 / fps) if fps > 0 else 100
            self.source_frames = []
            while True:
                ret, frame = cap.read()
                if not ret: break
                frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                self.source_frames.append(Image.fromarray(frame_rgba).resize((self.template_width, self.template_height), Image.LANCZOS))
            cap.release()
            self.source_image = None
            if self.source_frames:
                self.current_frame_index = 0
                self.timer.start(interval)
        except Exception as e:
            print(f"Error displaying video: {e}")
    def update_frame(self):
        if self.source_frames:
            self.current_frame_index = (self.current_frame_index + 1) % len(self.source_frames)
            self._update_preview()
    def update_custom_static_opacity(self, opacity):
        global CUSTOM_STATIC_OPACITY
        if opacity == CUSTOM_STATIC_OPACITY: return
        CUSTOM_STATIC_OPACITY = opacity
        self._update_preview()
    def update_template_opacity(self, opacity, initial_load=False):
        global TEMPLATE_OPACITY
        if not initial_load and opacity == TEMPLATE_OPACITY: return
        TEMPLATE_OPACITY = opacity
        try:
            base_template = self.template_img_base
            if opacity == 255:
                self.template_img = base_template
            else:
                img_data = np.array(base_template)
                if img_data.shape[2] == 4:
                    alpha_channel = img_data[:, :, 3]
                    new_alpha = (alpha_channel * (opacity / 255.0)).astype(np.uint8)
                    img_data[:, :, 3] = new_alpha
                    self.template_img = Image.fromarray(img_data)
            self._update_preview()
        except Exception as e:
            print(f"Error updating template opacity: {e}")
    def update_suggestions(self):
        if not self.is_main_item: return
        try:
            input_text = self.char_name_entry.text()
            self.suggestion_list.clear()
            if not input_text:
                self.suggestion_list.hide()
                return
            suggestions = sorted([name for name in CHARACTER_HASHES.keys() if name.lower().startswith(input_text.lower())])
            if suggestions:
                self.suggestion_list.addItems(suggestions)
                self.update_suggestion_theme()
                self.suggestion_list.show()
                self.suggestion_list.setCurrentRow(0)
                self.suggestion_list.raise_()
                self.update_suggestion_list_position()
                self.suggestion_list.setFixedHeight(min(100, self.suggestion_list.sizeHintForRow(0) * len(suggestions) + 5))
            else:
                self.suggestion_list.hide()
        except Exception as e:
            print(f"Error updating suggestions: {e}")
    def find_and_load_character_image(self, character_name):
        image_paths = find_character_images(character_name)
        if not image_paths:
            print(f"No media found for '{character_name}' in the 'media' folder or its subfolders.")
            return
        if len(image_paths) == 1:
            self.load_media_file(image_paths[0])
        else:
            dialog = ImagePickerDialog(image_paths, self)
            if dialog.exec_() == QDialog.Accepted and dialog.get_selected_path():
                self.load_media_file(dialog.get_selected_path())
    def select_suggestion(self, item):
        if not self.is_main_item: return
        try:
            selected_name = item.text()
            self.char_name_entry.setText(selected_name)
            self.hash_entry.setText(CHARACTER_HASHES[selected_name])
            self.suggestion_list.hide()
            self.find_and_load_character_image(selected_name)
        except Exception as e:
            print(f"Error selecting suggestion: {e}")

class IniMakerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("INI File Generator")
        
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame { border: none; }
            ItemWidget { border-bottom: 1px solid #444; padding-bottom: 15px; margin-bottom: 15px; }
            QFrame#SettingsFrame { 
                border: none; 
                background-color: #303030;
                border-radius: 6px; 
                margin-top: 10px; 
            }
            QLabel { color: #e0e0e0; background-color: transparent; padding: 5px 0; }
            QLineEdit { background-color: #3c3c3c; border: 1px solid #555; border-radius: 4px; padding: 6px; color: #f0f0f0; }
            QLineEdit:focus { border: 1px solid #00a0a0; }
            QPushButton { background-color: #008080; color: white; border: 1px solid #006a6a; border-radius: 4px; padding: 8px 16px; font-weight: bold; min-height: 20px; }
            QPushButton:hover { background-color: #009999; border: 1px solid #00b0b0; }
            QPushButton:pressed { background-color: #006666; border: 1px solid #005050; }
            QPushButton:disabled { background-color: #555555; color: #888888; border: 1px solid #444444; }
            QPushButton#RemoveButton { font-size: 14px; font-family: 'Consolas', monospace; font-weight: bold; max-width: 28px; padding: 4px; background-color: #6d3a3a; border-color: #8b4a4a; }
            QPushButton#RemoveButton:hover { background-color: #8b4a4a; border-color: #a25e5e; }
            QPushButton#RemoveButton:pressed { background-color: #5b2e2e; }
            QCheckBox { color: #e0e0e0; spacing: 5px; }
            QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #555; border-radius: 3px; background-color: #3c3c3c; }
            QCheckBox::indicator:checked { background-color: #008080; }
            QCheckBox::indicator:unchecked:hover { border: 1px solid #777; }
            #PreviewFrameOuter { background-color: transparent; border-radius: 6px; }
            #PreviewFrameInner { background-color: transparent; border-radius: 3px; }
            #PreviewContentLabel { background-color: #ffffff; }
            QSlider::groove:horizontal { border: 1px solid #4a4a4a; background: #3c3c3c; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #00a0a0; border: 1px solid #00a0a0; width: 16px; margin: -7px 0; border-radius: 8px; }
            QSlider::sub-page:horizontal { background: #008080; border-radius: 2px; }
            QScrollArea { border: none; }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)
        self.item_widgets = []
        self.item1 = ItemWidget(is_deletable=False, is_main_item=True, parent=self)
        self.item_widgets.append(self.item1)
        self.switch_portrait_toggle = QCheckBox("Enable Switch Portrait")
        self.other_items_group = QFrame()
        self.other_items_group.setObjectName("OtherItemsGroup")
        self.other_items_layout = QVBoxLayout(self.other_items_group)
        self.other_items_layout.setContentsMargins(0, 0, 0, 0)
        self.other_items_layout.setSpacing(10)
        control_bar_layout = QHBoxLayout()
        self.show_hide_button = QPushButton("Hide Other Portraits")
        self.add_item_button = QPushButton("Add New Portrait")
        control_bar_layout.addWidget(self.show_hide_button)
        control_bar_layout.addWidget(self.add_item_button)
        self.other_items_layout.addLayout(control_bar_layout)
        self.sub_items_container = QWidget()
        self.sub_items_layout = QVBoxLayout(self.sub_items_container)
        self.sub_items_layout.setContentsMargins(0, 0, 0, 0)
        self.sub_items_layout.setSpacing(0)
        self.other_items_layout.addWidget(self.sub_items_container)
        self.create_button = QPushButton("Create INI File")
        self.main_layout.addWidget(self.item1)
        self.main_layout.addWidget(self.switch_portrait_toggle)
        self.main_layout.addWidget(self.other_items_group)
        self.main_layout.addWidget(self.create_button)
        self.other_items_group.hide()
        self.is_sub_items_visible = True
        self.switch_portrait_toggle.toggled.connect(self._toggle_multi_portrait_mode)
        self.add_item_button.clicked.connect(self.add_new_item)
        self.show_hide_button.clicked.connect(self._toggle_sub_items_visibility)
        self.create_button.clicked.connect(self.create_ini_file)

    def add_new_item(self):
        item = ItemWidget(is_deletable=True, is_main_item=False, parent=self.sub_items_container)
        item.delete_requested.connect(self._remove_item)
        self.sub_items_layout.addWidget(item)
        self.item_widgets.append(item)
        if not self.is_sub_items_visible:
            self._toggle_sub_items_visibility()

    def _remove_item(self, item_to_remove):
        if item_to_remove in self.item_widgets:
            self.item_widgets.remove(item_to_remove)
            self.sub_items_layout.removeWidget(item_to_remove)
            item_to_remove.deleteLater()
            if len(self.item_widgets) == 1:
                self.other_items_group.hide()
                self.switch_portrait_toggle.setChecked(False)

    def _toggle_multi_portrait_mode(self, checked):
        self.other_items_group.setVisible(checked)
        if not checked:
            while len(self.item_widgets) > 1:
                self._remove_item(self.item_widgets[-1])
            self.item1.toggle_options_frame.setVisible(self.item1.frame_count > 1)

    def _toggle_sub_items_visibility(self):
        self.is_sub_items_visible = not self.is_sub_items_visible
        self.sub_items_container.setVisible(self.is_sub_items_visible)
        self.show_hide_button.setText("Hide Other Portraits" if self.is_sub_items_visible else "Show Other Portraits")

    def create_ini_file(self):
        try:
            items_data = []
            is_multi_portrait = self.switch_portrait_toggle.isChecked() and len(self.item_widgets) > 1
            main_item_data = self.item1.get_data()
            if not main_item_data['char_name'] or not main_item_data['hash_value']:
                print("Please provide Character Name and Hash Value for the primary portrait.")
                return
            if not main_item_data['filepath']:
                print("Please select a file for the primary portrait.")
                return
            items_data.append(main_item_data)
            if is_multi_portrait:
                for item in self.item_widgets[1:]:
                    data = item.get_data()
                    if not data['filepath']:
                        print("Please select a file for every portrait in the switch list.")
                        return
                    data['char_name'] = main_item_data['char_name']
                    data['hash_value'] = main_item_data['hash_value']
                    items_data.append(data)
            self.create_button.setEnabled(False)
            self.create_button.setText("Creating Mod...")
            self.conversion_thread = ConversionThread(items_data, is_multi_portrait)
            self.conversion_thread.finished.connect(self.conversion_finished)
            self.conversion_thread.start()
        except Exception as e:
            print(f"Error creating INI file: {e}")
            self.conversion_finished()

    def conversion_finished(self):
        print("Conversion and INI file generation completed.")
        self.create_button.setEnabled(True)
        self.create_button.setText("Create INI File")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    main_window_scroll_area = QScrollArea()
    main_window_scroll_area.setWidgetResizable(True)
    main_window_scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
    main_window_scroll_area.verticalScrollBar().setStyleSheet("QScrollBar:vertical { border: none; background: #2b2b2b; width: 10px; margin: 0px 0px 0px 0px; } QScrollBar::handle:vertical { background: #555; min-height: 20px; border-radius: 5px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { border: none; background: none; }")

    main_window = QWidget()
    main_window.setWindowTitle("Test IniMakerWidget")
    
    outer_container = QWidget()
    outer_container.setStyleSheet("QWidget { background-color: #2b2b2b; border-radius: 10px; }")
    outer_layout = QVBoxLayout(outer_container)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    
    header_layout = QHBoxLayout()
    header_layout.addStretch()
    exit_button = QPushButton("X")
    exit_button.setFixedSize(40, 40)
    exit_button.setStyleSheet("QPushButton { font-size: 16px; background-color: #c05050; border-radius: 8px; font-weight: bold; margin-top: 5px; margin-right: 5px; } QPushButton:hover { background-color: #d06060; }")
    exit_button.clicked.connect(app.quit)
    header_layout.addWidget(exit_button)
    outer_layout.addLayout(header_layout)

    ini_maker = IniMakerWidget()
    outer_layout.addWidget(ini_maker)

    main_layout = QVBoxLayout(main_window)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(outer_container)

    main_window_scroll_area.setWidget(main_window)
    
    frameless_container = QWidget()
    frameless_container_layout = QVBoxLayout(frameless_container)
    frameless_container_layout.setContentsMargins(0,0,0,0)
    frameless_container_layout.addWidget(main_window_scroll_area)
    frameless_container.setWindowFlags(Qt.FramelessWindowHint)
    frameless_container.setAttribute(Qt.WA_TranslucentBackground)

    frameless_container.resize(480, 800)
    frameless_container.show()
    sys.exit(app.exec_())
