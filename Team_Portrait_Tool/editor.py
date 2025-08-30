import sys
import os
import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QFileDialog, QSlider, QSpinBox,
                             QMessageBox)
from PyQt5.QtGui import QImage, QPixmap, QCursor
from PyQt5.QtCore import Qt, QTimer, QEvent # Import QEvent
from PIL import Image, ImageEnhance

# --- Configuration ---
TEMPLATE_FILENAME = "templates/team_portrait.png" # Use a constant for the template name

class VideoProcessor(QWidget):
    def __init__(self):
        super().__init__()

        # Load the template image FIRST
        self.template_cv = cv2.imread(TEMPLATE_FILENAME, cv2.IMREAD_UNCHANGED)
        if self.template_cv is None:
            QMessageBox.critical(self, "Error", f"Unable to load {TEMPLATE_FILENAME}. Make sure it's in a 'templates' sub-directory.")
            sys.exit(1)

        # Check if template has alpha channel, if not, add one (needed for overlay)
        if len(self.template_cv.shape) == 2: # Grayscale image
            self.template_cv = cv2.cvtColor(self.template_cv, cv2.COLOR_GRAY2BGRA)
            self.template_cv[:, :, 3] = 255 # Make it opaque
        elif self.template_cv.shape[2] == 3: # BGR image
            # Add fully opaque alpha channel
            self.template_cv = cv2.cvtColor(self.template_cv, cv2.COLOR_BGR2BGRA)
            self.template_cv[:, :, 3] = 255
        elif self.template_cv.shape[2] != 4: # Neither Grayscale, BGR, nor BGRA
            QMessageBox.critical(self, "Error", "Template image must be Grayscale, BGR, or BGRA.")
            sys.exit(1)

        # Create a QPixmap version of the template for initial display
        self.template_pixmap = self._convert_cv_to_pixmap(self.template_cv)
        if self.template_pixmap is None:
             QMessageBox.critical(self, "Error", "Could not convert template to displayable format.")
             sys.exit(1)

        # --- State Variables ---
        self.contrast_value = 1.0
        self.brightness_value = 1.0
        self.saturation_value = 1.0
        self.rotation_value = 0
        self.top_value = 0
        self.bottom_value = 0
        self.left_value = 0
        self.right_value = 0
        self.opacity = 100 # MODIFIED: Default opacity set to 100%
        self.media_path = None
        self.cap = None
        self.frame = None # Holds the *currently displayed* raw frame (image, video frame, gif frame)
        self.is_gif = False
        self.is_image = False
        self.original_image = None # Store the original loaded image
        self.gif_reader = None
        self.gif_frames = []
        self.gif_display_index = 0
        self.gif_duration = 100
        self.loop_enabled = False
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame_display)
        self.last_folder_opened = "" # Store last folder path

        # --- ADDED: State variables for looping logic ---
        self.playing_forward = True
        self.video_frame_index = 0
        self.video_frame_count = 0

        # --- Initialize UI ---
        self.initUI()

        # Display the template initially
        self.display_initial_template()
        self.show()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # --- UI STYLING ---
        dark_style = """
        QWidget {
            background-color: #2b2b2b;
            color: #f0f0f0;
        }
        QPushButton {
            background-color: #3c3f41;
            border: 1px solid #555555;
            padding: 5px 10px;
            border-radius: 4px;
            min-height: 20px;
        }
        QPushButton:hover {
            background-color: #4f5355;
            border: 1px solid #777777;
        }
        QPushButton:pressed {
            background-color: #2a2d2f;
        }
        QPushButton:checked {
            background-color: #007acc;
            color: white;
            border: 1px solid #005c99;
        }
        QPushButton:checked:hover {
            background-color: #008ae6;
        }
        #imageDisplayLabel {
            background-color: #212121;
            border: 1px solid #444444;
            border-radius: 4px;
        }
        QSpinBox {
            background-color: #3c3f41;
            border: 1px solid #555555;
            padding: 4px;
            border-radius: 4px;
        }
        QSpinBox:focus {
            border: 1px solid #007acc;
        }
        QSlider::groove:horizontal {
            border-radius: 3px;
            height: 6px;
            background-color: #3a3a3a;
            border: 1px solid #444;
        }
        QSlider::handle:horizontal {
            background: #00bcd4;
            border: 1px solid #00bcd4;
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QSlider::sub-page:horizontal {
            background: #00838f;
            border-radius: 3px;
            height: 6px;
        }
        QLabel {
            background-color: transparent;
        }
        QMessageBox {
            background-color: #3c3f41;
        }
        """
        self.setStyleSheet(dark_style)


        # --- Top Controls Layout ---
        top_controls_layout = QHBoxLayout()
        top_controls_layout.addStretch(1) # Pushes remaining buttons to the right

        # Loop Toggle Button
        self.loop_button = QPushButton("Loop Disabled")
        self.loop_button.setCheckable(True)
        self.loop_button.toggled.connect(self.toggle_loop)
        top_controls_layout.addWidget(self.loop_button)

        # Save Button
        save_button = QPushButton("Save Processed Media")
        save_button.clicked.connect(self.save_processed_media)
        top_controls_layout.addWidget(save_button)

        layout.addLayout(top_controls_layout)

        # --- Image Display Area (Clickable) ---
        self.image_label = QLabel()
        self.image_label.setObjectName("imageDisplayLabel") # Set object name for styling
        self.image_label.setAlignment(Qt.AlignCenter)
        min_h, min_w = self.template_cv.shape[:2]
        min_h = max(min_h, 300)
        min_w = max(min_w, 400)
        self.image_label.setMinimumSize(min_w, min_h)
        self.image_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.image_label.installEventFilter(self)
        layout.addWidget(self.image_label)


        # --- Cropping Controls ---
        crop_layout = QHBoxLayout()
        crop_layout.addWidget(QLabel("Crop/Pad:"))
        for label_text in ['Top', 'Bottom', 'Left', 'Right']:
            spinbox = QSpinBox()
            spinbox.setRange(-10000, 10000)
            spinbox.setValue(0)
            spinbox.valueChanged.connect(self.update_crop_values)
            setattr(self, f'{label_text.lower()}_spinbox', spinbox)
            crop_layout.addWidget(QLabel(label_text))
            crop_layout.addWidget(spinbox)
        layout.addLayout(crop_layout)

        # --- Adjustment Sliders ---
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Overlay Opacity:"))
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(self.opacity)
        self.opacity_slider.valueChanged.connect(self.update_opacity)
        opacity_layout.addWidget(self.opacity_slider)
        layout.addLayout(opacity_layout)

        self.contrast_slider = self.create_slider(layout, "Contrast", 1, 30, int(self.contrast_value * 10), self.update_contrast)
        self.brightness_slider = self.create_slider(layout, "Brightness", 1, 30, int(self.brightness_value * 10), self.update_brightness)
        self.saturation_slider = self.create_slider(layout, "Saturation", 0, 30, int(self.saturation_value * 10), self.update_saturation)
        self.rotation_slider = self.create_slider(layout, "Rotation (°)", -180, 180, self.rotation_value, self.update_rotation_slider, is_angle=True)

        self.setLayout(layout)
        self.setWindowTitle('Media Processor with Overlay')
        self.resize(max(650, min_w + 50), min_h + 300)


    # --- Event Handling for Clickable Label ---
    def eventFilter(self, source, event):
        """Handles events for watched objects, specifically clicks on image_label."""
        if source is self.image_label and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.select_media() # Trigger file selection on left-click
                return True # Event handled
        # Default processing for other events
        return super().eventFilter(source, event)

    # --- UI Helper Functions ---

    def display_initial_template(self):
        """Displays the loaded template image in the image_label."""
        if self.template_pixmap:
            scaled_pixmap = self.template_pixmap.scaled(self.image_label.size(),
                                                        Qt.KeepAspectRatio,
                                                        Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText("Error: Template not loaded.")

    def create_slider(self, layout, label, min_val, max_val, initial_val, callback, is_angle=False):
        """Helper to create a slider with its label."""
        slider_layout = QHBoxLayout()
        if is_angle:
            initial_display_value = initial_val
            label_format = f"{label}: {initial_display_value}°"
        else:
            initial_display_value = initial_val / 10.0
            label_format = f"{label}: {initial_display_value:.1f}"

        label_widget = QLabel(label_format)
        slider_layout.addWidget(label_widget)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(initial_val)
        slider.label_widget = label_widget
        slider.label_text = label
        slider.is_angle = is_angle

        slider.valueChanged.connect(lambda value, s=slider: self.update_slider_label_and_value(value, s, callback))

        slider_layout.addWidget(slider)
        layout.addLayout(slider_layout)
        return slider

    def update_slider_label_and_value(self, value, slider, callback_func):
        """Updates the slider's label and calls the corresponding update function."""
        if slider.is_angle:
            display_value = value
            slider.label_widget.setText(f"{slider.label_text}: {display_value}°")
            callback_func(value)
        else:
            float_value = value / 10.0
            slider.label_widget.setText(f"{slider.label_text}: {float_value:.1f}")
            callback_func(float_value)

    # --- Core Logic ---

    def update_crop_values(self):
        self.top_value = self.top_spinbox.value()
        self.bottom_value = self.bottom_spinbox.value()
        self.left_value = self.left_spinbox.value()
        self.right_value = self.right_spinbox.value()
        self.update_frame_display()

    def update_opacity(self, value):
        self.opacity = value
        self.update_frame_display()

    def update_contrast(self, value):
        self.contrast_value = value
        self.update_frame_display()

    def update_brightness(self, value):
        self.brightness_value = value
        self.update_frame_display()

    def update_saturation(self, value):
        self.saturation_value = value
        self.update_frame_display()

    def update_rotation_slider(self, value):
        self.rotation_value = value
        self.update_frame_display()

    def select_media(self):
        """Opens the file dialog (using native dialog by default)"""
        # Determine starting directory
        start_dir = self.last_folder_opened if self.last_folder_opened else os.getcwd()

        # Use QFileDialog.getOpenFileName WITHOUT DontUseNativeDialog option.
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Select Media File", start_dir, # Start in last used directory or CWD
            "Media Files (*.mp4 *.avi *.mov *.mkv *.gif *.jpg *.jpeg *.png *.bmp);;All Files (*)"
        )

        if filePath:
            self.last_folder_opened = os.path.dirname(filePath) # Store the folder path
            self.reset_processor() # Clear previous state before loading new
            self.media_path = filePath
            ext = os.path.splitext(self.media_path)[1].lower()

            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                if ext in ['.gif']:
                    self.is_gif = True
                    self.load_gif()
                    if self.gif_frames:
                        frame_duration = self.gif_duration if self.gif_duration > 0 else 33
                        if frame_duration < 20: frame_duration = 33 # Avoid overly fast GIFs
                        self.timer.start(int(frame_duration))
                    else:
                        self.media_path = None
                        self.display_initial_template()

                elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
                    self.is_image = False
                    self.is_gif = False
                    self.cap = cv2.VideoCapture(self.media_path)
                    if not self.cap.isOpened():
                        raise ValueError("Unable to open video file.")

                    # --- MODIFIED: Get video info for looping ---
                    self.video_frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    self.video_frame_index = 0
                    self.playing_forward = True

                    fps = self.cap.get(cv2.CAP_PROP_FPS)
                    if fps <= 0: fps = 30
                    self.timer.start(int(1000 / fps))
                    self.update_frame_display() # Trigger first frame read


                elif ext in ['.jpg', '.jpeg', '.png', '.bmp']:
                    self.is_image = True
                    self.is_gif = False
                    self.original_image = cv2.imread(self.media_path, cv2.IMREAD_COLOR)
                    if self.original_image is None:
                        try:
                             pil_img = Image.open(self.media_path).convert('RGB')
                             self.original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                        except Exception as pil_e:
                             print(f"OpenCV failed, PIL fallback also failed: {pil_e}")
                             raise ValueError(f"Unable to open image file: {filePath}")

                    if self.original_image is not None:
                        self.frame = self.original_image.copy()
                        self.update_frame_display()
                    else:
                         raise ValueError(f"Unable to open image file after attempting fallback: {filePath}")

                else:
                    QMessageBox.warning(self, "Unsupported Format", f"The file format '{ext}' is not supported by this application.")
                    self.media_path = None
                    self.display_initial_template()

            except Exception as e:
                QMessageBox.critical(self, "Error Loading Media", f"Could not load file: {self.media_path}\nError: {str(e)}")
                self.reset_processor()
            finally:
                QApplication.restoreOverrideCursor()


    def reset_processor(self):
        """Resets the state when loading new media, on error, or closing."""
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

        self.frame = None
        self.is_gif = False
        self.is_image = False
        self.original_image = None
        self.gif_frames = []
        self.gif_display_index = 0
        self.gif_duration = 100

        # --- MODIFIED: Reset new looping state variables ---
        self.playing_forward = True
        self.video_frame_index = 0
        self.video_frame_count = 0
        
        self.top_spinbox.setValue(0)
        self.bottom_spinbox.setValue(0)
        self.left_spinbox.setValue(0)
        self.right_spinbox.setValue(0)
        self.opacity_slider.setValue(100) # MODIFIED: Reset opacity to 100%
        self.contrast_slider.setValue(10)
        self.brightness_slider.setValue(10)
        self.saturation_slider.setValue(10)
        self.rotation_slider.setValue(0)

        self.media_path = None # Explicitly clear media path on reset
        self.display_initial_template()

    def load_gif(self):
        """Loads all frames from a GIF using PIL."""
        gif_reader = None
        try:
            gif_reader = Image.open(self.media_path)
            self.gif_frames = []
            total_duration = 0
            frame_count = 0

            is_animated = getattr(gif_reader, 'is_animated', False) and gif_reader.n_frames > 1

            if not is_animated:
                 rgb_frame = np.array(gif_reader.convert('RGB'))
                 bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGB2BGR)
                 self.gif_frames.append(bgr_frame)
                 self.gif_duration = 100
                 self.is_gif = False
                 self.is_image = True
                 self.original_image = bgr_frame
                 self.frame = self.original_image.copy()
                 self.update_frame_display()
                 gif_reader.close()
                 return

            for i in range(gif_reader.n_frames):
                gif_reader.seek(i)
                frame_rgba = gif_reader.copy().convert('RGBA')
                rgb_frame = np.array(frame_rgba)
                bgr_frame = cv2.cvtColor(rgb_frame, cv2.COLOR_RGBA2BGR)
                self.gif_frames.append(bgr_frame)

                try:
                    duration = gif_reader.info.get('duration', 100)
                    if duration <= 10: duration = 100
                    total_duration += duration
                    frame_count += 1
                except Exception:
                    pass

            if frame_count > 0:
                self.gif_duration = total_duration / frame_count
            else:
                self.gif_duration = 100
            
            # --- ADDED: Reset looping state on new GIF load ---
            self.gif_display_index = 0
            self.playing_forward = True


        except Exception as e:
            QMessageBox.critical(self, "GIF Error", f"Error loading GIF frames: {str(e)}")
            self.gif_frames = []
        finally:
            if gif_reader:
                 try: gif_reader.close()
                 except Exception: pass


    def update_frame_display(self):
        """Fetches/calculates the next frame and updates the display label."""
        current_raw_frame = None
        try:
            if self.is_image and self.original_image is not None:
                current_raw_frame = self.original_image.copy()

            # --- MODIFIED: Rewritten GIF looping logic ---
            elif self.is_gif and self.gif_frames:
                num_frames = len(self.gif_frames)
                if num_frames == 0: return
                if num_frames == 1:
                    current_raw_frame = self.gif_frames[0].copy()
                else:
                    # Get the current frame to display
                    current_raw_frame = self.gif_frames[self.gif_display_index].copy()

                    # Determine the next frame's index based on loop mode
                    if self.playing_forward:
                        self.gif_display_index += 1
                        if self.gif_display_index >= num_frames: # Reached the end
                            if self.loop_enabled: # Ping-pong loop
                                self.playing_forward = False
                                self.gif_display_index = num_frames - 2 # Start reversing from the second-to-last frame
                            else: # Simple loop
                                self.gif_display_index = 0 # Go back to the start
                    else: # Playing in reverse
                        self.gif_display_index -= 1
                        # When we get to the frame *before* the first one (i.e., index becomes 0 after showing 1)
                        if self.gif_display_index < 1:
                            self.playing_forward = True
                            self.gif_display_index = 0 # Go back to the start for the next forward cycle

            # --- MODIFIED: Rewritten Video looping logic ---
            elif self.cap and self.cap.isOpened():
                if self.video_frame_count <= 0: return # Can't loop without frame count

                self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.video_frame_index)
                ret, frame = self.cap.read()
                if not ret:
                    self.timer.stop()
                    print("Warning: Could not read video frame, stopping timer.")
                    return

                current_raw_frame = frame

                # Determine the next frame's index based on loop mode
                if self.playing_forward:
                    self.video_frame_index += 1
                    if self.video_frame_index >= self.video_frame_count: # Reached the end
                        if self.loop_enabled: # Ping-pong loop
                            self.playing_forward = False
                            # Clamp index to be safe for short videos
                            self.video_frame_index = max(0, self.video_frame_count - 2)
                        else: # Simple loop
                            self.video_frame_index = 0
                else: # Playing in reverse
                    self.video_frame_index -= 1
                    if self.video_frame_index < 1:
                        self.playing_forward = True
                        self.video_frame_index = 0

            # --- Frame processing and display (unchanged) ---
            if current_raw_frame is not None:
                self.frame = current_raw_frame
                processed_display_frame = self.process_frame_for_display(current_raw_frame)
                q_pixmap = self._convert_cv_to_pixmap(processed_display_frame)
                if q_pixmap:
                    self._display_pixmap(q_pixmap)
                else:
                    print("Warning: Failed to convert processed frame to pixmap.")
                    self.image_label.setText("Display Error")

            elif not self.media_path:
                self.display_initial_template()

        except Exception as e:
            print(f"Error updating frame display: {str(e)}")
            import traceback
            traceback.print_exc()


    def process_frame_for_display(self, input_frame):
        """Applies core processing AND the template overlay for UI display."""
        try:
            processed_core_frame = self.apply_core_processing(input_frame)
            if processed_core_frame is None:
                print("Warning: Core processing failed, returning original frame for display.")
                if len(input_frame.shape) == 2:
                    processed_core_frame = cv2.cvtColor(input_frame, cv2.COLOR_GRAY2BGR)
                elif input_frame.shape[2] == 4:
                     processed_core_frame = cv2.cvtColor(input_frame, cv2.COLOR_BGRA2BGR)
                else:
                     processed_core_frame = input_frame
                if processed_core_frame.shape[:2] != self.template_cv.shape[:2]:
                     target_h, target_w = self.template_cv.shape[:2]
                     processed_core_frame = cv2.resize(processed_core_frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

            if len(processed_core_frame.shape) == 2:
                 processed_core_frame = cv2.cvtColor(processed_core_frame, cv2.COLOR_GRAY2BGR)
            elif processed_core_frame.shape[2] == 4:
                 processed_core_frame = cv2.cvtColor(processed_core_frame, cv2.COLOR_BGRA2BGR)

            template_h, template_w = self.template_cv.shape[:2]
            frame_h, frame_w = processed_core_frame.shape[:2]

            if template_h != frame_h or template_w != frame_w:
                 print(f"Warning: Size mismatch before overlay ({frame_w}x{frame_h} vs {template_w}x{template_h}). Resizing template.")
                 template_resized = cv2.resize(self.template_cv, (frame_w, frame_h))
            else:
                 template_resized = self.template_cv

            overlay_rgb = template_resized[:, :, :3]
            overlay_alpha = (template_resized[:, :, 3] / 255.0) * (self.opacity / 100.0)

            frame_float = processed_core_frame.astype(np.float32) / 255.0
            overlay_rgb_float = overlay_rgb.astype(np.float32) / 255.0
            alpha_expanded = overlay_alpha[:, :, np.newaxis]

            blended_float = frame_float * (1 - alpha_expanded) + overlay_rgb_float * alpha_expanded
            blended_uint8 = (blended_float * 255).clip(0, 255).astype(np.uint8)
            return blended_uint8

        except Exception as e:
            print(f"Error applying display overlay: {str(e)}")
            import traceback
            traceback.print_exc()
            return processed_core_frame if 'processed_core_frame' in locals() else input_frame


    # --- Conversion and Display Helpers ---

    def _convert_cv_to_pixmap(self, cv_img):
        """Converts an OpenCV image (BGR or BGRA) to QPixmap."""
        if cv_img is None: return None
        try:
            img_copy = cv_img.copy()
            height, width = img_copy.shape[:2]
            if len(img_copy.shape) < 3:
                bytes_per_line = width
                q_image = QImage(img_copy.data, width, height, bytes_per_line, QImage.Format_Grayscale8)
            else:
                channel = img_copy.shape[2]
                bytes_per_line = channel * width
                if channel == 4:
                    img_copy = cv2.cvtColor(img_copy, cv2.COLOR_BGRA2RGBA)
                    q_image = QImage(img_copy.data, width, height, bytes_per_line, QImage.Format_RGBA8888)
                elif channel == 3:
                    img_copy = cv2.cvtColor(img_copy, cv2.COLOR_BGR2RGB)
                    q_image = QImage(img_copy.data, width, height, bytes_per_line, QImage.Format_RGB888)
                else:
                    print(f"Warning: Unexpected image channel count {channel}, cannot convert.")
                    return None

            return QPixmap.fromImage(q_image)
        except Exception as e:
            print(f"Error converting CV image to QPixmap: {str(e)}")
            return None

    def _display_pixmap(self, pixmap):
        """Scales and displays a QPixmap in the image_label."""
        if pixmap is None or pixmap.isNull():
             self.display_initial_template()
             return
        try:
             scaled_pixmap = pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
             self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
             print(f"Error displaying pixmap: {str(e)}")
             self.image_label.setText("Display Error")


    # --- Saving Logic ---

    def save_processed_media(self):
        """Saves the currently loaded media with applied core processing (no overlay)."""
        if not self.media_path:
            QMessageBox.warning(self, "Nothing to Save", "Please load a media file first by clicking the display area.")
            return

        base_filename = os.path.basename(self.media_path)
        name, ext = os.path.splitext(base_filename)
        suggested_name = f"{name}{ext}"
        if self.is_gif and self.loop_enabled:
             suggested_name = f"{name}{ext}"

        # --- MODIFICATION START ---
        # Define the target save folder and ensure it exists
        save_folder = "media"
        try:
            os.makedirs(save_folder, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(self, "Folder Creation Error", f"Could not create the '{save_folder}' directory.\nError: {e}")
            return

        # Suggest a filename within the target folder
        full_suggested_path = os.path.join(save_folder, suggested_name)

        # Use native dialog for saving, now defaulting to the 'media' folder
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Processed Media As",
                                                   full_suggested_path,
                                                   f"Media Files (*{ext});;All Files (*)")
        # --- MODIFICATION END ---


        if not save_path: return # User cancelled

        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)

            if self.is_image and self.original_image is not None:
                processed_frame = self.apply_core_processing(self.original_image.copy())
                if processed_frame is not None:
                    success = cv2.imwrite(save_path, processed_frame)
                    if not success: raise IOError(f"Failed to write image to {save_path}")
                else:
                    raise RuntimeError("Processing failed for image.")

            elif self.is_gif and self.gif_frames:
                # --- MODIFIED: Save logic for looped GIFs ---
                initial_frames = []
                print(f"Processing {len(self.gif_frames)} GIF frames for saving...")
                for idx, bgr_frame in enumerate(self.gif_frames):
                    processed_bgr = self.apply_core_processing(bgr_frame.copy())
                    if processed_bgr is None:
                        print(f"Warning: Skipping GIF frame {idx} during save due to processing error.")
                        continue
                    rgb_frame = cv2.cvtColor(processed_bgr, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(rgb_frame)
                    initial_frames.append(pil_img)

                if not initial_frames:
                    raise RuntimeError("No valid processed GIF frames to save.")

                save_frames = initial_frames
                if self.loop_enabled and len(initial_frames) > 2:
                    # Create the reverse sequence, excluding the first and last frames of the original
                    reverse_frames = initial_frames[-2:0:-1]
                    save_frames.extend(reverse_frames)
                    print(f"Added {len(reverse_frames)} frames for ping-pong loop.")

                print(f"Saving {len(save_frames)} processed frames to GIF: {save_path}")
                save_kwargs = {
                    "save_all": True,
                    "append_images": save_frames[1:],
                    "duration": int(self.gif_duration),
                    "loop": 0, # Loop forever in the final GIF file
                    "optimize": False
                }

                save_frames[0].save(save_path, **save_kwargs)


            elif self.cap and self.cap.isOpened():
                # --- Video Saving ---
                fps = self.cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0: fps = 30

                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, first_frame = self.cap.read()
                if not ret: raise RuntimeError("Cannot read first frame of video.")

                processed_first_frame = self.apply_core_processing(first_frame.copy())
                if processed_first_frame is None: raise RuntimeError("Cannot process first frame.")

                height, width = processed_first_frame.shape[:2]

                save_ext = os.path.splitext(save_path)[1].lower()
                if save_ext == '.mp4': fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                elif save_ext == '.avi': fourcc = cv2.VideoWriter_fourcc(*'XVID')
                elif save_ext == '.mov': fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                elif save_ext == '.mkv': fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                else:
                    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                    QMessageBox.warning(self, "Codec Warning", f"Unknown video extension '{save_ext}'. Attempting 'mp4v' codec. Saving might fail if incompatible.")

                print(f"Creating video writer: {save_path}, {fourcc}, {fps}, ({width},{height})")
                out = cv2.VideoWriter(save_path, fourcc, fps, (width, height))
                if not out.isOpened():
                    raise IOError(f"Could not open video writer for path: {save_path}\n"
                                  f"Check codec availability ('{fourcc}'), permissions, and path validity.")

                # --- MODIFIED: Save logic for looped videos ---
                all_processed_frames = []
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                print("Processing all video frames for saving...")
                while True:
                    ret, frame = self.cap.read()
                    if not ret: break
                    processed_frame = self.apply_core_processing(frame.copy())
                    if processed_frame is not None:
                        if processed_frame.shape[0] != height or processed_frame.shape[1] != width:
                            processed_frame = cv2.resize(processed_frame, (width, height))
                        all_processed_frames.append(processed_frame)
                
                final_frames_to_write = all_processed_frames
                if self.loop_enabled and len(all_processed_frames) > 2:
                    reverse_frames = all_processed_frames[-2:0:-1]
                    final_frames_to_write.extend(reverse_frames)
                    print(f"Added {len(reverse_frames)} frames for ping-pong loop.")

                print(f"Writing {len(final_frames_to_write)} frames to video...")
                for frame_to_write in final_frames_to_write:
                    out.write(frame_to_write)

                print(f"Releasing video writer.")
                out.release()
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Reset capture

            else:
                raise RuntimeError("No valid media loaded or state is inconsistent.")

            QMessageBox.information(self, "Save Successful", f"Processed media saved to:\n{save_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error Saving Media", f"Could not save the processed media.\nError: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            QApplication.restoreOverrideCursor()


    def apply_core_processing(self, frame_to_process):
        """
        Applies cropping, resizing, adjustments, and rotation.
        Returns the processed BGR frame, resized to template dimensions.
        Does NOT apply the template overlay itself.
        """
        if frame_to_process is None: return None

        try:
            processed_frame = frame_to_process.copy()

            # 1. Cropping / Padding
            h, w = processed_frame.shape[:2]
            pad_top = max(0, self.top_value)
            pad_bottom = max(0, self.bottom_value)
            pad_left = max(0, self.left_value)
            pad_right = max(0, self.right_value)

            if pad_top > 0 or pad_bottom > 0 or pad_left > 0 or pad_right > 0:
                processed_frame = cv2.copyMakeBorder(processed_frame, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=[0, 0, 0])
                h, w = processed_frame.shape[:2] # Update dimensions

            crop_top = abs(min(0, self.top_value))
            crop_bottom = h - abs(min(0, self.bottom_value))
            crop_left = abs(min(0, self.left_value))
            crop_right = w - abs(min(0, self.right_value))

            if crop_top < crop_bottom and crop_left < crop_right and crop_bottom <= h and crop_right <= w and crop_top >= 0 and crop_left >= 0:
                 processed_frame = processed_frame[crop_top:crop_bottom, crop_left:crop_right]
            elif not (crop_top == 0 and crop_bottom == h and crop_left == 0 and crop_right == w):
                 print(f"Warning: Invalid crop dimensions calculated ({crop_top}:{crop_bottom}, {crop_left}:{crop_right} for size {w}x{h}), skipping crop step.")


            if processed_frame.shape[0] <= 0 or processed_frame.shape[1] <= 0:
                print("Error: Frame dimensions became zero or negative after crop/pad.")
                return None

            # 2. Resize to Template Dimensions
            target_h, target_w = self.template_cv.shape[:2]
            interpolation = cv2.INTER_AREA
            processed_frame = cv2.resize(processed_frame, (target_w, target_h), interpolation=interpolation)


            # 3. Apply Adjustments (using PIL for better quality enhancers)
            if len(processed_frame.shape) == 2:
                processed_frame_bgr = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)
            elif processed_frame.shape[2] == 4:
                processed_frame_bgr = cv2.cvtColor(processed_frame, cv2.COLOR_BGRA2BGR)
            else:
                processed_frame_bgr = processed_frame

            processed_frame_rgb = cv2.cvtColor(processed_frame_bgr, cv2.COLOR_BGR2RGB)
            image_pil = Image.fromarray(processed_frame_rgb)

            needs_contrast = abs(self.contrast_value - 1.0) > 1e-6
            needs_brightness = abs(self.brightness_value - 1.0) > 1e-6
            needs_saturation = abs(self.saturation_value - 1.0) > 1e-6 and image_pil.mode != 'L'

            if needs_contrast:
                 enhancer = ImageEnhance.Contrast(image_pil)
                 image_pil = enhancer.enhance(self.contrast_value)
            if needs_brightness:
                 enhancer = ImageEnhance.Brightness(image_pil)
                 image_pil = enhancer.enhance(self.brightness_value)
            if needs_saturation:
                 enhancer = ImageEnhance.Color(image_pil)
                 image_pil = enhancer.enhance(self.saturation_value)

            if needs_contrast or needs_brightness or needs_saturation:
                 adjusted_rgb = np.array(image_pil)
                 processed_frame = cv2.cvtColor(adjusted_rgb, cv2.COLOR_RGB2BGR)


            # 4. Apply Rotation
            needs_rotation = self.rotation_value != 0
            if needs_rotation:
                if len(processed_frame.shape) == 2:
                     processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_GRAY2BGR)
                elif processed_frame.shape[2] == 4:
                     processed_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGRA2BGR)

                center = (target_w // 2, target_h // 2)
                rotation_matrix = cv2.getRotationMatrix2D(center, self.rotation_value, 1.0)
                processed_frame = cv2.warpAffine(processed_frame, rotation_matrix, (target_w, target_h),
                                                 flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0))

            return processed_frame

        except Exception as e:
            print(f"Error during core processing: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


    # --- Other Methods ---
    def toggle_loop(self, checked):
        self.loop_enabled = checked
        self.loop_button.setText("Loop Enabled" if checked else "Loop Disabled")

    def closeEvent(self, event):
        """Ensure resources are released on closing."""
        print("Closing application and releasing resources...")
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.frame = None
        self.original_image = None
        self.gif_frames = []
        print("Resources released.")
        event.accept()

    def resizeEvent(self, event):
        """Rescale the displayed pixmap when window/label size changes."""
        super().resizeEvent(event)
        current_pixmap = self.image_label.pixmap()
        if current_pixmap and not current_pixmap.isNull():
             self.update_frame_display()
        elif not self.media_path:
             self.display_initial_template()


def main():
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    
    # Create templates directory if it doesn't exist
    if not os.path.exists("templates"):
        os.makedirs("templates")

    if not os.path.exists(TEMPLATE_FILENAME):
         QMessageBox.critical(None, "Startup Error",
                              f"{TEMPLATE_FILENAME} not found!\n"
                              f"Please place your template image inside the 'templates' sub-directory:\n"
                              f"{os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')}")
         sys.exit(1)

    ex = VideoProcessor()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()