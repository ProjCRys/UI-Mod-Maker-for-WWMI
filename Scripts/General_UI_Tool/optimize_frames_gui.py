import sys
import os
import shutil
import subprocess
import threading
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, 
                            QPushButton, QProgressBar, QFileDialog, QLabel, 
                            QSpinBox, QFrame, QHBoxLayout, QMainWindow, QComboBox,
                            QStackedWidget, QRadioButton, QButtonGroup, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QPalette, QColor, QFont
from PIL import Image

class SignalHandler(QObject):
    progress_update = pyqtSignal(int, int)
    process_complete = pyqtSignal(int)

class ProcessingWidget(QMainWindow):
    def __init__(self):
        super().__init__()
        self.signal_handler = SignalHandler()
        self.init_ui()
        self.running = False
        self.setWindowTitle("Image Processor")
        self.setMinimumWidth(500)

    def init_ui(self):
        # Styling has been updated to remove hardcoded text colors.
        # This allows the text color to be inherited from the system's
        # color palette, making it compatible with light and dark modes.
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f2f5;
            }
            /* The global 'color' property has been removed from QWidget
               to allow palette inheritance. */
            QLabel {
                font-size: 13px;
                /* 'color' removed to use default system text color */
                padding: 5px 0;
                font-weight: 500;
            }
            QPushButton {
                background-color: #4299e1;
                color: white; /* Button text color kept for contrast */
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: #3182ce;
            }
            QPushButton:disabled {
                background-color: #a0aec0;
                opacity: 0.65;
            }
            QPushButton#folder-btn {
                background-color: #718096;
            }
            QPushButton#folder-btn:hover {
                background-color: #4a5568;
            }
            QProgressBar {
                border: none;
                border-radius: 8px;
                background-color: #e2e8f0;
                text-align: center;
                height: 16px;
                margin: 8px 0;
            }
            QProgressBar::chunk {
                background-color: #48bb78;
                border-radius: 8px;
            }
            QFrame#separator {
                background-color: #cbd5e0;
                max-height: 1px;
                margin: 15px 0;
            }
            QSpinBox {
                padding: 8px;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                background-color: white;
                min-width: 100px;
                /* 'color' removed to use default system text color */
            }
            QSpinBox:focus {
                border-color: #63b3ed;
                outline: 0;
            }
            QComboBox {
                padding: 8px;
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                background-color: white;
                min-width: 100px;
                /* 'color' removed to use default system text color */
            }
            QComboBox:focus {
                border-color: #63b3ed;
                outline: 0;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #4a5568;
                margin-right: 8px;
            }
            QRadioButton {
                font-size: 14px;
                /* 'color' removed to use default system text color */
                padding: 5px;
            }
            QRadioButton::indicator {
                width: 15px;
                height: 15px;
            }
        """)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # Header section
        header_label = QLabel("Frame Optimizing Tool")
        header_label.setStyleSheet("""
            font-size: 24px;
            /* 'color' removed to use default system text color */
            font-weight: bold;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(header_label)

        # Mode selection
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup()
        combined_mode = QRadioButton("Combined Mode")
        manual_mode = QRadioButton("Manual Mode")
        combined_mode.setChecked(True)
        self.mode_group.addButton(combined_mode, 0)
        self.mode_group.addButton(manual_mode, 1)
        mode_layout.addWidget(combined_mode)
        mode_layout.addWidget(manual_mode)
        mode_layout.addStretch()
        main_layout.addLayout(mode_layout)

        # Create stacked widget for different modes
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create combined mode widget
        combined_widget = QWidget()
        combined_layout = QVBoxLayout(combined_widget)
        self.setup_combined_mode(combined_layout)
        self.stacked_widget.addWidget(combined_widget)

        # Create manual mode widget
        manual_widget = QWidget()
        manual_layout = QVBoxLayout(manual_widget)
        self.setup_manual_mode(manual_layout)
        self.stacked_widget.addWidget(manual_widget)

        # Connect mode selection
        self.mode_group.buttonClicked.connect(self.change_mode)

        # Connect signals
        self.folder_combo.currentIndexChanged.connect(self.select_folder)
        self.folder_combo.activated.connect(self.refresh_folder_dropdown)
        self.scale_spin.valueChanged.connect(self.update_estimated_dimensions)
        self.start_btn.clicked.connect(self.start_processing)
        self.signal_handler.progress_update.connect(self.update_progress)
        self.signal_handler.process_complete.connect(self.process_completed)

        # Manual mode connections
        self.manual_folder_combo.currentIndexChanged.connect(self.select_manual_folder)
        self.manual_folder_combo.activated.connect(self.refresh_folder_dropdown)
        self.manual_scale_spin.valueChanged.connect(self.update_manual_estimated_dimensions)
        self.scale_btn.clicked.connect(self.start_scaling)
        self.convert_btn.clicked.connect(self.start_converting)

        # Populate the folder dropdowns
        self.populate_folder_dropdown()

    def setup_combined_mode(self, layout):
        # Folder selection section
        folder_section = QVBoxLayout()
        self.folder_combo = QComboBox()
        self.folder_combo.setPlaceholderText('No folder selected')
        self.folder_combo.setObjectName('folder-combo')
        self.folder_label = QLabel('No folder selected')
        # Contextual color is kept for status indication
        self.folder_label.setStyleSheet("color: #718096;")
        folder_section.addWidget(self.folder_combo)
        folder_section.addWidget(self.folder_label)
        layout.addLayout(folder_section)

        self.add_separator(layout)

        # Settings section
        settings_label = QLabel("Processing Settings")
        settings_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(settings_label)

        # Step 1: Scaling
        step_1_label = QLabel("Step 1: Scaling")
        step_1_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(step_1_label)

        # Scale factor selection
        scale_layout = QHBoxLayout()
        scale_label = QLabel('Scale Percentage:')
        self.scale_spin = QSpinBox()
        self.scale_spin.setRange(1, 1000)
        self.scale_spin.setValue(100)
        self.scale_spin.setSuffix('%')
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.scale_spin)
        scale_layout.addStretch()
        layout.addLayout(scale_layout)

        # Estimated dimensions display
        self.dimensions_label = QLabel('Estimated Dimensions: -')
        # Contextual color is kept for de-emphasized info text
        self.dimensions_label.setStyleSheet("color: #4a5568;")
        layout.addWidget(self.dimensions_label)

        # Batch size selection
        batch_layout = QHBoxLayout()
        batch_label = QLabel('Images per Batch:')
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 10000)
        self.batch_spin.setValue(10)
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.batch_spin)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        self.add_separator(layout)

        # Step 2: DDS Conversion
        step_2_label = QLabel("Step 2: DDS Conversion")
        step_2_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(step_2_label)

        # GPU ID selection
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel('GPU ID:')
        self.gpu_spin = QSpinBox()
        self.gpu_spin.setRange(0, 10)  # Adjust the range as needed
        self.gpu_spin.setValue(0)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addWidget(self.gpu_spin)
        gpu_layout.addStretch()
        layout.addLayout(gpu_layout)

        # GPU ID instructions
        gpu_instructions_label = QLabel('Open Task Manager > Performance Tab > GPU to find the GPU ID')
        # Contextual color is kept for de-emphasized info text
        gpu_instructions_label.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(gpu_instructions_label)

        self.add_separator(layout)

        # Progress section
        progress_label = QLabel("Processing Progress")
        progress_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(progress_label)

        # Progress bars
        self.progress_1 = QProgressBar()
        self.progress_1.setFormat('Scaling Progress: %p%')
        self.progress_2 = QProgressBar()
        self.progress_2.setFormat('Conversion Progress: %p%')
        layout.addWidget(self.progress_1)
        layout.addWidget(self.progress_2)

        # Start button
        self.start_btn = QPushButton('Start Processing')
        self.start_btn.setEnabled(False)
        layout.addWidget(self.start_btn, alignment=Qt.AlignCenter)

        layout.addStretch()

    def setup_manual_mode(self, layout):
        # Folder selection section
        folder_section = QVBoxLayout()
        self.manual_folder_combo = QComboBox()
        self.manual_folder_combo.setPlaceholderText('No folder selected')
        self.manual_folder_combo.setObjectName('folder-combo')
        self.manual_folder_label = QLabel('No folder selected')
        # Contextual color is kept for status indication
        self.manual_folder_label.setStyleSheet("color: #718096;")
        folder_section.addWidget(self.manual_folder_combo)
        folder_section.addWidget(self.manual_folder_label)
        layout.addLayout(folder_section)

        self.add_separator(layout)

        # Settings section
        settings_label = QLabel("Processing Settings")
        settings_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(settings_label)

        # Step 1: Scaling
        step_1_label = QLabel("Step 1: Scaling")
        step_1_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(step_1_label)

        # Scale factor selection
        scale_layout = QHBoxLayout()
        scale_label = QLabel('Scale Percentage:')
        self.manual_scale_spin = QSpinBox()
        self.manual_scale_spin.setRange(1, 1000)
        self.manual_scale_spin.setValue(100)
        self.manual_scale_spin.setSuffix('%')
        scale_layout.addWidget(scale_label)
        scale_layout.addWidget(self.manual_scale_spin)
        scale_layout.addStretch()
        layout.addLayout(scale_layout)

        # Estimated dimensions display
        self.manual_dimensions_label = QLabel('Estimated Dimensions: -')
        # Contextual color is kept for de-emphasized info text
        self.manual_dimensions_label.setStyleSheet("color: #4a5568;")
        layout.addWidget(self.manual_dimensions_label)

        # Batch size selection
        batch_layout = QHBoxLayout()
        batch_label = QLabel('Images per Batch:')
        self.manual_batch_spin = QSpinBox()
        self.manual_batch_spin.setRange(1, 10000)
        self.manual_batch_spin.setValue(10)
        batch_layout.addWidget(batch_label)
        batch_layout.addWidget(self.manual_batch_spin)
        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        self.add_separator(layout)

        # Step 2: DDS Conversion
        step_2_label = QLabel("Step 2: DDS Conversion")
        step_2_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(step_2_label)

        # GPU ID selection
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel('GPU ID:')
        self.manual_gpu_spin = QSpinBox()
        self.manual_gpu_spin.setRange(0, 10)  # Adjust the range as needed
        self.manual_gpu_spin.setValue(0)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addWidget(self.manual_gpu_spin)
        gpu_layout.addStretch()
        layout.addLayout(gpu_layout)

        # GPU ID instructions
        gpu_instructions_label = QLabel('Open Task Manager > Performance Tab > GPU to find the GPU ID')
        # Contextual color is kept for de-emphasized info text
        gpu_instructions_label.setStyleSheet("color: #718096; font-size: 12px;")
        layout.addWidget(gpu_instructions_label)

        self.add_separator(layout)

        # Progress section
        progress_label = QLabel("Processing Progress")
        progress_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            margin-top: 10px;
            /* 'color' removed to use default system text color */
        """)
        layout.addWidget(progress_label)

        # Progress bars
        self.manual_progress_1 = QProgressBar()
        self.manual_progress_1.setFormat('Scaling Progress: %p%')
        self.manual_progress_2 = QProgressBar()
        self.manual_progress_2.setFormat('Conversion Progress: %p%')
        layout.addWidget(self.manual_progress_1)
        layout.addWidget(self.manual_progress_2)

        # Buttons
        button_layout = QHBoxLayout()
        self.scale_btn = QPushButton('Scale Images')
        self.convert_btn = QPushButton('Convert to DDS')
        self.scale_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        button_layout.addWidget(self.scale_btn)
        button_layout.addWidget(self.convert_btn)
        layout.addLayout(button_layout)

        layout.addStretch()

    def change_mode(self, button):
        self.stacked_widget.setCurrentIndex(self.mode_group.id(button))

    def add_separator(self, layout):
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName('separator')
        layout.addWidget(separator)

    def populate_folder_dropdown(self):
        extracted_frames_path = "extracted_frames"
        if os.path.exists(extracted_frames_path):
            folders = [f for f in os.listdir(extracted_frames_path) if os.path.isdir(os.path.join(extracted_frames_path, f))]
            if folders:
                current_folder = self.folder_combo.currentText()
                current_manual_folder = self.manual_folder_combo.currentText()

                self.folder_combo.clear()
                self.manual_folder_combo.clear()
                self.folder_combo.addItem("Import Frame Folder...")
                self.manual_folder_combo.addItem("Import Frame Folder...")
                self.folder_combo.addItems(folders)
                self.manual_folder_combo.addItems(folders)

                # Restore the current selection if it exists in the new list
                if current_folder in folders:
                    self.folder_combo.setCurrentText(current_folder)
                if current_manual_folder in folders:
                    self.manual_folder_combo.setCurrentText(current_manual_folder)
            else:
                self.folder_combo.clear()
                self.manual_folder_combo.clear()
                self.folder_combo.addItem('No folder selected')
                self.manual_folder_combo.addItem('No folder selected')
        else:
            self.folder_combo.clear()
            self.manual_folder_combo.clear()
            self.folder_combo.addItem('No folder selected')
            self.manual_folder_combo.addItem('No folder selected')

    def refresh_folder_dropdown(self):
        self.populate_folder_dropdown()

    def select_folder(self):
        selected_folder = self.folder_combo.currentText()
        if selected_folder == "Import Frame Folder...":
            self.import_frame_folder()
        elif len(selected_folder) == 0:
            self.input_folder = None
            self.folder_label.setText('No folder selected')
            self.folder_label.setStyleSheet("color: #718096;")
            self.start_btn.setEnabled(False)
            self.dimensions_label.setText('Estimated Dimensions: -')
        else:
            self.input_folder = os.path.join("extracted_frames", selected_folder)
            self.folder_label.setText(f'Selected: {selected_folder}')
            self.folder_label.setStyleSheet("color: #48bb78; font-weight: 500;")
            self.start_btn.setEnabled(True)
            self.update_estimated_dimensions()

            # Print the selected folder path for debugging
            print(f"Selected folder path: {self.input_folder}")

            # Create scaled-output and dds folders
            scaled_output_path = os.path.join(self.input_folder, 'scaled-output')
            dds_output_path = os.path.join(self.input_folder, 'dds')
            os.makedirs(scaled_output_path, exist_ok=True)
            os.makedirs(dds_output_path, exist_ok=True)

            # Print the created folder paths for debugging
            print(f"Created scaled-output folder: {scaled_output_path}")
            print(f"Created dds folder: {dds_output_path}")

    def select_manual_folder(self):
        selected_folder = self.manual_folder_combo.currentText()
        if selected_folder == "Import Frame Folder...":
            self.import_frame_folder()
        elif len(selected_folder) == 0:
            self.manual_input_folder = None
            self.manual_folder_label.setText('No folder selected')
            self.manual_folder_label.setStyleSheet("color: #718096;")
            self.scale_btn.setEnabled(False)
            self.convert_btn.setEnabled(False)
            self.manual_dimensions_label.setText('Estimated Dimensions: -')
        else:   
            self.manual_input_folder = os.path.join("extracted_frames", selected_folder)
            self.manual_folder_label.setText(f'Selected: {selected_folder}')
            self.manual_folder_label.setStyleSheet("color: #48bb78; font-weight: 500;")
            self.scale_btn.setEnabled(True)
            self.convert_btn.setEnabled(True)
            self.update_manual_estimated_dimensions()

            # Print the selected folder path for debugging
            print(f"Selected manual folder path: {self.manual_input_folder}")

            # Create scaled-output and dds folders
            scaled_output_path = os.path.join(self.manual_input_folder, 'scaled-output')
            dds_output_path = os.path.join(self.manual_input_folder, 'dds')
            os.makedirs(scaled_output_path, exist_ok=True)
            os.makedirs(dds_output_path, exist_ok=True)

            # Print the created folder paths for debugging
            print(f"Created scaled-output folder: {scaled_output_path}")
            print(f"Created dds folder: {dds_output_path}")

    def import_frame_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Frame Folder")
        if folder_path:
            # Validate the folder
            if self.validate_frame_folder(folder_path):
                # Copy the valid contents to the extracted_frames directory
                new_folder_name = os.path.basename(folder_path)
                new_folder_path = os.path.join("extracted_frames", new_folder_name)
                os.makedirs(new_folder_path, exist_ok=True)
                for file in os.listdir(folder_path):
                    if self.is_valid_image_file(file):
                        shutil.copy(os.path.join(folder_path, file), new_folder_path)

                # Refresh the folder dropdown
                self.refresh_folder_dropdown()
            else:
                # Show an error message if the folder is invalid
                QMessageBox.warning(self, "Invalid Folder", "The selected folder does not contain numerically named images.")

    def validate_frame_folder(self, folder_path):
        # Check if the folder contains images named numerically
        files = os.listdir(folder_path)
        for file in files:
            if self.is_valid_image_file(file):
                try:
                    int(file.split('.')[0])
                except ValueError:
                    return False
        return True

    def is_valid_image_file(self, file):
        valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
        return file.lower().endswith(valid_extensions)

    def count_files(self, folder, extensions=None):
        count = 0
        for root, _, files in os.walk(folder):
            if extensions:
                count += sum(1 for f in files if any(f.lower().endswith(ext) for ext in extensions))
            else:
                count += len(files)
        return count

    def update_progress(self, step, progress):
        if self.stacked_widget.currentIndex() == 0:
            if step == 1:
                self.progress_1.setValue(progress)
            else:
                self.progress_2.setValue(progress)
        else:
            if step == 1:
                self.manual_progress_1.setValue(progress)
            else:
                self.manual_progress_2.setValue(progress)

    def process_completed(self, step):
        if self.stacked_widget.currentIndex() == 0:
            if step == 1:
                self.progress_1.setValue(100)
            else:
                self.progress_2.setValue(100)
                self.start_btn.setEnabled(True)
                self.running = False
        else:
            if step == 1:
                self.manual_progress_1.setValue(100)
                self.convert_btn.setEnabled(True)
                self.scale_btn.setEnabled(True)
            else:
                self.manual_progress_2.setValue(100)
                self.convert_btn.setEnabled(True)
                self.scale_btn.setEnabled(True)

    def run_processing(self):
        scaled_output = os.path.join(self.input_folder, 'scaled-output')
        dds_output = os.path.join(self.input_folder, 'dds')

        os.makedirs(scaled_output, exist_ok=True)
        os.makedirs(dds_output, exist_ok=True)

        scale_factor = self.scale_spin.value() / 100.0
        total_files = self.count_files(self.input_folder)
        processed_files = 0

        process = subprocess.Popen([
            'python', 'General_UI_Tool/scale.py',
            self.input_folder,
            str(scale_factor),
            str(self.batch_spin.value())
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                processed_files += 1
                progress_percentage = int((processed_files / total_files) * 100)
                self.signal_handler.progress_update.emit(1, progress_percentage)

        process.wait()
        self.signal_handler.process_complete.emit(1)

        total_conversion_files = self.count_files(scaled_output)
        converted_files = 0

        process = subprocess.Popen([
            'python', 'General_UI_Tool/dds-converter.py',
            scaled_output,
            dds_output, 
            "--gpu", str(self.gpu_spin.value())
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                output_str = output.decode('utf-8', errors='ignore')
                if "writing" in output_str:
                    converted_files += 1
                    conversion_progress_percentage = int((converted_files / total_conversion_files) * 100)
                    self.signal_handler.progress_update.emit(2, conversion_progress_percentage)
                    print(f"Debug: {output_str.strip()}")  # Print the line for debugging

        process.wait()
        self.signal_handler.process_complete.emit(2)

    def run_manual_scaling(self):
        scaled_output = os.path.join(self.manual_input_folder, 'scaled-output')
        os.makedirs(scaled_output, exist_ok=True)

        scale_factor = self.manual_scale_spin.value() / 100.0
        total_files = self.count_files(self.manual_input_folder)
        processed_files = 0

        process = subprocess.Popen([
            'python', 'General_UI_Tool/scale.py',
            self.manual_input_folder,
            str(scale_factor),
            str(self.manual_batch_spin.value())
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                processed_files += 1
                progress_percentage = int((processed_files / total_files) * 100)
                self.signal_handler.progress_update.emit(1, progress_percentage)

        process.wait()
        self.signal_handler.process_complete.emit(1)

    def run_manual_converting(self):
        scaled_output = os.path.join(self.manual_input_folder, 'scaled-output')
        dds_output = os.path.join(self.manual_input_folder, 'dds')
        os.makedirs(dds_output, exist_ok=True)

        total_files = self.count_files(scaled_output)
        converted_files = 0

        process = subprocess.Popen([
            'python', 'General_UI_Tool/dds-converter.py',
            scaled_output,
            dds_output, 
            "--gpu", str(self.manual_gpu_spin.value())
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        while True:
            output = process.stdout.readline()
            if output == b'' and process.poll() is not None:
                break
            if output:
                output_str = output.decode('utf-8', errors='ignore')
                if "writing" in output_str:
                    converted_files += 1
                    progress_percentage = int((converted_files / total_files) * 100)
                    self.signal_handler.progress_update.emit(2, progress_percentage)
                    print(f"Debug: {output_str.strip()}")  # Print the line for debugging

        process.wait()
        self.signal_handler.process_complete.emit(2)

    def start_processing(self):
        if not self.running:
            self.running = True
            self.start_btn.setEnabled(False)
            self.progress_1.setValue(0)
            self.progress_2.setValue(0)
            
            processing_thread = threading.Thread(target=self.run_processing)
            processing_thread.daemon = True
            processing_thread.start()

    def start_scaling(self):
        self.scale_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        self.manual_progress_1.setValue(0)
        
        processing_thread = threading.Thread(target=self.run_manual_scaling)
        processing_thread.daemon = True
        processing_thread.start()

    def start_converting(self):
        self.scale_btn.setEnabled(False)
        self.convert_btn.setEnabled(False)
        self.manual_progress_2.setValue(0)
        
        processing_thread = threading.Thread(target=self.run_manual_converting)
        processing_thread.daemon = True
        processing_thread.start()

    def update_estimated_dimensions(self):
        if hasattr(self, 'input_folder'):
            image_files = [f for f in os.listdir(self.input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
            if image_files:
                first_image_path = os.path.join(self.input_folder, image_files[0])
                with Image.open(first_image_path) as img:
                    original_width, original_height = img.size
                    scale_factor = self.scale_spin.value() / 100.0
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)
                    self.dimensions_label.setText(f'Estimated Dimensions: {new_width}x{new_height}')
            else:
                self.dimensions_label.setText('Estimated Dimensions: -')

    def update_manual_estimated_dimensions(self):
        if hasattr(self, 'manual_input_folder'):
            image_files = [f for f in os.listdir(self.manual_input_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
            if image_files:
                first_image_path = os.path.join(self.manual_input_folder, image_files[0])
                with Image.open(first_image_path) as img:
                    original_width, original_height = img.size
                    scale_factor = self.manual_scale_spin.value() / 100.0
                    new_width = int(original_width * scale_factor)
                    new_height = int(original_height * scale_factor)
                    self.manual_dimensions_label.setText(f'Estimated Dimensions: {new_width}x{new_height}')
            else:
                self.manual_dimensions_label.setText('Estimated Dimensions: -')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ProcessingWidget()
    window.show()
    sys.exit(app.exec_())