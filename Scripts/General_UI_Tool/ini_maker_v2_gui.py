import sys
import os
import json
import shutil
import subprocess
import re
import imageio.v2 as imageio
from pathlib import Path

from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFileDialog, QSlider, QGridLayout, QFrame, QDialog,
                             QDialogButtonBox, QMainWindow, QProgressBar, QScrollArea, QTabWidget,
                             QMessageBox, QComboBox, QCompleter)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPalette

from PIL import Image, ImageSequence

# --- Global Constants ---
CONFIG_FILE = "config.json"
TEMPLATE_OPACITY = 255
# Ensure this path is correct relative to where you run the script.
TEXCONV_PATH = 'General_UI_Tool/texconv.exe'

# --- Helper Functions ---

def load_character_hashes(file_path):
    hashes = {}
    try:
        with open(file_path, "r", encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if not line or " --> " not in line: continue
                name, hash_value = line.split(" --> ", 1)
                hashes[name.strip()] = hash_value.strip()
    except FileNotFoundError:
        print(f"Warning: Character hashes file not found at '{file_path}'")
    except Exception as e:
        print(f"An error occurred while loading character hashes: {e}")
    return hashes

CHARACTER_HASHES = load_character_hashes("UI_Hashes.txt")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as file:
                return json.load(file).get("last_folder_path", "")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}")
    return ""

def save_config(folder_path):
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump({"last_folder_path": folder_path}, file)
    except IOError as e:
        print(f"Error saving config: {e}")

def generate_frame_conditions(frame_count):
    return "\n".join([f"else if $framevar == {i}\n    this = ResourceFrame{i}" for i in range(1, frame_count)])

def generate_resource_frames(char_name, hash_value, frame_count):
    return "\n".join([f"[ResourceFrame{i}]\nfilename = {hash_value} - {char_name}/{i}.dds" for i in range(frame_count)])

def generate_ini_file(char_name, hash_value, frame_count):
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
else if $framevar >= {frame_count - 1}
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
    try:
        filename = f"{char_name}.ini"
        with open(filename, "w", encoding='utf-8') as file:
            file.write(template)
        return filename
    except IOError as e:
        print(f"Error generating INI file: {e}")
        return None

def find_dds_hashes(folder_path):
    hashes, paths = [], []
    if not os.path.isdir(folder_path): return hashes, paths
    pattern = re.compile(r't0=([a-f0-9]+)\([a-f0-9]+\)')
    for filename in sorted(os.listdir(folder_path)):
        if filename.lower().endswith(".dds"):
            if match := pattern.search(filename):
                file_path = os.path.join(folder_path, filename)
                try:
                    imageio.imread(file_path) # Verify file is readable
                    hashes.append(match.group(1))
                    paths.append(file_path)
                except Exception as e:
                    print(f"Skipping un-viewable file {filename}: {e}")
    return hashes, paths

# --- UI Helper Classes ---

class ThumbnailLabel(QLabel):
    clicked = pyqtSignal()
    def __init__(self, parent=None): super().__init__(parent); self.setCursor(Qt.PointingHandCursor)
    def mousePressEvent(self, event): self.clicked.emit()
    def set_selected(self, is_selected):
        self.setProperty("selected", is_selected)
        self.style().unpolish(self); self.style().polish(self)

class TemplateSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Template"); self.setMinimumSize(700, 600)
        self.selected_path = None
        layout = QVBoxLayout(self)
        try:
            highlight_color = self.palette().color(QPalette.Highlight).name()
            self.setStyleSheet(f"QLabel[selected=true] {{ border: 2px solid {highlight_color}; }}")
        except Exception: pass

        tabs = QTabWidget(); tabs.addTab(self._create_recent_tab(), "Recent Templates")
        tabs.addTab(self._create_dds_search_tab(), "Search DDS")
        tabs.addTab(self._create_browse_file_tab(), "Browse File"); layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _create_grid_widget(self):
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); grid = QGridLayout(container)
        scroll.setWidget(container); return scroll, grid

    def _create_pixmap_from_path(self, path, size):
        try:
            np_array = imageio.imread(path)
            h, w, ch = np_array.shape
            fmt = QImage.Format_RGBA8888 if ch == 4 else QImage.Format_RGB888
            q_img = QImage(np_array.data, w, h, ch * w, fmt)
            return QPixmap.fromImage(q_img).scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e:
            print(f"Could not load thumbnail for {path}: {e}"); return None

    def _populate_grid(self, grid, paths):
        while grid.count():
            if child := grid.takeAt(0).widget(): child.deleteLater()
        self.thumbnail_widgets = []
        for i, path in enumerate(paths):
            if pixmap := self._create_pixmap_from_path(path, QSize(128, 128)):
                thumb = ThumbnailLabel(); thumb.setPixmap(pixmap)
                thumb.setAlignment(Qt.AlignCenter); thumb.setProperty("file_path", path)
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self.thumbnail_widgets.append(thumb); grid.addWidget(thumb, i // 4, i % 4)

    def _on_thumbnail_clicked(self):
        self.selected_path = self.sender().property("file_path")
        for widget in self.thumbnail_widgets: widget.set_selected(widget == self.sender())

    def _create_recent_tab(self):
        widget = QWidget(); layout = QVBoxLayout(widget)
        scroll, grid = self._create_grid_widget(); layout.addWidget(scroll)
        templates_dir = Path("templates")
        if templates_dir.is_dir():
            self._populate_grid(grid, [str(p) for p in templates_dir.iterdir() if p.is_file()])
        else:
            layout.addWidget(QLabel("The 'templates' folder will be created when you select your first template."))
        return widget

    def _create_dds_search_tab(self):
        widget = QWidget(); layout = QVBoxLayout(widget)
        btn = QPushButton("Browse for Folder Containing DDS Files...")
        scroll, self.dds_grid = self._create_grid_widget(); layout.addWidget(btn); layout.addWidget(scroll)
        btn.clicked.connect(self._search_for_dds)
        return widget

    def _search_for_dds(self):
        if folder := QFileDialog.getExistingDirectory(self, "Select Folder"):
            _, paths = find_dds_hashes(folder)
            if not paths: QMessageBox.information(self, "Not Found", "No viewable DDS files found.")
            else: self._populate_grid(self.dds_grid, paths)

    def _create_browse_file_tab(self):
        widget = QWidget(); layout = QVBoxLayout(widget); btn = QPushButton("Click to Browse for an Image File...")
        btn.clicked.connect(self._browse_for_file); layout.addWidget(btn); return widget

    def _browse_for_file(self):
        if path := QFileDialog.getOpenFileName(self, "Select Template", "", "Images (*.png *.jpg *.jpeg *.bmp *.dds)")[0]:
            self.selected_path = path; self.accept()

    def get_selected_path(self): return self.selected_path

# --- Main Processing Thread ---

class ProcessThread(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str) # Added string for error messages

    # --- MODIFICATION START 1 ---
    # Added 'template_size' to handle resizing
    def __init__(self, ui_element_name, hash_value, source_frame_paths, save_path, template_size):
        super().__init__()
        self.name = ui_element_name
        self.hash = hash_value
        self.source_frame_paths = source_frame_paths
        self.save_path = save_path
        self.target_width, self.target_height = template_size
    # --- MODIFICATION END 1 ---

    def run(self):
        try:
            # --- MODIFICATION START 2 ---
            # Major rewrite of the processing logic to resize and convert frames
            self.progress.emit(5, "Initializing...")
            if not Path(TEXCONV_PATH).exists():
                raise FileNotFoundError(f"texconv.exe not found at '{TEXCONV_PATH}'. Please ensure it is in the correct location.")

            frame_count = len(self.source_frame_paths)
            if frame_count == 0:
                raise ValueError("No source frames provided.")

            self.progress.emit(10, "Generating INI file...")
            ini_file_path = generate_ini_file(self.name, self.hash, frame_count)
            if not ini_file_path:
                raise IOError("Failed to generate INI file.")

            self.progress.emit(20, "Preparing mod directory...")
            final_mod_folder = Path(self.save_path) / self.name
            final_dds_folder = final_mod_folder / f"{self.hash} - {self.name}"
            
            if final_dds_folder.exists():
                shutil.rmtree(final_dds_folder)
            final_dds_folder.mkdir(parents=True, exist_ok=True)
            
            temp_png_dir = final_dds_folder / "temp_pngs"
            temp_png_dir.mkdir()

            # Process each frame: Resize -> Save Temp PNG -> Convert to DDS
            total_frames = len(self.source_frame_paths)
            for i, frame_path in enumerate(self.source_frame_paths):
                # Update progress for this specific step
                progress_percent = 25 + int(70 * (i / total_frames))
                self.progress.emit(progress_percent, f"Processing frame {i + 1}/{total_frames}...")

                # 1. Read and Resize image using Pillow
                source_image = Image.open(frame_path).convert("RGBA")
                resized_image = source_image.resize((self.target_width, self.target_height), Image.LANCZOS)
                
                # 2. Save as a temporary PNG
                temp_png_path = temp_png_dir / f"{i}.png"
                resized_image.save(temp_png_path)
                
                # 3. Use texconv.exe to convert the PNG to a DDS
                final_dds_path = final_dds_folder / f"{i}.dds"
                
                # Using BC7_UNORM for high quality UI textures with alpha
                command = [
                    TEXCONV_PATH,
                    '-f', 'BC7_UNORM',
                    '-o', str(final_dds_folder),
                    '-y', # Overwrite existing file
                    str(temp_png_path)
                ]
                
                result = subprocess.run(command, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                if result.returncode != 0:
                    error_message = f"texconv.exe failed on frame {i}:\n{result.stderr}"
                    raise RuntimeError(error_message)

            self.progress.emit(95, "Cleaning up...")
            shutil.rmtree(temp_png_dir) # Clean up temporary directory
            shutil.move(ini_file_path, final_mod_folder / Path(ini_file_path).name)
            
            self.progress.emit(100, "Finished!")
            self.finished.emit(True, "Mod created successfully!")
            # --- MODIFICATION END 2 ---
        except Exception as e:
            error_msg = f"An error occurred: {e}"
            print(error_msg)
            # Clean up partial files on error
            if 'ini_file_path' in locals() and Path(ini_file_path).exists():
                Path(ini_file_path).unlink()
            if 'final_mod_folder' in locals() and final_mod_folder.exists():
                shutil.rmtree(final_mod_folder)
            self.finished.emit(False, error_msg)


# --- Main Application Widget ---
class AnimationWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.template_img = None; self.template_width, self.template_height = 256, 256
        self.source_frames = []; self.source_frame_paths = []
        self.current_frame_index = 0
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_frame)
        self.init_ui()
        self.load_animation_folders()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # --- Top Inputs ---
        top_grid = QGridLayout()
        top_grid.addWidget(QLabel("UI Element:"), 0, 0)
        self.ui_element_entry = QLineEdit()
        top_grid.addWidget(self.ui_element_entry, 0, 1)
        top_grid.addWidget(QLabel("Hash Value:"), 1, 0)
        self.hash_entry = QLineEdit()
        top_grid.addWidget(self.hash_entry, 1, 1)

        self.completer = QCompleter(CHARACTER_HASHES.keys(), self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setFilterMode(Qt.MatchStartsWith)
        self.ui_element_entry.setCompleter(self.completer)
        self.completer.activated.connect(self.select_suggestion)

        # --- Middle Stretchy Preview ---
        self.preview_frame = QFrame()
        self.preview_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.preview_frame.mousePressEvent = self.select_template
        self.preview_frame.setCursor(Qt.PointingHandCursor)
        self.preview_label = QLabel("Click to select template")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.addWidget(self.preview_label)

        # --- Bottom Controls ---
        bottom_grid = QGridLayout()
        bottom_grid.addWidget(QLabel("Template Opacity:"), 0, 0)
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 255); self.opacity_slider.setValue(TEMPLATE_OPACITY)
        self.opacity_slider.valueChanged.connect(self.update_template_opacity)
        bottom_grid.addWidget(self.opacity_slider, 0, 1)
        
        bottom_grid.addWidget(QLabel("Animation Frames Folder:"), 1, 0)
        self.folder_combo = QComboBox()
        self.folder_combo.currentTextChanged.connect(self.on_folder_selected)
        bottom_grid.addWidget(self.folder_combo, 1, 1)

        self.create_button = QPushButton("Create Mod")
        self.create_button.clicked.connect(self.start_processing)
        bottom_grid.addWidget(self.create_button, 2, 0, 1, 2)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        bottom_grid.addWidget(self.progress_bar, 3, 0, 1, 2)

        # --- Assemble Layout ---
        main_layout.addLayout(top_grid)
        main_layout.addWidget(self.preview_frame, 1) # The '1' is the stretch factor
        main_layout.addLayout(bottom_grid)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.adjust_template_size()
    
    def select_suggestion(self, name):
        if name in CHARACTER_HASHES:
            self.ui_element_entry.setText(name)
            self.hash_entry.setText(CHARACTER_HASHES[name])

    def load_animation_folders(self):
        self.folder_combo.clear(); self.folder_combo.addItem("Select a folder...")
        frames_dir = Path("extracted_frames")
        if frames_dir.is_dir():
            self.folder_combo.addItems(sorted([f.name for f in frames_dir.iterdir() if f.is_dir()]))

    def select_template(self, event):
        dialog = TemplateSelectionDialog(self)
        if dialog.exec_() == QDialog.Accepted and (path := dialog.get_selected_path()):
            self.load_template(path)

    def load_template(self, path):
        try:
            templates_dir = Path("templates"); templates_dir.mkdir(exist_ok=True)
            dest = templates_dir / Path(path).name
            if not dest.exists() and Path(path).exists(): shutil.copy2(path, dest)
            
            self.template_img = Image.open(path).convert("RGBA")
            self.adjust_template_size()
            
            filename = Path(path).name
            hash_pattern = re.compile(r't0=([a-f0-9]+)\([a-f0-9]+\)')
            if match := hash_pattern.search(filename):
                extracted_hash = match.group(1)
                self.hash_entry.setText(extracted_hash)
                found_name = next((name for name, h in CHARACTER_HASHES.items() if h == extracted_hash), "")
                self.ui_element_entry.setText(found_name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load template image:\n{e}")
            self.template_img = None

    def adjust_template_size(self):
        if self.template_img:
            w, h = self.template_img.size
            available_width = self.preview_frame.width() - 10
            if available_width > 0 and w > 0:
                self.template_width = available_width
                self.template_height = int(available_width * (h / w))
                self.redraw_preview()

    def on_folder_selected(self, folder_name):
        self.timer.stop(); self.source_frames.clear(); self.source_frame_paths.clear()
        if folder_name == "Select a folder...": self.redraw_preview(); return
        
        base_path = Path("extracted_frames") / folder_name
        source_path = base_path / "dds" if (base_path / "dds").is_dir() else base_path
        
        def natural_sort_key(s): return [int(t) if t.isdigit() else t.lower() for t in re.split('([0-9]+)', s.stem)]
        
        image_files = sorted([f for f in source_path.iterdir() if f.suffix.lower() in ['.dds', '.png']], key=natural_sort_key)
        if not image_files: self.redraw_preview(); return
        
        self.source_frame_paths = image_files
        try:
            for img_path in image_files:
                self.source_frames.append(Image.fromarray(imageio.imread(img_path)))
            self.current_frame_index = 0
            self.timer.start(1000 // 30)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not load animation frames:\n{e}")
            self.source_frames.clear(); self.source_frame_paths.clear()
        self.redraw_preview()

    def update_template_opacity(self, opacity):
        global TEMPLATE_OPACITY; TEMPLATE_OPACITY = opacity; self.redraw_preview()

    def redraw_preview(self):
        if not self.template_img: self.preview_label.setText("Click to select template"); self.preview_label.setPixmap(QPixmap()); return
        if self.template_width <= 0 or self.template_height <= 0: return
        
        scaled_template = self.template_img.resize((self.template_width, self.template_height), Image.LANCZOS)
        base_image = Image.new("RGBA", (self.template_width, self.template_height))
        
        if self.source_frames:
            media_frame = self.source_frames[self.current_frame_index]
            scaled_media = media_frame.resize((self.template_width, self.template_height), Image.LANCZOS)
            base_image = Image.alpha_composite(base_image, scaled_media)
        
        alpha = scaled_template.split()[3].point(lambda p: p * (TEMPLATE_OPACITY / 255.0))
        final_image = Image.alpha_composite(base_image, Image.merge("RGBA", (*scaled_template.split()[:3], alpha)))
        
        q_img = QImage(final_image.tobytes(), final_image.width, final_image.height, QImage.Format_RGBA8888)
        self.preview_label.setPixmap(QPixmap.fromImage(q_img))

    def update_frame(self):
        if self.source_frames:
            self.current_frame_index = (self.current_frame_index + 1) % len(self.source_frames)
            self.redraw_preview()

    def start_processing(self):
        name = self.ui_element_entry.text()
        hash_val = self.hash_entry.text()
        if not all([name, hash_val, self.template_img, self.source_frame_paths]):
            QMessageBox.warning(self, "Input Missing", "Please provide a UI Element name, hash, select a template, and choose an animation folder.")
            return

        last_used_dir = load_config()
        save_path = QFileDialog.getExistingDirectory(self, "Select Directory to Save Mod", last_used_dir)
        if not save_path:
            return
        save_config(save_path)
        
        self.create_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setFormat("%p% - %t")
        
        # --- MODIFICATION START 3 ---
        # Pass the original template's dimensions to the processing thread
        template_size = self.template_img.size 
        self.process_thread = ProcessThread(name, hash_val, self.source_frame_paths, save_path, template_size)
        # --- MODIFICATION END 3 ---
        
        self.process_thread.progress.connect(self.update_progress)
        self.process_thread.finished.connect(self.on_process_complete)
        self.process_thread.start()

    def update_progress(self, value, text):
        self.progress_bar.setValue(value)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat(f"%p% - {text}")

    def on_process_complete(self, success, message):
        self.create_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("INI Maker v2")
        self.setCentralWidget(AnimationWidget())
        self.resize(500, 800)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())