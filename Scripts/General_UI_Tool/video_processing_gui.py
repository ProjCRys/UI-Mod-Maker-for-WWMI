# video_processing_gui.py
import os
import sys
import shutil
import imageio
import cv2
import numpy as np
from PIL import Image, ImageDraw
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSize, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QPushButton, QProgressBar, QMessageBox, QFileDialog, 
                             QApplication, QSlider, QFrame, QDialog, 
                             QDialogButtonBox, QScrollArea, QGridLayout, QTabWidget)
from PyQt5.QtGui import QImage, QPixmap, QPainter

# --- Assumed API Import ---
from General_UI_Tool.find_hashes import find_dds_hashes

# --- Assumed Tool Imports ---
from General_UI_Tool.video_fps_converter import process_video_fps
from General_UI_Tool.video_segmentation import segment_video

# --- Backend function to apply visual effects ---
def apply_effects_numpy(np_image, corner_radius_percent, frame_opacity_percent):
    if np_image.shape[2] == 3: source_bgra = cv2.cvtColor(np_image, cv2.COLOR_BGR2BGRA)
    else: source_bgra = np_image.copy()
    h, w = source_bgra.shape[:2]
    processed_image = np.zeros((h, w, 4), dtype=np.uint8)
    radius = int(min(h, w) / 2 * (corner_radius_percent / 100.0))
    if radius > 0:
        mask_pil = Image.new('L', (w, h), 0); draw = ImageDraw.Draw(mask_pil)
        draw.rounded_rectangle((0, 0, w, h), radius=radius, fill=255); mask = np.array(mask_pil)
        processed_image[mask == 255] = source_bgra[mask == 255]
    else: processed_image = source_bgra
    opacity = np.clip(frame_opacity_percent / 100.0, 0.0, 1.0)
    processed_image[:, :, 3] = (processed_image[:, :, 3] * opacity).astype(np.uint8)
    return processed_image

class ThumbnailLabel(QLabel):
    clicked = pyqtSignal()
    # Define theme-specific selection colors
    selection_color_light = "dodgerblue"
    selection_color_dark = "#00cec9"  # Teal color from main.py dark theme

    def __init__(self, parent=None, theme='dark'):
        super().__init__(parent)
        self.theme = theme
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("border: 2px solid transparent; padding: 1px;")

    def mousePressEvent(self, event):
        self.clicked.emit()

    def set_selected(self, is_selected):
        # Use the appropriate color based on the current theme
        if self.theme == 'dark':
            color = self.selection_color_dark if is_selected else "transparent"
        else:
            color = self.selection_color_light if is_selected else "transparent"
        self.setStyleSheet(f"border: 2px solid {color}; padding: 1px;")

class TemplateSelectionDialog(QDialog):
    def __init__(self, parent=None, theme='dark'):
        super().__init__(parent)
        self.theme = theme
        self.setWindowTitle("Select Template")
        self.setMinimumSize(700, 600)
        self.selected_path = None
        self.thumbnail_widgets = []
        
        main_layout = QVBoxLayout(self)
        
        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_recent_tab(), "Recent Templates")
        tab_widget.addTab(self._create_dds_search_tab(), "Search DDS")
        tab_widget.addTab(self._create_browse_file_tab(), "Browse File")
        main_layout.addWidget(tab_widget)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        self._apply_theme()

    def _apply_theme(self):
        if self.theme == 'dark':
            self.setStyleSheet("""
                QDialog {
                    background-color: #2d3436;
                    color: #dfe6e9;
                }
                QLabel {
                    color: #dfe6e9;
                }
                QTabWidget::pane {
                    border-top: 1px solid #444c4e;
                    background: #22282a;
                }
                QTabBar::tab {
                    background: #2d3436;
                    color: #dfe6e9;
                    border: 1px solid #444c4e;
                    border-bottom: none;
                    padding: 8px 20px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #22282a;
                    color: #00cec9;
                    border-color: #444c4e;
                }
                QTabBar::tab:!selected {
                    margin-top: 2px;
                }
                QTabBar::tab:hover {
                    background: #3b4245;
                    color: #00cec9;
                }
                QPushButton {
                    background-color: #3b4245;
                    color: #dfe6e9;
                    border: 1px solid #636e72;
                    padding: 5px 15px;
                    border-radius: 4px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #636e72;
                    border-color: #00cec9;
                }
                QDialogButtonBox QPushButton {
                    background-color: #3b4245;
                    color: #00cec9;
                    border: 1px solid #00cec9;
                }
                QDialogButtonBox QPushButton:hover {
                    background-color: #00cec9;
                    color: #22282a;
                }
                QScrollArea {
                    background-color: #22282a;
                    border: none;
                }
            """)
        else:  # light theme
            self.setStyleSheet("""
                QDialog {
                    background-color: #FFFFFF;
                    color: #333333;
                }
                QLabel {
                    color: #333333;
                }
                QTabWidget::pane {
                    border: 1px solid #FADADD;
                    border-top: none;
                    background: #FFFFFF;
                }
                QTabBar::tab {
                    background: #FFF0F5;
                    color: #333333;
                    border: 1px solid #FADADD;
                    border-bottom: none;
                    padding: 8px 20px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #FFFFFF;
                    color: #E75480;
                    border-color: #FADADD;
                }
                QTabBar::tab:!selected {
                    margin-top: 2px;
                }
                QTabBar::tab:hover {
                    background: #FDECF2;
                }
                QPushButton {
                    background-color: #FFF0F5;
                    color: #E75480;
                    border: 1px solid #FADADD;
                    padding: 5px 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #E75480;
                    color: #ffffff;
                }
                QDialogButtonBox QPushButton {
                    min-width: 80px;
                }
                QScrollArea {
                    background-color: #FFFFFF;
                    border: none;
                }
            """)

    def get_selected_path(self):
        return self.selected_path

    def _create_thumbnail_grid_widget(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(10)
        scroll_area.setWidget(grid_container)
        return scroll_area, grid_layout

    def _populate_grid(self, grid_layout, paths):
        while grid_layout.count():
            child = grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.thumbnail_widgets.clear()
        THUMBNAIL_SIZE = QSize(128, 128)
        num_columns = 4
        for i, path in enumerate(paths):
            row, col = divmod(i, num_columns)
            try:
                img_data = imageio.imread(path)
                h, w, ch = img_data.shape
                fmt = QImage.Format_RGBA8888 if ch == 4 else QImage.Format_RGB888
                q_img = QImage(img_data.data, w, h, ch * w, fmt)
                pixmap = QPixmap.fromImage(q_img).scaled(THUMBNAIL_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                thumb = ThumbnailLabel(theme=self.theme)  # Pass theme to thumbnail
                thumb.setPixmap(pixmap)
                thumb.setFixedSize(THUMBNAIL_SIZE)
                thumb.setAlignment(Qt.AlignCenter)
                thumb.setProperty("file_path", path)
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self.thumbnail_widgets.append(thumb)
                grid_layout.addWidget(thumb, row, col)
            except Exception as e:
                print(f"Could not create thumbnail for {path}: {e}")

    def _on_thumbnail_clicked(self):
        clicked_widget = self.sender()
        self.selected_path = clicked_widget.property("file_path")
        for widget in self.thumbnail_widgets:
            widget.set_selected(widget == clicked_widget)

    def _create_recent_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        scroll_area, grid_layout = self._create_thumbnail_grid_widget()
        layout.addWidget(scroll_area)
        templates_dir = os.path.join(os.getcwd(), "templates")
        if os.path.exists(templates_dir):
            paths = [os.path.join(templates_dir, f) for f in os.listdir(templates_dir)]
            if paths:
                self._populate_grid(grid_layout, paths)
            else:
                layout.addWidget(QLabel("No recent templates found. Load a new template to save it here."))
        else:
            layout.addWidget(QLabel("The 'templates' folder will be created when you select your first template."))
        return widget

    def _create_dds_search_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        browse_button = QPushButton("Browse for Folder Containing DDS Files...")
        scroll_area, self.dds_grid_layout = self._create_thumbnail_grid_widget()
        layout.addWidget(browse_button)
        layout.addWidget(scroll_area)
        browse_button.clicked.connect(self._search_for_dds)
        return widget

    def _search_for_dds(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            _, paths = find_dds_hashes(folder_path)
            if not paths:
                QMessageBox.information(self, "Not Found", "No viewable DDS files found.")
            else:
                self._populate_grid(self.dds_grid_layout, paths)

    def _create_browse_file_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setAlignment(Qt.AlignCenter)
        self.browse_file_label = QLabel("No file selected.")
        
        # Style the label based on the theme
        browse_file_label_color = "grey" if self.theme == 'light' else "#b2bec3"
        self.browse_file_label.setStyleSheet(f"font-style: italic; color: {browse_file_label_color};")
        
        browse_button = QPushButton("Click to Browse for an Image File...")
        browse_button.setMinimumHeight(60)
        layout.addStretch()
        layout.addWidget(browse_button)
        layout.addWidget(self.browse_file_label)
        layout.addStretch()
        browse_button.clicked.connect(self._browse_for_file)
        return widget

    def _browse_for_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Template", "", "Images (*.png *.jpg *.jpeg *.bmp *.dds)")
        if path:
            self.selected_path = path
            self.accept()

class ProcessingThread(QThread):
    update_progress = pyqtSignal(int); update_status = pyqtSignal(str); processing_complete = pyqtSignal(str)
    def __init__(self, media_path, target_fps, segment_length, corner_roundness, transparency, is_static_image, template_path=None):
        super().__init__()
        self.media_path = media_path; self.target_fps = target_fps; self.segment_length = segment_length
        self.corner_roundness = corner_roundness; self.transparency = transparency; self.is_static_image = is_static_image
        self.template_path = template_path; self.template_dims = None
    def run(self):
        if self.template_path:
            try:
                template_data = imageio.imread(self.template_path)
                self.template_dims = (template_data.shape[1], template_data.shape[0])
            except Exception as e: print(f"Worker thread could not read template: {e}")
        if self.is_static_image: self.process_image()
        else: self.process_video()
    def process_image(self):
        try:
            filename = os.path.splitext(os.path.basename(self.media_path))[0]
            out_folder = os.path.join(os.getcwd(), "extracted_frames", filename)
            if os.path.exists(out_folder): shutil.rmtree(out_folder)
            os.makedirs(out_folder, exist_ok=True)
            image_data = cv2.imread(self.media_path, cv2.IMREAD_UNCHANGED)
            if image_data is None: raise IOError("Could not read input image.")
            if self.template_dims:
                h, w = image_data.shape[:2]; th, tw = self.template_dims[1], self.template_dims[0]
                new_h = int(w * th / tw)
                image_data = cv2.resize(image_data, (w, new_h), interpolation=cv2.INTER_LANCZOS4)
            processed_image = apply_effects_numpy(image_data, float(self.corner_roundness), float(self.transparency))
            out_path = os.path.join(out_folder, f"{filename}_frame_0001.png")
            cv2.imwrite(out_path, processed_image)
            self.update_progress.emit(100); self.processing_complete.emit(f"Image processing complete!\nOutput: {out_path}")
        except Exception as e: self.processing_complete.emit(f"An error occurred: {str(e)}")
    def process_video(self):
        temp_folder = os.path.join(os.getcwd(), "temp")
        try:
            self.update_status.emit("Converting FPS..."); self.update_progress.emit(0)
            if os.path.exists(temp_folder): shutil.rmtree(temp_folder)
            converted_video = process_video_fps(self.media_path, int(self.target_fps), temp_folder)
            self.update_progress.emit(25)
            self.update_status.emit("Segmenting video...")
            segment_folder = os.path.join(temp_folder, "video_segments")
            segment_count = segment_video(converted_video, float(self.segment_length), segment_folder)
            self.update_progress.emit(50)
            filename = os.path.splitext(os.path.basename(self.media_path))[0]
            out_folder = os.path.join(os.getcwd(), "extracted_frames", filename)
            if os.path.exists(out_folder): shutil.rmtree(out_folder)
            os.makedirs(out_folder, exist_ok=True)
            self.update_status.emit("Extracting & processing frames...")
            total_frames = 0
            segments = sorted([os.path.join(segment_folder, f) for f in os.listdir(segment_folder)])
            for i, seg_path in enumerate(segments):
                cap = cv2.VideoCapture(seg_path)
                while True:
                    ret, frame = cap.read()
                    if not ret: break
                    if self.template_dims:
                        h, w = frame.shape[:2]; th, tw = self.template_dims[1], self.template_dims[0]
                        new_h = int(w * th / tw)
                        frame = cv2.resize(frame, (w, new_h), interpolation=cv2.INTER_LANCZOS4)
                    processed = apply_effects_numpy(frame, float(self.corner_roundness), float(self.transparency))
                    out_path = os.path.join(out_folder, f"{filename}_frame_{total_frames + 1:04d}.png")
                    cv2.imwrite(out_path, processed)
                    total_frames += 1
                cap.release()
                self.update_progress.emit(50 + int(40 * (i + 1) / len(segments)))
            self.update_status.emit("Cleaning up..."); self.update_progress.emit(90); shutil.rmtree(temp_folder)
            self.update_progress.emit(100)
            self.processing_complete.emit(f"Processing complete!\nSegments: {segment_count}\nFrames: {total_frames}\nOutput: {out_folder}")
        except Exception as e:
            self.processing_complete.emit(f"An error occurred: {str(e)}")
            if os.path.exists(temp_folder): shutil.rmtree(temp_folder)

class VideoProcessingWidget(QWidget):
    def __init__(self, parent=None, theme='dark'):
        super().__init__(parent)
        self.theme = theme  # Store the current theme
        self.template_pixmap = None; self.video_capture = None; self.static_image_pixmap = None
        self.input_is_static_image = False; self.is_gif = False; self.gif_frames = []
        self.template_path = None
        self.timer = QTimer(self); self.timer.timeout.connect(self.update_frame)
        self.source_fps = 30; self.total_frames = 0; self.frame_pos_counter = 0
        self.debounce_timer = QTimer(self); self.debounce_timer.setSingleShot(True); self.debounce_timer.timeout.connect(self.update_preview_from_settings)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self); main_layout.setSpacing(15); main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.addWidget(QLabel("Step 1: Select Input Video or Image"))
        self.media_path = QLineEdit(); self.media_path.setPlaceholderText("Click 'Browse' to select a video, gif, or image file...")
        self.browse_media_button = QPushButton("Browse for Media...")
        main_layout.addWidget(self.media_path); main_layout.addWidget(self.browse_media_button); main_layout.addWidget(self._create_separator())
        main_layout.addWidget(QLabel("Step 2: Set Visual Effects (Live Preview)"))
        extraction_layout = QHBoxLayout()
        roundness_layout = QVBoxLayout(); roundness_layout.addWidget(QLabel("Corner Roundness (0-100):")); self.corner_roundness = QLineEdit("0"); roundness_layout.addWidget(self.corner_roundness)
        transparency_layout = QVBoxLayout(); transparency_layout.addWidget(QLabel("Frame Transparency (0-100):")); self.transparency = QLineEdit("100"); transparency_layout.addWidget(self.transparency)
        extraction_layout.addLayout(roundness_layout); extraction_layout.addLayout(transparency_layout); main_layout.addLayout(extraction_layout); main_layout.addWidget(self._create_separator())
        main_layout.addWidget(QLabel("Step 3: Set Processing Parameters (Video/GIF Only)"))
        settings_layout = QHBoxLayout()
        fps_layout = QVBoxLayout(); fps_layout.addWidget(QLabel("Target FPS (Live Preview):")); self.target_fps = QLineEdit("30"); fps_layout.addWidget(self.target_fps)
        segment_layout = QVBoxLayout(); segment_layout.addWidget(QLabel("Segment Length (s):")); self.segment_length = QLineEdit("10"); segment_layout.addWidget(self.segment_length)
        settings_layout.addLayout(fps_layout); settings_layout.addLayout(segment_layout); main_layout.addLayout(settings_layout); main_layout.addWidget(self._create_separator())
        main_layout.addWidget(QLabel("Step 4: Select Template for Comparison"))
        self.select_template_button = QPushButton("Select Template...")
        main_layout.addWidget(self.select_template_button)
        self.template_path_label = QLabel("No template selected."); self.template_path_label.setStyleSheet("font-style: italic; color: grey;")
        main_layout.addWidget(self.template_path_label)
        slider_layout = QHBoxLayout(); slider_layout.addWidget(QLabel("Template Transparency:")); self.transparency_slider = QSlider(Qt.Horizontal); self.transparency_slider.setRange(0, 100); self.transparency_slider.setValue(50); self.transparency_slider.setEnabled(False); slider_layout.addWidget(self.transparency_slider)
        main_layout.addLayout(slider_layout)
        self.preview_container = QFrame()
        self.preview_container.setStyleSheet("QFrame { border: 1px solid #c0c0c0; border-radius: 4px; background-color: black; }")
        self.preview_container.setMinimumHeight(300)
        preview_layout = QVBoxLayout(self.preview_container); preview_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_label = QLabel("Media preview will appear here"); self.preview_label.setAlignment(Qt.AlignCenter); self.preview_label.setAttribute(Qt.WA_TranslucentBackground); preview_layout.addWidget(self.preview_label)
        main_layout.addWidget(self.preview_container); main_layout.addStretch()
        self.progress = QProgressBar(); self.status_label = QLabel("Ready"); self.process_button = QPushButton("Start Processing")
        main_layout.addWidget(self.progress); main_layout.addWidget(self.status_label); main_layout.addWidget(self.process_button)
        self.browse_media_button.clicked.connect(self.browse_media)
        self.select_template_button.clicked.connect(self.show_template_dialog)
        self.process_button.clicked.connect(self.start_processing)
        self.target_fps.textChanged.connect(self.update_playback_speed)
        self.transparency_slider.valueChanged.connect(self.on_visual_settings_changed)
        self.corner_roundness.textChanged.connect(self.on_visual_settings_changed)
        self.transparency.textChanged.connect(self.on_visual_settings_changed)
    def _create_separator(self): line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken); line.setStyleSheet("margin-top: 10px; margin-bottom: 5px;"); return line

    def browse_media(self):
        filter = "All Media (*.mp4 *.mkv *.gif *.png *.jpg *.jpeg *.bmp *.dds);;Videos (*.mp4 *.mkv);;GIFs (*.gif);;Images (*.png *.jpg *.jpeg *.bmp *.dds)"
        path, _ = QFileDialog.getOpenFileName(self, "Select Media", "", filter)
        if not path: return
        self.media_path.setText(path); self.timer.stop()
        if self.video_capture: self.video_capture.release(); self.video_capture = None
        self.gif_frames.clear(); self.is_gif = self.input_is_static_image = False
        ext = os.path.splitext(path)[1].lower()
        if ext == '.gif': self.is_gif = True; self.target_fps.setEnabled(True); self.segment_length.setEnabled(True); self.load_gif_for_preview(path)
        elif ext in ['.mp4', '.mkv', '.avi', '.mov']: self.target_fps.setEnabled(True); self.segment_length.setEnabled(True); self.load_video_for_preview(path)
        else: self.input_is_static_image = True; self.target_fps.setEnabled(False); self.segment_length.setEnabled(False); self.load_static_image_for_preview(path)

    def load_gif_for_preview(self, path):
        try:
            self.status_label.setText("Loading GIF frames..."); QApplication.processEvents()
            with imageio.get_reader(path) as reader:
                self.source_fps = reader.get_meta_data().get('fps', 10)
                for frame in reader: self.gif_frames.append(cv2.cvtColor(frame, cv2.COLOR_RGBA2BGRA if frame.shape[2]==4 else cv2.COLOR_RGB2BGR))
            self.total_frames = len(self.gif_frames); self.frame_pos_counter = 0; self.update_playback_speed(); self.status_label.setText("Ready")
        except Exception as e: QMessageBox.critical(self, "Error", f"Could not load GIF: {e}"); self.status_label.setText("Error")

    def load_video_for_preview(self, path):
        self.video_capture = cv2.VideoCapture(path)
        if not self.video_capture.isOpened(): QMessageBox.critical(self, "Error", "Could not open video file.")
        else: self.source_fps = self.video_capture.get(cv2.CAP_PROP_FPS) or 30; self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT)); self.frame_pos_counter = 0; self.update_playback_speed()

    def load_static_image_for_preview(self, path):
        self.static_image_pixmap = QPixmap(path)
        if self.static_image_pixmap.isNull(): QMessageBox.critical(self, "Error", "Failed to load image.")
        else: self.update_preview_from_settings()

    def update_playback_speed(self):
        self.timer.stop()
        if self.is_gif or self.video_capture:
            try:
                fps = float(self.target_fps.text())
                if fps > 0: self.timer.start(int(1000 / fps))
            except (ValueError, ZeroDivisionError): pass
            
    def show_template_dialog(self):
        # Pass the stored theme to the dialog
        dialog = TemplateSelectionDialog(self, theme=self.theme)
        if dialog.exec_() == QDialog.Accepted:
            path = dialog.get_selected_path()
            if path:
                self.load_template(path)
            
    def load_template(self, image_path):
        try:
            templates_dir = os.path.join(os.getcwd(), "templates")
            os.makedirs(templates_dir, exist_ok=True)
            dest_path = os.path.join(templates_dir, os.path.basename(image_path))
            if not os.path.abspath(image_path) == os.path.abspath(dest_path):
                shutil.copy2(image_path, dest_path)
            image_data = imageio.imread(image_path)
            if image_data.ndim == 2: image_data = imageio.core.util.grayscale_to_rgb(image_data)
            h, w, ch = image_data.shape
            fmt = QImage.Format_RGBA8888 if ch == 4 else QImage.Format_RGB888
            q_image = QImage(image_data.data, w, h, ch * w, fmt)
            self.template_pixmap = QPixmap.fromImage(q_image)
            self.template_path = image_path
            self.transparency_slider.setEnabled(True)
            self.template_path_label.setText(f"Template: {os.path.basename(image_path)}")
            self.resize_preview_container(); self.update_preview_from_settings()
        except Exception as e:
            self.template_path = None
            QMessageBox.critical(self, "Error", f"Could not load template image:\n{e}\n\nNote: For DDS support, run: pip install imageio[freeimage]")

    def on_visual_settings_changed(self): self.debounce_timer.start(100)
    def update_preview_from_settings(self):
        was_active = self.timer.isActive(); self.timer.stop()
        if self.input_is_static_image and self.static_image_pixmap: self.render_preview(self.static_image_pixmap)
        elif self.is_gif or self.video_capture: self.update_frame()
        elif self.template_pixmap: self.render_preview(self.template_pixmap)
        if was_active: self.timer.start()
    def apply_effects_to_pixmap(self, source_pixmap):
        try: corner_radius = float(self.corner_roundness.text()); frame_opacity = float(self.transparency.text())
        except ValueError: corner_radius, frame_opacity = 0, 100
        qimage = source_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = qimage.bits(); ptr.setsize(qimage.byteCount())
        np_array = np.array(ptr, copy=True).reshape(qimage.height(), qimage.width(), 4)
        processed_array = apply_effects_numpy(np_array, corner_radius, frame_opacity)
        h, w, ch = processed_array.shape
        final_image = QImage(processed_array.data, w, h, ch * w, QImage.Format_ARGB32)
        return QPixmap.fromImage(final_image)
    def render_preview(self, base_pixmap):
        if not base_pixmap or base_pixmap.isNull(): return
        final_pixmap = None
        if self.template_pixmap:
            stretched_media_pixmap = base_pixmap.scaled(self.template_pixmap.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            edited_media_pixmap = self.apply_effects_to_pixmap(stretched_media_pixmap)
            painter = QPainter(edited_media_pixmap)
            painter.setOpacity(self.transparency_slider.value() / 100.0)
            painter.drawPixmap(0, 0, self.template_pixmap)
            painter.end()
            final_pixmap = edited_media_pixmap
        else: final_pixmap = self.apply_effects_to_pixmap(base_pixmap)
        self.preview_label.setPixmap(final_pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def update_frame(self):
        frame = None
        if self.is_gif:
            if not self.gif_frames: return
            self.frame_pos_counter = (self.frame_pos_counter + 1) % self.total_frames
            frame = self.gif_frames[int(self.frame_pos_counter)]
        elif self.video_capture and self.video_capture.isOpened():
            if self.total_frames > 1:
                frame_increment = self.source_fps / (float(self.target_fps.text()) or self.source_fps)
                self.frame_pos_counter += frame_increment
                if self.frame_pos_counter >= self.total_frames: self.frame_pos_counter = 0
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, int(self.frame_pos_counter))
            ret, cv2_frame = self.video_capture.read()
            if not ret: self.frame_pos_counter = 0; self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0); ret, cv2_frame = self.video_capture.read()
            if not ret: self.timer.stop(); return
            frame = cv2_frame
        if frame is not None:
            h, w, ch = frame.shape
            fmt = QImage.Format_ARGB32 if ch == 4 else QImage.Format_RGB888
            q_img = QImage(frame.data, w, h, ch * w, fmt).rgbSwapped()
            self.render_preview(QPixmap.fromImage(q_img))
    def resize_preview_container(self):
        if self.preview_container.width() > 0:
            aspect_ratio = 9/16
            pixmap_to_check = self.template_pixmap or self.static_image_pixmap
            if pixmap_to_check and not pixmap_to_check.isNull(): aspect_ratio = pixmap_to_check.height() / pixmap_to_check.width()
            self.preview_container.setFixedHeight(int(self.preview_container.width() * aspect_ratio))
    def resizeEvent(self, event): super().resizeEvent(event); self.resize_preview_container(); self.update_preview_from_settings()
    def start_processing(self):
        if not self.validate_inputs(): return
        self.set_controls_enabled(False)
        self.thread = ProcessingThread(media_path=self.media_path.text(), target_fps=self.target_fps.text(), segment_length=self.segment_length.text(), corner_roundness=self.corner_roundness.text(), transparency=self.transparency.text(), is_static_image=(self.input_is_static_image), template_path=self.template_path)
        self.thread.update_progress.connect(self.progress.setValue); self.thread.update_status.connect(self.status_label.setText); self.thread.processing_complete.connect(self.on_processing_complete); self.thread.start()
    def on_processing_complete(self, message):
        (QMessageBox.critical if "error" in message.lower() else QMessageBox.information)(self, "Status", message)
        self.set_controls_enabled(True); self.status_label.setText("Ready"); self.progress.setValue(0)
    def set_controls_enabled(self, enabled):
        widgets = [self.browse_media_button, self.select_template_button, self.media_path, self.corner_roundness, self.transparency, self.process_button]
        for w in widgets: w.setEnabled(enabled)
        is_anim = enabled and (self.is_gif or (self.video_capture is not None and not self.input_is_static_image))
        self.target_fps.setEnabled(is_anim); self.segment_length.setEnabled(is_anim)
        self.transparency_slider.setEnabled(enabled and self.template_pixmap is not None)
    def validate_inputs(self):
        if not self.media_path.text() or not os.path.exists(self.media_path.text()):
            QMessageBox.warning(self, "Input Error", "Please select a valid input media file."); return False
        return True
    def closeEvent(self, event): self.timer.stop(); self.video_capture and self.video_capture.release(); super().closeEvent(event)

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    # Example of running standalone with a specific theme
    # window = VideoProcessingWidget(theme='light')
    window = VideoProcessingWidget(theme='dark')
    window.setWindowTitle('Media Processing Tool')
    window.resize(750, 950)
    window.show()
    sys.exit(app.exec_())