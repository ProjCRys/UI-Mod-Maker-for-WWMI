import sys
import re
import subprocess
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QPushButton, QLineEdit, QStackedWidget,
                             QScrollArea, QLabel, QDialog, QFileDialog, QMessageBox,
                             QInputDialog, QComboBox)  # Add QComboBox here
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QFont
import ollama
import tempfile
import os
import importlib.util
import traceback


class StreamWorker(QThread):
    finished = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, prompt, convo, model):
        super().__init__()
        self.prompt = prompt
        self.convo = convo
        self.model = model
        
    def run(self):
        response = ''
        stream = ollama.chat(model=self.model, messages=self.convo, stream=True)
        
        sentence_buffer = ''
        for chunk in stream:
            content = chunk['message']['content']
            response += content
            self.progress.emit(content)
            
            sentence_buffer += content
            sentences = re.split(r'(?<=[.,!?])\s+', sentence_buffer)
            sentence_buffer = sentences[-1] if sentences else ''
            
        self.finished.emit(response)

class CodeContainer(QWidget):
    execute_requested = pyqtSignal(str)  # Add signal for execution
    export_requested = pyqtSignal(str)   # Add signal for export
    
    def __init__(self, code, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        
        # Code display
        self.code_display = QTextEdit()
        self.code_display.setReadOnly(True)
        # UPDATED: Set text color to black
        self.code_display.setStyleSheet("""
            QTextEdit {
                background-color: #ADD8E6; /* Light Blue */
                color: black; /* Ensure text is always black */
                font-family: monospace;
                padding: 10px;
            }
        """)
        self.code_display.setText(code)
        
        # Add editable state
        self.editable = False
        
        # Buttons
        button_layout = QHBoxLayout()
        self.execute_btn = QPushButton("Execute")
        self.edit_btn = QPushButton("Edit")
        self.export_btn = QPushButton("Export")
        
        # Add save button (initially hidden)
        self.save_btn = QPushButton("Save")
        self.save_btn.hide()
        
        # Connect buttons to local methods
        self.execute_btn.clicked.connect(self.execute_code)
        self.export_btn.clicked.connect(self.export_code)
        
        button_layout.addWidget(self.execute_btn)
        button_layout.addWidget(self.edit_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.export_btn)
        
        layout.addWidget(self.code_display)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def toggle_edit_mode(self):
        self.editable = not self.editable
        self.code_display.setReadOnly(not self.editable)
        if self.editable:
            self.edit_btn.hide()
            self.save_btn.show()
            self.execute_btn.hide()
            self.export_btn.hide()
        else:
            self.edit_btn.show()
            self.save_btn.hide()
            self.execute_btn.show()
            self.export_btn.show()

    def execute_code(self):
        code = self.code_display.toPlainText()
        lines = code.splitlines()
        if len(lines) > 0:
            lines = lines[1:]  # Remove first line
        code = '\n'.join(lines)
        self.execute_requested.emit(code)

    def export_code(self):
        code = self.code_display.toPlainText()
        lines = code.splitlines()
        if len(lines) > 0:
            lines = lines[1:]  # Remove first line
        code = '\n'.join(lines)
        self.export_requested.emit(code)

class CodeEditor(QDialog):
    def __init__(self, code, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Code Editor")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        self.editor = QTextEdit()
        self.editor.setText(code)
        # UPDATED: Set text color to black
        self.editor.setStyleSheet("""
            QTextEdit {
                background-color: #ADD8E6; /* Light Blue */
                color: black; /* Ensure text is always black */
                font-family: monospace;
                padding: 10px;
            }
        """)
        
        self.execute_btn = QPushButton("Execute")
        
        layout.addWidget(self.editor)
        layout.addWidget(self.execute_btn)
        
        self.setLayout(layout)
        self.resize(600, 400)

class MessageWidget(QWidget):
    def __init__(self, is_user, content, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout()

        # Profile label with text instead of an image
        profile_label = QLabel("👑" if is_user else "✦")
        profile_label.setFixedSize(40, 40)
        profile_label.setAlignment(Qt.AlignCenter)  # Center the profile text

        # Set font properties for the profile label
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        profile_label.setFont(font)

        # Content layout
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        if is_user:
            label = QLabel(content)
            label.setWordWrap(True)
            content_layout.addWidget(label)
        else:
            # Parse content for code blocks
            parts = content.split('```')
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    if part.strip():
                        label = QLabel(part.strip())
                        label.setWordWrap(True)
                        content_layout.addWidget(label)
                else:  # Code block
                    code_container = CodeContainer(part.strip())
                    content_layout.addWidget(code_container)

        # UPDATED: Changed AI color to neon blue and set all text to black
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {'#FFD1DC' if is_user else '#00BFFF'}; /* Pastel Pink for user, Neon Blue for AI */
                color: black; /* Ensure all text is black */
                border-radius: 5px;
                margin: 5px;
                padding: 10px;
            }}
        """)

        if is_user:
            layout.addLayout(content_layout)
            layout.addWidget(profile_label)
        else:
            layout.addWidget(profile_label)
            layout.addLayout(content_layout)

        self.setLayout(layout)


class Main(QWidget):
    def __init__(self):
        super().__init__()
        self.convo = []
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('Plugin Maker AI')
        self.resize(800, 600)
        
        # Main layout
        layout = QVBoxLayout()
        
        # Header with dropdown for models
        header_layout = QHBoxLayout()
        self.model_dropdown = QComboBox()
        self.model_dropdown.setEditable(True)
        self.model_dropdown.setInsertPolicy(QComboBox.NoInsert)
        self.model_dropdown.setPlaceholderText("Download Model")
        self.model_dropdown.currentTextChanged.connect(self.on_model_selected)
        self.model_dropdown.setMinimumWidth(200)
        self.model_dropdown.setMaximumWidth(400)
        
        # Load models from Ollama
        self.load_models()
        
        # "?" button for help
        help_button = QPushButton("?")
        help_button.clicked.connect(self.open_help)
        
        header_layout.addStretch()
        header_layout.addWidget(self.model_dropdown)
        header_layout.addWidget(help_button)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Stacked widget for screens
        self.stacked_widget = QStackedWidget()
        self.chat_screen = self.create_chat_screen()
        self.code_screen = self.create_code_screen()
        
        self.stacked_widget.addWidget(self.chat_screen)
        self.stacked_widget.addWidget(self.code_screen)
        
        layout.addWidget(self.stacked_widget)
        self.setLayout(layout)
        
    def create_chat_screen(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Messages area
        self.messages_area = QScrollArea()
        self.messages_area.setWidgetResizable(True)
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout()
        self.messages_layout.addStretch()
        self.messages_container.setLayout(self.messages_layout)
        self.messages_area.setWidget(self.messages_container)
        
        # Input area
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.returnPressed.connect(self.send_message)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_box)
        input_layout.addWidget(self.send_button)
        
        layout.addWidget(self.messages_area)
        layout.addLayout(input_layout)
        
        widget.setLayout(layout)
        return widget
        
    def create_code_screen(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Output area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumSize(600, 400)
        
        self.output_container = QWidget()
        self.output_layout = QVBoxLayout()
        self.output_layout.setContentsMargins(0, 0, 0, 0)
        self.output_container.setLayout(self.output_layout)
        
        scroll.setWidget(self.output_container)
        
        # Error container
        self.error_container = QWidget()
        error_layout = QVBoxLayout()
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: red;")
        self.error_label.setWordWrap(True)
        self.copy_error_btn = QPushButton("Copy Error")
        self.copy_error_btn.clicked.connect(self.copy_error)
        error_layout.addWidget(self.error_label)
        error_layout.addWidget(self.copy_error_btn)
        self.error_container.setLayout(error_layout)
        self.error_container.hide()
        
        # Back button
        self.back_button = QPushButton("Back to Chat")
        self.back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        layout.addWidget(scroll)
        layout.addWidget(self.error_container)
        layout.addWidget(self.back_button)
        
        widget.setLayout(layout)
        return widget
    
    def execute_code(self, code):
        self.stacked_widget.setCurrentIndex(1)
        self.error_container.hide()
        
        # Clear previous output
        for i in reversed(range(self.output_layout.count())): 
            widget = self.output_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        
        try:
            # Check if code is HTML
            if code.strip().startswith('<'):
                # Display in web view
                web_view = QWebEngineView()
                web_view.setHtml(code)
                self.output_layout.addWidget(web_view)
                web_view.setMinimumSize(400, 300)
                
            else:
                # Create a temporary module
                with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f:
                    # Add necessary imports
                    imports = """
import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
"""
                    f.write(imports + code)
                    temp_path = f.name

                try:
                    # Import the temporary module
                    spec = importlib.util.spec_from_file_location("temp_module", temp_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Look for widget classes and instances
                    widget = None
                    
                    # First look for a class named 'Main'
                    if hasattr(module, 'Main'):
                        widget = module.Main()
                    else:
                        # Look for any QWidget subclass
                        for name in dir(module):
                            obj = getattr(module, name)
                            if isinstance(obj, type) and issubclass(obj, QWidget) and obj != QWidget:
                                widget = obj()
                                break
                        
                        # If no class found, look for widget instances
                        if widget is None:
                            for name in dir(module):
                                obj = getattr(module, name)
                                if isinstance(obj, QWidget) and not isinstance(obj, type):
                                    widget = obj
                                    break

                    if widget is None:
                        raise Exception("No QWidget class or instance found in the code")

                    # Add widget to output layout
                    widget.setParent(self.output_container)
                    self.output_layout.addWidget(widget)
                    widget.show()
                    
                    # Set minimum size if none specified
                    if widget.size().isEmpty():
                        widget.resize(400, 300)

                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(temp_path)
                    except:
                        pass

        except Exception as e:
            self.error_container.show()
            error_text = f"Error: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.error_label.setText(error_text)
            print(f"Error executing code: {error_text}")
    
    def send_message(self):
        text = self.input_box.text().strip()
        if not text:
            return
            
        # Add user message
        self.add_message(True, text)
        self.input_box.clear()
        
        # Start streaming response
        self.convo.append({'role': 'user', 'content': text})
        self.worker = StreamWorker(text, self.convo, self.current_model)
        self.current_response = ''
        self.current_message = None
        
        # Create empty dialogue box with temporary message
        self.current_message = self.add_message(False, "Thinking")
        
        # Animate the temporary message
        self.animation_index = 0
        self.animation_texts = ["Thinking", "Thinking.", "Thinking..", "Thinking..."]
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_message)
        self.animation_timer.start(500)  # Update every 500 milliseconds
        
        self.worker.progress.connect(self.update_stream)
        self.worker.finished.connect(self.finish_stream)
        self.worker.start()
    
    def add_message(self, is_user, content):
        message = MessageWidget(is_user, content)
        self.messages_layout.insertWidget(self.messages_layout.count() - 1, message)
        QTimer.singleShot(10, self._scroll_to_bottom) # Scroll after widget has been added
        return message

    def _scroll_to_bottom(self):
        self.messages_area.verticalScrollBar().setValue(
            self.messages_area.verticalScrollBar().maximum()
        )
    
    def animate_message(self):
        if self.current_message:
            # Find the index of the current message to replace it
            index = self.messages_layout.indexOf(self.current_message)
            self.current_message.deleteLater()
            
            self.current_message = MessageWidget(False, self.animation_texts[self.animation_index])
            self.messages_layout.insertWidget(index, self.current_message)
            
            self.animation_index = (self.animation_index + 1) % len(self.animation_texts)
    
    def update_stream(self, content):
        self.animation_timer.stop()  # Stop the animation when stream response starts
        self.current_response += content

        if self.current_message:
            index = self.messages_layout.indexOf(self.current_message)
            self.current_message.deleteLater()
            self.current_message = MessageWidget(False, self.current_response)
            self.messages_layout.insertWidget(index, self.current_message)
        else:
             self.current_message = self.add_message(False, self.current_response)
        
        self._scroll_to_bottom()
    
    def finish_stream(self, response):
        self.convo.append({'role': 'assistant', 'content': response})

        # Final update to ensure the last received content is rendered correctly
        if self.current_message:
            index = self.messages_layout.indexOf(self.current_message)
            self.current_message.deleteLater()
            self.current_message = MessageWidget(False, response)
            self.messages_layout.insertWidget(index, self.current_message)

        # Connect execute/export/edit buttons for the final message
        for code_container in self.current_message.findChildren(CodeContainer):
            code_container.execute_requested.connect(self.execute_code)
            code_container.export_requested.connect(self.export_code)
            code_container.edit_btn.clicked.connect(code_container.toggle_edit_mode)
            code_container.save_btn.clicked.connect(code_container.toggle_edit_mode)

        self.current_message = None # Reset for next message
        self._scroll_to_bottom()

    def remove_first_line(self, code):
        # Split the code into lines and remove the first line
        lines = code.splitlines()
        if len(lines) > 0:
            lines = lines[1:]
        # Join the remaining lines back into a single string
        return '\n'.join(lines)
    
    def edit_code(self, code):
        editor = CodeEditor(code, self)
        editor.execute_btn.clicked.connect(
            lambda: self.execute_code(editor.editor.toPlainText())
        )
        editor.show()
    
    def export_code(self, code):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if not folder_path:
            return

        # Prompt the user for a folder name
        folder_name, ok = QInputDialog.getText(self, "Enter Folder Name", "Folder Name:")
        if not ok or not folder_name:
            return

        try:
            # Create folder
            full_path = os.path.join(folder_path, folder_name)
            os.makedirs(full_path, exist_ok=True)

            # Save file
            if code.strip().startswith('<'):
                file_path = os.path.join(full_path, "main.html")
            else:
                file_path = os.path.join(full_path, "main.py")

            with open(file_path, 'w') as f:
                f.write(code)

            QMessageBox.information(self, "Success", f"Code exported to {full_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export code: {str(e)}")
    
    def copy_error(self):
        QApplication.clipboard().setText(self.error_label.text())

    def load_models(self):
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                models = [line.split()[0] for line in lines if not line.startswith("NAME") and "failed" not in line]
                self.model_dropdown.addItems(models)
                if models:
                    self.current_model = models[0]
                else:
                    self.current_model = "Download Model"
            else:
                self.model_dropdown.addItem("Download Model")
                self.current_model = "Download Model"
        except Exception as e:
            self.model_dropdown.addItem("Download Model")
            self.current_model = "Download Model"
            print(f"Error loading models: {str(e)}")

    def on_model_selected(self, model):
        if model == "Download Model":
            self.open_help()
        else:
            self.current_model = model

    def open_help(self):
        import webbrowser
        webbrowser.open("https://ollama.com/library")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())