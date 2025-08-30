import os
import sys
import shutil
import importlib
import importlib.util
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QStackedWidget, QMessageBox, QLabel, QSizePolicy, QFileDialog,
    QFrame, QScrollArea
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPalette, QColor, QCursor

class PreviewPopup(QWidget):
    def __init__(self, parent=None, plugin_folder=None):
        super().__init__(parent)
        self.setStyleSheet("""
            PreviewPopup {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
        """)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        
        self.preview_content = QWidget()
        self.preview_layout = QVBoxLayout()
        self.preview_content.setLayout(self.preview_layout)
        
        if plugin_folder:
            main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                      plugin_folder, 
                                      'main.py')
            print(f"Previewing: {main_py_path}")
            if os.path.exists(main_py_path):
                try:
                    spec = importlib.util.spec_from_file_location(
                        f"preview_module_{plugin_folder}",
                        main_py_path
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Specifically look for Main class
                    if hasattr(module, 'Main'):
                        gui_class = getattr(module, 'Main')
                        if issubclass(gui_class, QWidget):
                            preview_instance = gui_class()
                            preview_instance.setFixedHeight(200)
                            self.preview_layout.addWidget(preview_instance)
                    else:
                        self.preview_layout.addWidget(QLabel("No Main class found"))
                except Exception as e:
                    self.preview_layout.addWidget(QLabel(f"Error loading preview: {str(e)}"))
            else:
                self.preview_layout.addWidget(QLabel("No preview available"))
        
        self.layout.addWidget(self.preview_content)

class HoverButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.preview = None
        self.parent_widget = parent
        self.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                padding: 10px;
                font-size: 16px;
                text-align: left;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)

    def enterEvent(self, event):
        parent_layout = self.parent().layout()
        button_index = parent_layout.indexOf(self)
        
        # Clean up any existing preview
        self.cleanup_preview()
        
        # Create new preview
        self.preview = PreviewPopup(self.parent_widget, self.text())
        self.preview.setFixedWidth(self.width())
        parent_layout.insertWidget(button_index + 1, self.preview)

    def leaveEvent(self, event):
        cursor_pos = QCursor.pos()
        if self.preview:
            preview_geo = self.preview.geometry()
            preview_global_geo = self.preview.mapToGlobal(preview_geo.topLeft())
            preview_rect = preview_geo.translated(preview_global_geo)
            
            if not preview_rect.contains(cursor_pos):
                self.cleanup_preview()

    def cleanup_preview(self):
        if self.preview:
            parent_layout = self.parent().layout()
            button_index = parent_layout.indexOf(self)
            next_item = parent_layout.itemAt(button_index + 1)
            if next_item and isinstance(next_item.widget(), PreviewPopup):
                next_item.widget().deleteLater()
                parent_layout.removeItem(next_item)
            self.preview = None

class PluginLoader(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Plugin Loader')

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.header_layout = QHBoxLayout()
        self.layout.addLayout(self.header_layout)

        self.title_label = QLabel("Plugin Loader")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        self.header_layout.addWidget(self.title_label)

        self.header_layout.addStretch()

        self.import_button = QPushButton("⬇️ Import")
        self.import_button.setFixedSize(100, 30)
        self.import_button.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.import_button.clicked.connect(self.import_plugin)
        self.header_layout.addWidget(self.import_button)

        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.setFixedSize(100, 30)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.refresh_button.clicked.connect(self.refresh_plugin_list)
        self.header_layout.addWidget(self.refresh_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.layout.addWidget(self.scroll_area)

        self.stacked_widget = QStackedWidget()
        self.scroll_area.setWidget(self.stacked_widget)

        self.plugins_widget = QWidget()
        self.plugins_view = QVBoxLayout()
        self.plugins_widget.setLayout(self.plugins_view)
        self.stacked_widget.addWidget(self.plugins_widget)

        self.selected_plugins_view = QVBoxLayout()
        self.selected_plugins_widget = QWidget()
        self.selected_plugins_widget.setLayout(self.selected_plugins_view)
        self.stacked_widget.addWidget(self.selected_plugins_widget)

        self.plugin_container = QWidget()
        self.plugin_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.selected_plugins_view.addWidget(self.plugin_container)

        self.load_plugins()

        self.stacked_widget.setCurrentWidget(self.plugins_widget)

    def load_plugins(self):
        while self.plugins_view.count():
            item = self.plugins_view.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        folders = [f for f in os.listdir(current_dir) 
                  if os.path.isdir(os.path.join(current_dir, f)) 
                  and f != '__pycache__' and f != 'Custom_Plugins_PyQt5']

        for folder in folders:
            button = HoverButton(folder, self.plugins_widget)
            button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            button.clicked.connect(lambda _, f=folder: self.load_plugin(f))
            self.plugins_view.addWidget(button)

        self.plugins_view.addStretch()

    def load_plugin(self, folder_name):
        main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                   folder_name, 
                                   'main.py')

        if os.path.exists(main_py_path):
            try:
                # Use importlib for loading the actual plugin
                spec = importlib.util.spec_from_file_location(
                    f"plugin_module_{folder_name}",
                    main_py_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Specifically look for Main class
                if hasattr(module, 'Main'):
                    gui_class = getattr(module, 'Main')
                    if issubclass(gui_class, QWidget):
                        self.gui_instance = gui_class()
                    else:
                        QMessageBox.warning(self, 'Error', 'Main class must be a QWidget subclass')
                        return
                else:
                    QMessageBox.warning(self, 'Error', 'No Main class found in main.py')
                    return

                self.plugin_container.deleteLater()
                self.plugin_container = QWidget()
                self.plugin_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                self.selected_plugins_view.addWidget(self.plugin_container)

                plugin_layout = QVBoxLayout()
                plugin_layout.addWidget(self.gui_instance)
                self.plugin_container.setLayout(plugin_layout)

                self.title_label.hide()
                self.import_button.hide()
                self.refresh_button.hide()
                self.plugins_widget.hide()

                self.stacked_widget.setCurrentWidget(self.selected_plugins_widget)

                self.adjust_gui_size()
            except Exception as e:
                QMessageBox.warning(self, 'Error', f'Error loading plugin: {str(e)}')
        else:
            QMessageBox.warning(self, 'Error', f'main.py not found in folder: {folder_name}')

    def adjust_gui_size(self):
        self.gui_instance.adjustSize()
        self.plugin_container.adjustSize()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.stacked_widget.currentWidget() == self.selected_plugins_widget:
            self.adjust_gui_size()

    def import_plugin(self):
        folder_path = QFileDialog.getExistingDirectory(self, 'Select Plugin Folder')

        if folder_path:
            main_py_path = os.path.join(folder_path, 'main.py')
            if os.path.exists(main_py_path):
                current_dir = os.path.dirname(os.path.abspath(__file__))
                folder_name = os.path.basename(folder_path)
                destination_path = os.path.join(current_dir, folder_name)

                if not os.path.exists(destination_path):
                    shutil.copytree(folder_path, destination_path)
                    self.load_plugins()
                    QMessageBox.information(self, 'Import', f'Plugin "{folder_name}" imported successfully!')
                else:
                    QMessageBox.warning(self, 'Error', f'Folder "{folder_name}" already exists.')
            else:
                QMessageBox.warning(self, 'Error', 'Selected folder does not contain a main.py file.')

    def refresh_plugin_list(self):
        self.load_plugins()
        QMessageBox.information(self, 'Refresh', 'Plugin list refreshed.')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PluginLoader()
    ex.show()
    sys.exit(app.exec_())