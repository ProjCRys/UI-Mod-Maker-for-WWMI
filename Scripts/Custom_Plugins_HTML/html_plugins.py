import os
import sys
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QScrollArea, QFrame, QMainWindow, QStatusBar,
    QHBoxLayout, QSizePolicy, QFileDialog, QMessageBox
)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QDir, QUrl, Qt, QTimer
from PyQt5.QtGui import QIcon

class PreviewWebView(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(400)
        self.setFixedHeight(600)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QWebEngineView {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
        """)
        
    def enterEvent(self, event):
        if hasattr(self, 'parent_button'):
            self.parent_button.set_preview_active(True)
            
    def leaveEvent(self, event):
        if hasattr(self, 'parent_button'):
            self.parent_button.set_preview_active(False)
            QTimer.singleShot(100, self.parent_button.check_preview_state)

class PluginButton(QPushButton):
    def __init__(self, text, html_path, parent=None):
        super().__init__(text, parent)
        self.html_path = html_path
        self.preview = None
        self.preview_active = False
        self.button_active = False
        self.hide_timer = None

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
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
        
    def create_preview(self):
        if not self.preview:
            self.preview = PreviewWebView()
            self.preview.parent_button = self
            url = QUrl.fromLocalFile(os.path.abspath(self.html_path))
            self.preview.setUrl(url)
        return self.preview
        
    def set_preview_active(self, active):
        self.preview_active = active
        
    def set_button_active(self, active):
        self.button_active = active
        
    def check_preview_state(self):
        if not (self.preview_active or self.button_active):
            if self.hide_timer:
                self.hide_timer.stop()
            self.hide_timer = QTimer()
            self.hide_timer.setSingleShot(True)
            self.hide_timer.timeout.connect(self.hide_preview)
            self.hide_timer.start(200)
            
    def hide_preview(self):
        if not (self.preview_active or self.button_active) and hasattr(self, 'main_window'):
            self.main_window.remove_current_preview()
            self.preview = None

class HTMLPluginApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Plugin Loader')
        self.initUI()

    def initUI(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
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
        self.refresh_button.clicked.connect(self.refresh_plugins)
        self.header_layout.addWidget(self.refresh_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.layout.addWidget(self.scroll_area)

        self.plugins_widget = QWidget()
        self.plugins_view = QVBoxLayout(self.plugins_widget)
        self.plugins_view.setSpacing(5)
        self.plugins_view.setContentsMargins(10, 10, 10, 10)
        self.scroll_area.setWidget(self.plugins_widget)

        self.current_preview = None
        self.current_button = None
        
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        
        self.refresh_plugins()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.current_preview:
            self.current_preview.setFixedWidth(self.plugins_widget.width() - 20)

    def import_plugin(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Plugin Folder",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        
        if folder_path:
            main_html_path = os.path.join(folder_path, "main.html")
            if os.path.exists(main_html_path):
                current_dir = os.path.dirname(os.path.abspath(__file__))
                folder_name = os.path.basename(folder_path)
                destination_path = os.path.join(current_dir, "Custom_Plugins_HTML", folder_name)

                if not os.path.exists(destination_path):
                    shutil.copytree(folder_path, destination_path)
                    self.refresh_plugins()
                    QMessageBox.information(self, 'Import', f'Plugin "{folder_name}" imported successfully!')
                else:
                    QMessageBox.warning(self, 'Error', f'Folder "{folder_name}" already exists.')
            else:
                QMessageBox.warning(self, 'Error', 'Selected folder does not contain a main.html file.')

    def remove_current_preview(self):
        if self.current_preview:
            self.current_preview.hide()
            self.current_preview.setParent(None)
            self.current_preview = None
        if self.current_button:
            self.current_button = None

    def show_preview(self, button):
        if self.current_preview and self.current_button == button:
            return
            
        self.remove_current_preview()
        
        self.current_preview = button.create_preview()
        self.current_button = button

        self.current_preview.setFixedWidth(self.plugins_widget.width() - 20)

        button_index = self.plugins_view.indexOf(button)
        if button_index != -1:
            self.plugins_view.insertWidget(button_index + 1, self.current_preview)

        button.set_preview_active(True)
        self.current_preview.show()

    def refresh_plugins(self):
        for i in reversed(range(self.plugins_view.count())):
            widget = self.plugins_view.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.remove_current_preview()

        plugins_dir = QDir("Custom_Plugins_HTML")
        if not plugins_dir.exists():
            plugins_dir.mkpath(".")

        plugins = []
        for folder_name in plugins_dir.entryList(QDir.Dirs | QDir.NoDotAndDotDot):
            html_path = os.path.join(plugins_dir.path(), folder_name, "main.html")
            if os.path.isfile(html_path):
                plugins.append((folder_name, html_path))

        for folder_name, html_path in plugins:
            button = PluginButton(folder_name, html_path)
            button.main_window = self
            button.clicked.connect(lambda checked, path=html_path: self.open_html(path))
            button.enterEvent = lambda e, btn=button: self.handle_button_enter(btn)
            button.leaveEvent = lambda e, btn=button: self.handle_button_leave(btn)
            self.plugins_view.addWidget(button)

        self.plugins_view.addStretch()
        self.statusBar.showMessage(f"Found {len(plugins)} plugins")

    def handle_button_enter(self, button):
        button.set_button_active(True)
        self.show_preview(button)

    def handle_button_leave(self, button):
        button.set_button_active(False)
        QTimer.singleShot(100, button.check_preview_state)

    def open_html(self, path):
        # Remove all widgets from the central layout
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.web_view = QWebEngineView()
        url = QUrl.fromLocalFile(os.path.abspath(path))
        self.web_view.setUrl(url)
        self.layout.addWidget(self.web_view)
        
        self.statusBar.showMessage(f"Loaded: {path}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = HTMLPluginApp()
    window.resize(1024, 768)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()