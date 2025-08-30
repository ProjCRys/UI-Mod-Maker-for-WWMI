import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QSlider, QGridLayout, QSizePolicy, QFrame, QCompleter, QDialog, QDialogButtonBox)
from PyQt5.QtCore import Qt, QTimer, QEvent, QRect, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter, QIcon # QIcon moved here

from PIL import Image, ImageSequence, ImageCms

# For video processing, ensure OpenCV is installed.
import cv2

CONFIG_FILE = "config.json"
# MODIFIED: Default opacity set to 255 (100% visible)
TEMPLATE_OPACITY = 255  # Global variable for template opacity (0-255)
TEXCONV_PATH = 'General_UI_Tool/texconv.exe'

# MODIFIED: Load character hash data from the text file with per-line error handling
def load_character_hashes(file_path):
    """Load character hashes from a text file, skipping malformed lines."""
    hashes = {}
    try:
        with open(file_path, "r") as file:
            # Enumerate to provide line number in error messages
            for i, line in enumerate(file, 1):
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                try:
                    # Attempt to split the line
                    name, hash_value = line.split(" --> ")
                    # Add the valid entry to the dictionary, stripping any extra whitespace
                    hashes[name.strip()] = hash_value.strip()
                except ValueError:
                    # This block executes if the line doesn't contain " --> "
                    # or has more than one, causing split to return a list of a different size.
                    print(f"Warning: Skipping malformed line {i} in '{file_path}': '{line}'")
                    # Continue to the next line in the file
                    continue
    except FileNotFoundError:
        print(f"Error: Character hashes file not found at '{file_path}'")
    except Exception as e:
        print(f"An unexpected error occurred while loading character hashes: {e}")
    return hashes

CHARACTER_HASHES = load_character_hashes("UI_Hashes.txt")

def load_config():
    """Load the last used folder path from the config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                return config.get("last_folder_path", "")
        except Exception as e:
            print(f"Error loading config: {e}")
    return ""

def save_config(folder_path):
    """Save the last used folder path to the config file."""
    config = {"last_folder_path": folder_path}
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file)
    except Exception as e:
        print(f"Error saving config: {e}")

def is_video_file(filepath):
    """Determine if the given file is a video based on its extension."""
    video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    ext = os.path.splitext(filepath)[1].lower()
    return ext in video_exts

def get_frame_count(filepath):
    """Returns the number of frames in a GIF or video file."""
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
                    print("The file is not animated.")
                    return 1
    except Exception as e:
        print(f"Error processing file: {e}")
        return 1

def save_frames_to_folder(filepath, folder_path, template_width, template_height):
    """Saves each frame of the animated image or video to the specified folder as PNGs."""
    try:
        if is_video_file(filepath):
            cap = cv2.VideoCapture(filepath)
            frame_index = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                # Convert BGR (OpenCV format) to RGBA
                frame_rgba = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                # Convert numpy array to PIL Image and resize
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
                    # Apply sRGB transformation if an ICC profile is available
                    if 'icc_profile' in frame_image.info:
                        icc_profile = frame_image.info['icc_profile']
                        srgb_profile = ImageCms.createProfile('sRGB')
                        transform = ImageCms.buildTransformFromOpenProfiles(icc_profile, srgb_profile, 'RGBA', 'RGBA', intent=ImageCms.INTENT_PERCEPTUAL)
                        frame_image = ImageCms.applyTransform(frame_image, transform)
                    frame_image.save(os.path.join(folder_path, f"{i}.png"))
    except Exception as e:
        print(f"Error saving frames to folder: {e}")

def generate_frame_conditions(frame_count):
    """Generates the conditionals for frame switching."""
    conditions = []
    for i in range(frame_count):
        conditions.append(f"else if $framevar == {i}")
        conditions.append(f"    this = ResourceFrame{i}")
    return "\n".join(conditions)

def generate_resource_frames(char_name, hash_value, frame_count):
    """Generates the resource frames section."""
    frames = []
    for i in range(frame_count):
        frames.append(f"[ResourceFrame{i}]")
        frames.append(f"filename = {hash_value} - {char_name}/{i}.dds")
    return "\n".join(frames)

def generate_ini_file(char_name, hash_value, frame_count):
    """Generates an INI file with the given parameters."""
    try:
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
    this = ResourceFrame0
{generate_frame_conditions(frame_count)}
endif

{generate_resource_frames(char_name, hash_value, frame_count)}
"""
        filename = f"{char_name}.ini"
        with open(filename, "w") as file:
            file.write(template)
        return filename
    except Exception as e:
        print(f"Error generating INI file: {e}")
        return None

def find_character_images(character_name):
    """Searches the 'media' folder and its subfolders for images containing the character's name."""
    media_path = Path("media")
    if not media_path.exists() or not media_path.is_dir():
        return []

    matches = []
    media_exts = ['.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.svg', '.webp', '.raw', '.heif', '.ico', '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']

    # Use rglob('*') to recursively search all files in all subdirectories
    for f in media_path.rglob('*'):
        if f.is_file() and character_name.lower() in f.stem.lower() and f.suffix.lower() in media_exts:
            matches.append(str(f))

    return matches

class ImagePickerDialog(QDialog):
    def __init__(self, image_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Character Image")
        self.setMinimumSize(400, 300)

        self.layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        self.list_widget.setIconSize(QSize(100, 100))
        self.list_widget.setSpacing(5)
        self.list_widget.setViewMode(QListWidget.IconMode)
        self.list_widget.setResizeMode(QListWidget.Adjust)
        self.list_widget.itemDoubleClicked.connect(self.accept)

        for path in image_paths:
            item = QListWidgetItem(os.path.basename(path))
            pixmap = QPixmap(path)
            icon = QIcon(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            item.setIcon(icon)
            item.setData(Qt.UserRole, path)
            self.list_widget.addItem(item)

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

        self.layout.addWidget(self.list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)

        self.selected_file_path = None

    def accept(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_file_path = current_item.data(Qt.UserRole)
        super().accept()

    def get_selected_path(self):
        return self.selected_file_path

class ConversionThread(QThread):
    finished = pyqtSignal()

    def __init__(self, char_name, hash_value, filepath, template_width, template_height):
        super().__init__()
        self.char_name = char_name
        self.hash_value = hash_value
        self.filepath = filepath
        self.template_width = template_width
        self.template_height = template_height

    def run(self):
        try:
            frame_count = get_frame_count(self.filepath)

            # Create a temporary folder to save frames
            temp_folder_path = os.path.join(os.getcwd(), f"temp_frames_{self.char_name}")
            os.makedirs(temp_folder_path, exist_ok=True)
            save_frames_to_folder(self.filepath, temp_folder_path, self.template_width, self.template_height)

            # Convert PNGs to DDS
            dds_folder_path = os.path.join(os.getcwd(), self.char_name)
            convert_pngs_to_dds(temp_folder_path, dds_folder_path)

            # Generate the INI file
            ini_file = generate_ini_file(self.char_name, self.hash_value, frame_count)
            if ini_file:
                # Ask the user where to save the final folder
                default_folder_name = f"{self.char_name}"
                folder_path = QFileDialog.getExistingDirectory(None, "Save Folder", default_folder_name)
                if folder_path:
                    final_char_folder = os.path.join(folder_path, self.char_name)
                    os.makedirs(final_char_folder, exist_ok=True)

                    final_dds_folder = os.path.join(final_char_folder, f"{self.hash_value} - {self.char_name}")
                    shutil.move(dds_folder_path, final_dds_folder)

                    shutil.move(ini_file, os.path.join(final_char_folder, ini_file))

                    save_config(folder_path)

            if os.path.exists(temp_folder_path):
                shutil.rmtree(temp_folder_path)
                print(f"Deleted temp_frames folder: {temp_folder_path}")
        except Exception as e:
            print(f"Error in conversion thread: {e}")
        finally:
            self.finished.emit()

def convert_pngs_to_dds(input_folder, output_folder, gpu_id=1):
    """Convert PNGs to DDS format using Texconv."""
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)
    input_files = list(input_folder.glob('*.png'))
    command = [
        TEXCONV_PATH, '-f', 'BC7_UNORM', '-srgbi', '-gpu', str(gpu_id),
        '-bc', 'x', '-o', str(output_folder), str(input_folder) + '/*.png'
    ]
    try:
        subprocess.run(command, check=True)
        print(f"Converted images in {input_folder} successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error during conversion of {input_folder}: {e}")
    converted_files = list(output_folder.glob('*.dds'))
    return len(input_files), len(converted_files)

class IniMakerWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("INI File Generator")
        
        # --- UI STYLING ---
        self.setStyleSheet("""
            IniMakerWidget {
                background-color: #2b2b2b;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QFrame {
                border: none;
            }
            QLabel {
                color: #e0e0e0;
                background-color: transparent;
                padding: 5px 0;
            }
            QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 6px;
                color: #f0f0f0;
            }
            QLineEdit:focus {
                border: 1px solid #00a0a0;
            }
            QPushButton {
                background-color: #008080;
                color: white;
                border: 1px solid #006a6a; /* Added border for contrast */
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #009999;
                border: 1px solid #00b0b0; /* Brighter border on hover */
            }
            QPushButton:pressed {
                background-color: #006666; /* Darker background for clicked state */
                border: 1px solid #005050; /* Darker border for clicked state */
            }
            QPushButton:disabled {
                background-color: #555555;
                color: #888888;
                border: 1px solid #444444; /* Added border for consistency */
            }
            #PreviewFrameOuter {
                background-color: #d36a6a;
                border-radius: 6px;
            }
            #PreviewFrameInner {
                background-color: #e8985e;
                border-radius: 3px;
            }
            #PreviewContentLabel {
                background-color: #ffffff;
            }
            QSlider::groove:horizontal {
                border: 1px solid #4a4a4a;
                background: #3c3c3c;
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #00a0a0;
                border: 1px solid #00a0a0;
                width: 16px;
                margin: -7px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #008080;
                border-radius: 2px;
            }
            /* Default QListWidget style removed from here, will be set dynamically */
        """)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(12)

        try:
            self.template_img = Image.open("templates/team_portrait.png").convert("RGBA")
            self.template_width, self.template_height = self.template_img.size
            self.template_data = list(self.template_img.getdata())
            for i, item in enumerate(self.template_data):
                if item[3] == 0:
                    self.template_data[i] = (0, 0, 0, 0)
                else:
                    self.template_data[i] = item[:-1] + (TEMPLATE_OPACITY,)
            self.template_img.putdata(self.template_data)
            self.template_image = QPixmap.fromImage(self.pil_to_qimage(self.template_img))
        except Exception as e:
            print(f"Error loading template image: {e}")
            self.template_image = QPixmap()
            # Set default sizes if template fails to load
            self.template_width, self.template_height = 256, 256

        self.char_name_label = QLabel("Character Name:")
        self.char_name_entry = QLineEdit(self)
        self.char_name_entry.textChanged.connect(self.update_suggestions)
        self.char_name_entry.installEventFilter(self)

        self.hash_label = QLabel("Hash Value:")
        self.hash_entry = QLineEdit(self)

        self.suggestion_list = QListWidget(self)
        self.suggestion_list.setFixedWidth(200)
        self.suggestion_list.setMinimumHeight(20)
        self.suggestion_list.setMaximumHeight(100)
        self.suggestion_list.itemClicked.connect(self.select_suggestion)
        self.suggestion_list.hide()
        
        # --- DYNAMIC THEME UPDATE SETUP ---
        self.current_theme = None # Track the current theme to avoid redundant updates
        # Install event filter to catch hover events (QEvent.Enter)
        self.suggestion_list.installEventFilter(self)
        # Connect scrollbar signal to the theme update function
        self.suggestion_list.verticalScrollBar().valueChanged.connect(self.update_suggestion_theme)
        # Set the initial theme
        self.update_suggestion_theme()

        # --- PREVIEW FRAME REWORK for styling ---
        self.preview_frame = QFrame(self)
        self.preview_frame.setObjectName("PreviewFrameOuter")
        self.preview_frame.setFixedSize(self.template_width + 40, self.template_height + 40)
        self.preview_frame.mousePressEvent = self.open_file
        self.preview_frame.setCursor(Qt.PointingHandCursor)

        outer_layout = QVBoxLayout(self.preview_frame)
        outer_layout.setContentsMargins(10, 10, 10, 10)
        inner_frame = QFrame(self.preview_frame)
        inner_frame.setObjectName("PreviewFrameInner")
        outer_layout.addWidget(inner_frame)
        inner_layout = QVBoxLayout(inner_frame)
        inner_layout.setContentsMargins(10, 10, 10, 10)
        self.preview_label = QLabel()
        self.preview_label.setObjectName("PreviewContentLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setPixmap(self.template_image)
        self.preview_label.setFixedSize(self.template_width, self.template_height)
        inner_layout.addWidget(self.preview_label)
        
        self.create_button = QPushButton("Create INI File", self)
        self.create_button.clicked.connect(self.create_ini_file)

        self.opacity_label = QLabel("Template Opacity:")
        self.opacity_slider = QSlider(Qt.Horizontal, self)
        self.opacity_slider.setRange(0, 255)
        self.opacity_slider.setValue(TEMPLATE_OPACITY)
        self.opacity_slider.valueChanged.connect(self.update_template_opacity)

        # --- LAYOUT REWORK ---
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        grid_layout.addWidget(self.char_name_label, 0, 0)
        grid_layout.addWidget(self.char_name_entry, 0, 1)
        grid_layout.addWidget(self.hash_label, 1, 0)
        grid_layout.addWidget(self.hash_entry, 1, 1)
        grid_layout.setColumnStretch(1, 1)
        preview_wrapper = QWidget()
        preview_layout = QHBoxLayout(preview_wrapper)
        preview_layout.setContentsMargins(0, 10, 0, 10)
        preview_layout.addWidget(self.preview_frame)
        grid_layout.addWidget(preview_wrapper, 2, 0, 1, 2, alignment=Qt.AlignCenter)
        grid_layout.addWidget(self.create_button, 3, 0, 1, 2)
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        grid_layout.addLayout(opacity_layout, 4, 0, 1, 2)
        self.layout.addLayout(grid_layout)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.current_frame_index = 0
        self.frames = []
        self.source_frames = []
        self.source_image = None
        self.filepath = None

    def update_suggestion_theme(self):
        """Reads settings.json and updates the suggestion box style if the theme changed."""
        new_theme = "dark"  # Default theme
        try:
            with open("settings.json", "r") as f:
                settings = json.load(f)
                if "theme" in settings:
                    new_theme = settings.get("theme", "dark").lower()
                elif "dark_mode" in settings:
                    new_theme = "dark" if settings.get("dark_mode", False) else "light"
        except (FileNotFoundError, json.JSONDecodeError):
            pass # Keep default theme if file is missing/invalid

        # Only update if the theme has actually changed
        if new_theme == self.current_theme:
            return
        
        self.current_theme = new_theme

        if self.current_theme == "light":
            stylesheet = """
                QListWidget {
                    background-color: #ffffff; border: 1px solid #c0c0c0;
                    padding: 2px; color: #000000;
                }
                QListWidget::item { padding: 4px; border-radius: 2px; }
                QListWidget::item:hover { background-color: #e6e6e6; }
                QListWidget::item:selected { background-color: #0078d7; color: #ffffff; }
            """
        else: # Dark theme
            stylesheet = """
                QListWidget {
                    background-color: #3c3c3c; border: 1px solid #555;
                    padding: 2px; color: #e0e0e0;
                }
                QListWidget::item { padding: 4px; border-radius: 2px; }
                QListWidget::item:hover { background-color: #4a4a4a; }
                QListWidget::item:selected { background-color: #008080; color: white; }
            """
        self.suggestion_list.setStyleSheet(stylesheet)

    def eventFilter(self, obj, event):
        # Filter for the character name input field
        if obj == self.char_name_entry:
            if event.type() == QEvent.FocusIn:
                self.update_suggestion_theme() # Update theme when it's about to appear
                self.update_suggestions()
                if self.suggestion_list.count() > 0:
                    self.suggestion_list.show()
                    self.update_suggestion_list_position()
            elif event.type() == QEvent.FocusOut:
                # Use a timer to hide, allowing clicks on the suggestion list
                QTimer.singleShot(150, self.suggestion_list.hide)

        # Filter for the suggestion list itself
        if obj == self.suggestion_list:
            # Update theme on hover
            if event.type() == QEvent.Enter:
                self.update_suggestion_theme()

        return super().eventFilter(obj, event)

    def update_suggestion_list_position(self):
        entry_pos = self.char_name_entry.mapTo(self, self.char_name_entry.rect().bottomLeft())
        self.suggestion_list.move(entry_pos)
        self.suggestion_list.setFixedWidth(self.char_name_entry.width())

    def pil_to_qimage(self, pil_image):
        try:
            if pil_image.mode == 'RGBA':
                return QImage(pil_image.tobytes("raw", "RGBA"), pil_image.size[0], pil_image.size[1], QImage.Format_RGBA8888)
            else:
                return QImage(pil_image.tobytes("raw", "RGB"), pil_image.size[0], pil_image.size[1], QImage.Format_RGB888)
        except Exception as e:
            print(f"Error converting PIL image to QImage: {e}")
            return QImage()

    def load_media_file(self, filepath):
        try:
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                return
            self.filepath = filepath
            if is_video_file(filepath):
                self.frame_count = get_frame_count(filepath)
                self.show_video(filepath)
            elif filepath.lower().endswith(".gif"):
                self.frame_count = get_frame_count(filepath)
                self.show_gif(filepath)
            else:
                self.frame_count = 1
                self.show_image(filepath)
        except Exception as e:
            print(f"Error loading media file {filepath}: {e}")

    def open_file(self, event):
        try:
            last_folder = load_config()
            initial_dir = last_folder if last_folder and os.path.exists(last_folder) else os.path.join(os.getcwd(), "media")
            if not os.path.exists(initial_dir):
                initial_dir = os.getcwd()

            filepath, _ = QFileDialog.getOpenFileName(
                self, "Open Image, GIF, or Video", initial_dir,
                "Media Files (*.gif *.png *.jpg *.bmp *.tiff *.svg *.webp *.raw *.heif *.ico *.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
            )
            if filepath:
                self.load_media_file(filepath)
                save_config(os.path.dirname(filepath))
        except Exception as e:
            print(f"Error opening file: {e}")

    def show_gif(self, filepath):
        try:
            self.timer.stop()
            gif_image = Image.open(filepath)
            self.source_frames = [frame.copy().convert("RGBA").resize((self.template_width, self.template_height), Image.LANCZOS) for frame in ImageSequence.Iterator(gif_image)]
            self.source_image = None
            self.frames = [QPixmap.fromImage(self.pil_to_qimage(Image.alpha_composite(source_frame, self.template_img))) for source_frame in self.source_frames]
            if self.frames:
                self.current_frame_index = 0
                self.timer.start(100)
        except Exception as e:
            print(f"Error displaying GIF: {e}")

    def show_image(self, filepath):
        try:
            self.timer.stop()
            image = Image.open(filepath)
            self.source_image = image.resize((self.template_width, self.template_height), Image.LANCZOS).convert("RGBA")
            self.source_frames = []
            composite_image = Image.alpha_composite(self.source_image, self.template_img)
            self.preview_label.setPixmap(QPixmap.fromImage(self.pil_to_qimage(composite_image)))
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
                self.frames = [QPixmap.fromImage(self.pil_to_qimage(Image.alpha_composite(sf.convert("RGBA"), self.template_img))) for sf in self.source_frames]
                self.current_frame_index = 0
                self.timer.start(interval)
        except Exception as e:
            print(f"Error displaying video: {e}")

    def update_frame(self):
        try:
            if self.frames:
                self.preview_label.setPixmap(self.frames[self.current_frame_index])
                self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
        except Exception as e:
            print(f"Error updating frame: {e}")

    def create_ini_file(self):
        try:
            char_name = self.char_name_entry.text()
            hash_value = self.hash_entry.text()
            if not char_name or not hash_value or not self.filepath:
                print("Please provide all inputs and select a file.")
                return
            self.create_button.setEnabled(False)
            self.create_button.setText("Creating Mod...")
            self.conversion_thread = ConversionThread(char_name, hash_value, self.filepath, self.template_width, self.template_height)
            self.conversion_thread.finished.connect(self.conversion_finished)
            self.conversion_thread.start()
        except Exception as e:
            print(f"Error creating INI file: {e}")

    def conversion_finished(self):
        print("Conversion and INI file generation completed.")
        self.create_button.setEnabled(True)
        self.create_button.setText("Create INI File")

    def update_template_opacity(self, opacity):
        global TEMPLATE_OPACITY
        TEMPLATE_OPACITY = opacity
        try:
            template_img = Image.open("templates/team_portrait.png").convert("RGBA")
            template_data = list(template_img.getdata())
            for i, item in enumerate(template_data):
                if item[3] != 0:
                    template_data[i] = item[:-1] + (int(opacity),)
            template_img.putdata(template_data)
            self.template_img = template_img

            if self.source_image:
                composite = Image.alpha_composite(self.source_image, self.template_img)
                self.preview_label.setPixmap(QPixmap.fromImage(self.pil_to_qimage(composite)))
            elif self.source_frames:
                self.frames = [QPixmap.fromImage(self.pil_to_qimage(Image.alpha_composite(sf, self.template_img))) for sf in self.source_frames]
                if self.frames:
                    self.current_frame_index = min(self.current_frame_index, len(self.frames) - 1)
                    self.preview_label.setPixmap(self.frames[self.current_frame_index])
            else:
                self.template_image = QPixmap.fromImage(self.pil_to_qimage(self.template_img))
                self.preview_label.setPixmap(self.template_image)
        except Exception as e:
            print(f"Error updating template opacity: {e}")

    def update_suggestions(self):
        try:
            input_text = self.char_name_entry.text()
            self.suggestion_list.clear()
            suggestions = sorted([name for name in CHARACTER_HASHES.keys() if name.lower().startswith(input_text.lower())])
            self.suggestion_list.addItems(suggestions)
            if suggestions:
                self.update_suggestion_theme() # Update theme when it's about to appear
                self.suggestion_list.show()
                self.suggestion_list.setCurrentRow(0)
                self.suggestion_list.raise_()
                self.update_suggestion_list_position()
                self.suggestion_list.setFixedHeight(min(100, self.suggestion_list.sizeHintForRow(0) * len(suggestions)))
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
        try:
            selected_name = item.text()
            self.char_name_entry.setText(selected_name)
            self.hash_entry.setText(CHARACTER_HASHES[selected_name])
            self.suggestion_list.hide()
            self.find_and_load_character_image(selected_name)
        except Exception as e:
            print(f"Error selecting suggestion: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = QWidget()
    main_window.setWindowTitle("Test IniMakerWidget")
    main_window.setStyleSheet("background-color: #1e1e1e;")
    layout = QVBoxLayout(main_window)
    layout.setContentsMargins(20, 20, 20, 20)
    ini_maker = IniMakerWidget()
    layout.addWidget(ini_maker)
    main_window.resize(450, 700)
    main_window.show()
    sys.exit(app.exec_())