# main.py
import sys
import os
import json
import webbrowser
import multiprocessing
# --- MODIFICATION: Added imports for the new update functionality ---
import shutil
import zipfile
import urllib.request
from datetime import datetime

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QPushButton, QVBoxLayout, QFrame, QScrollArea,
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
                             QStackedWidget, QMessageBox, QSizePolicy, QDialog,
                             QFileDialog, QGridLayout, QShortcut)
from PyQt5.QtCore import (Qt, QUrl, QThread, pyqtSignal, QTimer, QPropertyAnimation,
                          QEasingCurve, QAbstractAnimation, QRect, QSize)
from PyQt5.QtGui import QColor, QPainter, QIcon, QPixmap, QKeySequence
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt5.QtWebEngineWidgets import (QWebEngineView, QWebEngineProfile, QWebEngineDownloadItem, QWebEnginePage,
                                      QWebEngineSettings)
from Team_Portrait_Tool.editor import VideoProcessor
from Team_Portrait_Tool.ini_maker import IniMakerWidget
from General_UI_Tool.video_processing_gui import VideoProcessingWidget
from General_UI_Tool.optimize_frames_gui import ProcessingWidget
from General_UI_Tool.ini_maker_v2_gui import AnimationWidget
from Custom_Plugins_HTML.html_plugins import HTMLPluginApp
from Custom_Plugins_PyQt5.pyqt5_plugin_loader import PluginLoader
from Plugin_Maker_AI.plugin_maker import Main as PluginMakerAI

# --- THEME MANAGEMENT ---
THEMES = {
    'light': {
        'global': """
            QWidget { font-family: 'Segoe UI', 'Roboto', sans-serif; color: #333333; background-color: #FFFFFF; }
            QMainWindow, QDialog { background-color: #FFFFFF; }
            QMessageBox { background-color: #ffffff; }
            QMessageBox QLabel { color: #333333; background-color: transparent; }
            QMessageBox QPushButton { background-color: #FFF0F5; color: #E75480; border: 1px solid #FADADD; padding: 5px 15px; border-radius: 5px; min-width: 80px; }
            QMessageBox QPushButton:hover { background-color: #E75480; color: #ffffff; border: 1px solid #E75480; }
            QScrollBar:vertical { border: none; background: #FFF0F5; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #FADADD; min-height: 20px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #E75480; }
            QScrollBar:horizontal { border: none; background: #FFF0F5; height: 10px; margin: 0; }
            QScrollBar::handle:horizontal { background: #FADADD; min-width: 20px; border-radius: 5px; }
            QScrollBar::handle:horizontal:hover { background: #E75480; }
        """,
        'top_bar': "QWidget { background-color: #FFFFFF; border-bottom: 1px solid #FADADD; }",
        'toggle_btn': "background-color: transparent; border: none; color: #888888; font-size: 22px;",
        'toggle_btn_hover': "color: #E75480;",
        'software_name': "QLabel { color: #333333; padding: 10px; font-size: 16px; font-weight: bold; background-color: transparent; }",
        'icon_btn_normal': "background-color: transparent; border: 2px solid #D3D3D3; color: #888888; font-size: 16px; font-weight: bold; border-radius: 20px;",
        'icon_btn_hover': "background-color: #E75480; color: #ffffff; border-color: #E75480;",
        'tutorial_btn_closed': "background-color: #ef4444; border: 2px solid #ef4444; color: white; font-size: 16px; font-weight: bold; border-radius: 20px;",
        'sidenav': "QFrame { background-color: #FFF0F5; border-right: 1px solid #FADADD; }",
        'sidenav_title': "QLabel { color: #E75480; padding: 20px 15px; font-size: 18px; font-weight: bold; background-color: #ffffff; }",
        'group_title': "color: #555555; padding: 15px 15px 5px 15px; font-size: 18px; font-weight: bold;",
        'group_title_hover': "color: #E75480;",
        'module_widget_hover': "background-color: #FDECF2;",
        'indicator_inactive': "border: 2px solid #d1d5db; border-radius: 5px;",
        'indicator_active': "border: 2px solid #E75480; background-color: #E75480; border-radius: 5px;",
        'module_label': "QLabel { color: #374151; padding: 5px; background: transparent; font-size: 12px; }",
        'add_btn': "background-color: transparent; border: none;",
        'add_btn_hover': "background-color: transparent;",
        'concept_layer_note': "QLabel { color: #6b7280; font-size: 40px; font-weight: 300; }",
        'concept_add_container': "QFrame { border: 2px dashed #E75480; border-radius: 70px; background-color: transparent; }",
        'concept_add_btn': "background-color: transparent; border: none;",
        'concept_add_btn_hover': "background-color: rgba(231, 84, 128, 0.1); border-radius: 65px;",
        'concept_shadow_color': "#FADADD",
        'module_container': "QFrame { background-color: #ffffff; border: 1px solid #FADADD; border-radius: 8px; }",
        'close_btn': "background-color: transparent; border: none; color: #9ca3af; font-size: 20px; font-weight: bold;",
        'close_btn_hover': "color: #ef4444;",
        'add_icon_color': '#E75480',
        'settings_container': "QFrame { background-color: #f8fafc; border-radius: 8px; }",
        'settings_title': "QLabel { color: #333; font-size: 24px; font-weight: bold; }",
        'settings_section_title': "QLabel { color: #555; font-size: 16px; font-weight: bold; border-bottom: 1px solid #FADADD; padding-bottom: 5px; }",
        'settings_button': "QPushButton { background-color: #FFF0F5; color: #E75480; border: 1px solid #FADADD; padding: 10px; border-radius: 5px; } QPushButton:hover { background-color: #E75480; color: #ffffff; }"
    },
    'dark': {
        'global': """
            QWidget { font-family: 'Segoe UI', 'Roboto', sans-serif; color: #dfe6e9; background-color: #2d3436; }
            QMainWindow, QDialog { background-color: #2d3436; }
            QPushButton { background-color: #3b4245; color: #dfe6e9; border: 1px solid #636e72; padding: 5px 10px; border-radius: 4px; }
            QPushButton:hover { background-color: #636e72; border-color: #00cec9; }
            QPushButton:pressed { background-color: #22282a; }
            QPushButton:disabled { background-color: #3b4245; color: #636e72; border-color: #444c4e; }
            QMessageBox { background-color: #22282a; }
            QMessageBox QLabel { color: #dfe6e9; background-color: transparent; }
            QMessageBox QPushButton { background-color: #3b4245; color: #00cec9; border: 1px solid #00cec9; padding: 5px 15px; border-radius: 5px; min-width: 80px; }
            QMessageBox QPushButton:hover { background-color: #00cec9; color: #22282a; }
            QScrollBar:vertical { border: none; background: #22282a; width: 10px; margin: 0; }
            QScrollBar::handle:vertical { background: #636e72; min-height: 20px; border-radius: 5px; }
            QScrollBar::handle:vertical:hover { background: #00cec9; }
            QScrollBar:horizontal { border: none; background: #22282a; height: 10px; margin: 0; }
            QScrollBar::handle:horizontal { background: #636e72; min-width: 20px; border-radius: 5px; }
            QScrollBar::handle:horizontal:hover { background: #00cec9; }
            QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox { background-color: #22282a; color: #dfe6e9; border: 1px solid #636e72; border-radius: 3px; padding: 4px; }
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #00cec9; }
            QAbstractItemView { background-color: #22282a; color: #dfe6e9; border: 1px solid #00cec9; selection-background-color: #00cec9; selection-color: #22282a; }
        """,
        'top_bar': "QWidget { background-color: #22282a; border-bottom: 1px solid #00cec9; }",
        'toggle_btn': "background-color: transparent; border: none; color: #dfe6e9; font-size: 22px;",
        'toggle_btn_hover': "color: #00cec9;",
        'software_name': "QLabel { color: #dfe6e9; padding: 10px; font-size: 16px; font-weight: bold; background-color: transparent; }",
        'icon_btn_normal': "background-color: transparent; border: 2px solid #dfe6e9; color: #dfe6e9; font-size: 16px; font-weight: bold; border-radius: 20px;",
        'icon_btn_hover': "background-color: #00cec9; color: #2d3436; border-color: #00cec9;",
        'tutorial_btn_closed': "background-color: #d63031; border: 2px solid #d63031; color: white; font-size: 16px; font-weight: bold; border-radius: 20px;",
        'sidenav': "QFrame { background-color: #22282a; border-right: 1px solid #444c4e; }",
        'sidenav_title': "QLabel { color: #00cec9; padding: 20px 15px; font-size: 18px; font-weight: bold; background-color: #22282a; }",
        'group_title': "color: #dfe6e9; padding: 15px 15px 5px 15px; font-size: 18px; font-weight: bold;",
        'group_title_hover': "color: #00cec9;",
        'module_widget_hover': "background-color: #3b4245;",
        'indicator_inactive': "border: 2px solid #636e72; border-radius: 5px;",
        'indicator_active': "border: 2px solid #00cec9; background-color: #00cec9; border-radius: 5px;",
        'module_label': "QLabel { color: #dfe6e9; padding: 5px; background: transparent; font-size: 12px; }",
        'add_btn': "background-color: transparent; border: none;",
        'add_btn_hover': "background-color: transparent;",
        'concept_layer_note': "QLabel { color: #b2bec3; font-size: 40px; font-weight: 300; }",
        'concept_add_container': "QFrame { border: 2px dashed #00cec9; border-radius: 70px; background-color: transparent; }",
        'concept_add_btn': "background-color: transparent; border: none;",
        'concept_add_btn_hover': "background-color: rgba(0, 206, 201, 0.1); border-radius: 65px;",
        'concept_shadow_color': "#00cec9",
        'module_container': "QFrame { background-color: #22282a; border: 1px solid #444c4e; border-radius: 8px; }",
        'close_btn': "background-color: transparent; border: none; color: #b2bec3; font-size: 20px; font-weight: bold;",
        'close_btn_hover': "color: #d63031;",
        'add_icon_color': '#00cec9',
        'settings_container': "QFrame { background-color: #3b4245; border-radius: 8px; }",
        'settings_title': "QLabel { color: #dfe6e9; font-size: 24px; font-weight: bold; }",
        'settings_section_title': "QLabel { color: #b2bec3; font-size: 16px; font-weight: bold; border-bottom: 1px solid #444c4e; padding-bottom: 5px; }",
        'settings_button': "QPushButton { background-color: #22282a; color: #00cec9; border: 1px solid #00cec9; padding: 10px; border-radius: 5px; } QPushButton:hover { background-color: #00cec9; color: #22282a; }"
    }
}


# --- CUSTOM WIDGETS ---
class AddModuleButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFlat(True)


class SideNavAddButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__("", parent)
        self.setFlat(True)


# --- Settings Management ---
CONFIG_FILE = 'settings.json'

def load_settings():
    defaults = {
        "show_tutorial_on_startup": True, 
        "theme": "dark"
    }
    if not os.path.exists(CONFIG_FILE):
        save_settings(defaults)
        return defaults
    try:
        with open(CONFIG_FILE, 'r') as f:
            settings = json.load(f)
            for key, value in defaults.items():
                if key not in settings:
                    settings[key] = value
            return settings
    except (json.JSONDecodeError, FileNotFoundError):
        save_settings(defaults)
        return defaults

def save_settings(settings):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(settings, f, indent=4)


# --- FIX: Update thread now accepts a parameter to conditionally run the backup. ---
class UpdateThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, should_backup: bool):
        super().__init__()
        self.should_backup = should_backup
        self.repo_owner = "ProjCRys"
        self.repo_name = "UI-Mod-Maker-for-WWMI"
        self.github_zip_link = f"https://github.com/{self.repo_owner}/{self.repo_name}/archive/refs/heads/main.zip"
        
        self.app_path = os.path.dirname(os.path.abspath(sys.argv[0]))
        self.download_path = os.path.join(self.app_path, 'update.zip')

    def run(self):
        temp_extract_path = os.path.join(self.app_path, 'temp_update')
        
        try:
            # STEP 1: BACKUP THE CURRENT VERSION (CONDITIONAL)
            if self.should_backup:
                self.progress.emit("Backing up the current version...")
                parent_dir = os.path.dirname(self.app_path)
                backup_folder_name = f"backup_{self.repo_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                backup_path = os.path.join(parent_dir, backup_folder_name)
                
                ignore_patterns = shutil.ignore_patterns('*.pyc', '__pycache__', 'backup_*', 'temp_update', '*.zip')
                shutil.copytree(self.app_path, backup_path, ignore=ignore_patterns)
            else:
                self.progress.emit("Skipping backup as requested.")

            # STEP 2: DOWNLOAD THE NEW VERSION
            self.progress.emit(f"Downloading update from {self.repo_owner}/{self.repo_name}...")
            urllib.request.urlretrieve(self.github_zip_link, self.download_path)
            
            # STEP 3: EXTRACT TO A TEMPORARY FOLDER
            self.progress.emit("Extracting new files...")
            if os.path.exists(temp_extract_path):
                shutil.rmtree(temp_extract_path)
            
            with zipfile.ZipFile(self.download_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_path)
            
            # STEP 4: APPLY THE UPDATE FROM THE TEMPORARY FOLDER
            self.progress.emit("Applying update...")
            update_source_dir = os.path.join(temp_extract_path, f'{self.repo_name}-main', 'Scripts')

            if not os.path.isdir(update_source_dir):
                raise FileNotFoundError("The required 'Scripts' folder was not found in the downloaded update.")

            for item in os.listdir(update_source_dir):
                source_item = os.path.join(update_source_dir, item)
                dest_item = os.path.join(self.app_path, item)
                
                if os.path.isdir(source_item):
                    if os.path.exists(dest_item):
                        shutil.rmtree(dest_item)
                    shutil.copytree(source_item, dest_item)
                else:
                    shutil.copy2(source_item, dest_item)
            
            # STEP 5: CLEANUP
            self.progress.emit("Cleaning up...")
            os.remove(self.download_path)
            shutil.rmtree(temp_extract_path)

            self.finished.emit(True, "Update successful! The application will now restart.")

        except Exception as e:
            self.finished.emit(False, f"An error occurred: {e}")
            if os.path.exists(self.download_path):
                os.remove(self.download_path)
            if os.path.exists(temp_extract_path):
                shutil.rmtree(temp_extract_path)

class ModuleContainer(QFrame):
    closed = pyqtSignal()
    def __init__(self, module_widget, parent=None, closeable=True):
        super().__init__(parent)
        self.setFrameStyle(QFrame.NoFrame)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        header = QWidget()
        header.setStyleSheet("background-color: transparent;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 5, 0)
        if closeable:
            self.close_btn = QPushButton("×")
            self.close_btn.setFixedSize(24, 24)
            self.close_btn.clicked.connect(self.close)
            header_layout.addStretch()
            header_layout.addWidget(self.close_btn)
        self.layout.addWidget(header)
        module_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        module_widget.setStyleSheet("background-color: transparent;")
        self.layout.addWidget(module_widget)

    def close(self):
        self.closed.emit()
        self.setParent(None)
        self.deleteLater()

class ConceptLayer(QWidget):
    def __init__(self, module_name, parent=None):
        super().__init__(parent)
        self.module_name = module_name
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(10)
        
        self.container_widget = QWidget()
        self.container_layout = QHBoxLayout(self.container_widget)
        self.container_layout.setSpacing(15)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.container_widget)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        self.empty_state_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setContentsMargins(0, 0, 0, 0)
        empty_layout.setSpacing(15)
        
        self.note_label = QLabel(f"No {self.module_name} modules added yet.")
        self.note_label.setAlignment(Qt.AlignCenter)
        
        self.add_button_container = QFrame()
        self.add_button_container.setFrameStyle(QFrame.NoFrame)
        self.add_button_container.setFixedSize(140, 140)
        
        add_button_layout = QGridLayout(self.add_button_container)
        add_button_layout.setSpacing(0)
        add_button_layout.setContentsMargins(3, 3, 7, 7)
        
        self.add_button = AddModuleButton()
        self.add_button.setFixedSize(130, 130)
        self.add_button.clicked.connect(self.add_module_container)
        add_button_layout.addWidget(self.add_button, 0, 0)
        
        self.add_button_shadow = QGraphicsDropShadowEffect(self)
        self.add_button_shadow.setBlurRadius(20)
        self.add_button_shadow.setOffset(0,0)
        self.add_button_container.setGraphicsEffect(self.add_button_shadow)

        empty_layout.addStretch(1)
        empty_layout.addWidget(self.note_label, 0, Qt.AlignCenter)
        empty_layout.addWidget(self.add_button_container, 0, Qt.AlignCenter)
        empty_layout.addStretch(1)

        self.layout.addWidget(self.empty_state_widget)
        self.layout.addWidget(self.scroll_area)
        
        self.max_containers = 3
        self._update_view()

    def _update_view(self):
        is_empty = self.container_layout.count() == 0
        self.empty_state_widget.setVisible(is_empty)
        self.scroll_area.setVisible(not is_empty)

    def add_module_container(self): pass

    def add_container(self, container):
        if self.container_layout.count() >= self.max_containers:
            QMessageBox.warning(self, "Limit Reached", f"Maximum number of containers ({self.max_containers}) has been reached.")
            container.deleteLater()
            return False
        container.closed.connect(self.container_closed)
        self.container_layout.addWidget(container)
        main_window = self.window()
        if isinstance(main_window, MainWindow):
            main_window.apply_theme_to_widget(container, main_window.current_theme)
        self._update_view()
        self.equalize_container_widths()
        return True

    def container_closed(self):
        QTimer.singleShot(0, self._update_view)
        QTimer.singleShot(0, self.equalize_container_widths)

    def equalize_container_widths(self):
        total_width = self.container_widget.width() - (self.container_layout.spacing() * (self.container_layout.count() - 1))
        num_containers = self.container_layout.count()
        if num_containers > 0:
            for i in range(self.container_layout.count()):
                widget = self.container_layout.itemAt(i).widget()
                if widget:
                    widget.setMinimumWidth(total_width // num_containers)
                    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

class EditorLayer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("Video Editor", parent)
    def add_module_container(self): self.add_container(ModuleContainer(VideoProcessor()))

class IniMakerLayer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("INI File Maker", parent)
    def add_module_container(self): self.add_container(ModuleContainer(IniMakerWidget()))

class VideoProcessingLayer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("Video Processing", parent)
    def add_module_container(self): self.add_container(ModuleContainer(VideoProcessingWidget()))

class CustomPluginsLayer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("Custom Plugins", parent)
    def add_module_container(self): self.add_container(ModuleContainer(HTMLPluginApp()))

class PyQt5PluginsLayer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("PyQt5 Plugins", parent)
    def add_module_container(self): self.add_container(ModuleContainer(PluginLoader()))

class OptimizeFrameLayer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("Optimize Frame", parent)
    def add_module_container(self): self.add_container(ModuleContainer(ProcessingWidget()))

class IniMakerV2Layer(ConceptLayer):
    def __init__(self, parent=None): super().__init__("INI Maker v2", parent)
    def add_module_container(self): self.add_container(ModuleContainer(AnimationWidget()))
    def equalize_container_widths(self):
        total_width = self.container_widget.width()
        num_containers = self.container_layout.count()
        if num_containers > 0:
            container_width = total_width // num_containers
            for i in range(self.container_layout.count()):
                widget = self.container_layout.itemAt(i).widget()
                if widget: widget.setFixedWidth(container_width)

class HomeLayer(ConceptLayer):
    home_loaded = pyqtSignal()
    def __init__(self, web_profile, parent=None):
        self.web_profile = web_profile
        super().__init__("Home", parent)
        self.max_containers = 1
        self.add_module_container()
    def _on_load_finished(self, success):
        if success: self.home_loaded.emit()
    def add_module_container(self):
        page = QWebEnginePage(self.web_profile, self)
        web_view = QWebEngineView()
        web_view.setPage(page)
        web_view.setUrl(QUrl("https://gamebanana.com/mods/536292"))
        web_view.setZoomFactor(1.5)
        web_view.loadFinished.connect(self._on_load_finished)
        module_container = ModuleContainer(web_view, closeable=False)
        module_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if not self.add_container(module_container):
            QMessageBox.warning(self, "Error", "Failed to add the home module.")

class TutorialLayer(ConceptLayer):
    def __init__(self, parent=None):
        super().__init__("Tutorial", parent)
        self.max_containers = 1
        self.web_view = None
        self.add_module_container()

    def add_module_container(self):
        self.web_view = QWebEngineView()
        current_dir = os.path.dirname(os.path.abspath(__file__))
        html_file_path = os.path.join(current_dir, "tutorial.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_file_path))
        self.web_view.setZoomFactor(1.5)
        self.web_view.loadFinished.connect(self._apply_initial_theme)
        
        module_container = ModuleContainer(self.web_view, closeable=False)
        module_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if not self.add_container(module_container):
            QMessageBox.warning(self, "Error", "Failed to add the tutorial module.")
            
    def _apply_initial_theme(self):
        main_window = self.window()
        if isinstance(main_window, MainWindow):
            self.set_theme(main_window.current_theme)
            
    def set_theme(self, theme_name):
        if self.web_view:
            js_code = f"document.documentElement.classList.toggle('dark-mode', {str(theme_name == 'dark').lower()});"
            self.web_view.page().runJavaScript(js_code)

class SettingsLayer(QWidget):
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        container = QFrame()
        container.setFixedWidth(600)
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(30, 30, 30, 30)
        self.container_layout.setSpacing(20)
        self.container = container

        title = QLabel("Settings")
        self.title_label = title
        
        appearance_label = QLabel("Appearance")
        self.appearance_label = appearance_label
        
        self.theme_button = QPushButton()
        self.theme_button.clicked.connect(self.main_window.toggle_theme)

        app_label = QLabel("Application")
        self.app_label = app_label

        self.refresh_button = QPushButton("Refresh Application")
        self.refresh_button.clicked.connect(self.main_window.refresh_application)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.main_window.start_update)

        self.update_status_label = QLabel("")
        self.update_status_label.setAlignment(Qt.AlignCenter)
        self.update_status_label.setWordWrap(True)

        self.container_layout.addWidget(title, 0, Qt.AlignCenter)
        self.container_layout.addSpacing(20)
        self.container_layout.addWidget(appearance_label)
        self.container_layout.addWidget(self.theme_button)
        self.container_layout.addSpacing(20)
        self.container_layout.addWidget(app_label)
        self.container_layout.addWidget(self.refresh_button)
        self.container_layout.addWidget(self.update_button)
        self.container_layout.addWidget(self.update_status_label)
        self.container_layout.addStretch()

        layout.addWidget(container)
        
class PluginMakerAILayer(ConceptLayer):
    def __init__(self, parent=None):
        super().__init__("Plugin Maker AI (Experimental)", parent)
        self.max_containers = 1
    def add_module_container(self): self.add_container(ModuleContainer(PluginMakerAI()))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Animated UI Maker")
        self.settings = load_settings()
        self.current_theme = self.settings.get("theme", "dark")
        self.web_profile = QWebEngineProfile("storage", self)
        self.web_profile.downloadRequested.connect(self.handle_download_request)
        self.update_thread = None
        
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.plus_icon_path = os.path.join(self.script_dir, 'Tutorial-Resources', '+.png')
        
        os.makedirs("previews", exist_ok=True)
        self.screenshot_shortcut = QShortcut(QKeySequence("Ctrl+P"), self)
        self.screenshot_shortcut.activated.connect(self.take_previews)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setup_top_bar()
        content_widget = QWidget()
        self.content_layout = QHBoxLayout(content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.setup_sidenav()
        self.content_layout.addWidget(self.sidenav)
        self.setup_concept_layers()
        self.content_layout.addWidget(self.layer_stack)
        self.main_layout.addWidget(content_widget)
        self.selected_module = None
        self._setup_animations()
        self.apply_theme(self.current_theme)
        self.switch_module("Home")

    def _setup_animations(self):
        self.sidenav.setMaximumWidth(250)
        self.sidenav_animation = QPropertyAnimation(self.sidenav, b"maximumWidth")
        self.sidenav_animation.setDuration(300)
        self.sidenav_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.opacity_effect = QGraphicsOpacityEffect(self.layer_stack)
        self.layer_stack.setGraphicsEffect(self.opacity_effect)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self.opacity_effect.setEnabled(False)

    def setup_top_bar(self):
        self.top_bar = QWidget()
        self.top_bar.setFixedHeight(50)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(5, 0, 10, 0)
        self.toggle_btn = QPushButton("≡")
        self.toggle_btn.setFixedSize(40, 40)
        self.toggle_btn.clicked.connect(self.toggle_sidenav)
        self.software_name = QLabel("Animated UI Maker for WWMI")
        
        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.setFixedSize(100, 40)
        self.home_btn.clicked.connect(lambda: self.switch_module("Home"))
        
        self.tutorial_btn = QPushButton("🛈 Tutorial")
        self.tutorial_btn.setFixedSize(100, 40)
        self.tutorial_btn.clicked.connect(self.show_tutorial)
        
        top_layout.addWidget(self.toggle_btn)
        top_layout.addWidget(self.software_name)  
        top_layout.addStretch()
        top_layout.addWidget(self.home_btn)
        top_layout.addWidget(self.tutorial_btn)
        self.main_layout.addWidget(self.top_bar)
        
    def setup_sidenav(self):
        self.sidenav = QFrame()
        self.sidenav_layout = QVBoxLayout(self.sidenav)
        self.sidenav_layout.setContentsMargins(0, 0, 0, 0)
        self.sidenav_layout.setSpacing(0)
        
        self.sidenav_title = QLabel("Modules")
        self.sidenav_layout.addWidget(self.sidenav_title)
        self.module_indicators = {}
        self.module_widgets = []
        self.group_titles = []
        
        def create_group(title_text, is_expanded=True):
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(0, 5, 0, 5)
            group_layout.setSpacing(2)
            content_container = QWidget()
            content_container.setLayout(group_layout)
            content_container.setVisible(is_expanded)
            icon = "▼" if is_expanded else "▶"
            group_title = QLabel(f"{icon} {title_text}")
            group_title.setProperty("is_expanded", is_expanded)
            group_title.setCursor(Qt.PointingHandCursor)
            self.group_titles.append(group_title)
            group_title.mousePressEvent = lambda event, gt=group_title, cc=content_container: self.toggle_group(gt, cc)
            self.sidenav_layout.addWidget(group_title)
            self.sidenav_layout.addWidget(content_container)
            return group_layout

        layouts = {
            "Team Portrait Tool": ["Video Editor", "INI File Maker"],
            "General UI Tool": ["Video Processing", "Optimize Frame", "INI File Maker v2"],
            "Custom Plugins": ["HTML Plugins", "PyQt5 Plugins", "Plugin Maker AI (Experimental)"]
        }
        add_functions = {
            "Video Editor": self.add_editor_module, "INI File Maker": self.add_ini_maker_module,
            "Video Processing": self.add_video_processing_module, "Optimize Frame": self.add_optimize_frame_module,
            "INI File Maker v2": self.add_ini_maker_v2_module, "HTML Plugins": self.add_custom_plugins_module,
            "PyQt5 Plugins": self.add_pyqt5_plugins_module, "Plugin Maker AI (Experimental)": self.add_plugin_maker_ai_module
        }
        for group, modules in layouts.items():
            layout = create_group(group)
            for module in modules:
                layout.addWidget(self.create_module_button(module, add_functions[module]))
        
        self.sidenav_layout.addStretch()

        self.settings_btn = QPushButton("⚙️ Settings")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setMinimumHeight(40)
        self.settings_btn.setStyleSheet("text-align: left; padding-left: 20px;")
        self.settings_btn.clicked.connect(lambda: self.switch_module("Settings"))
        self.sidenav_layout.addWidget(self.settings_btn)

    def create_module_button(self, module_name, add_function):
        module_widget = QWidget()
        module_widget.setCursor(Qt.PointingHandCursor)
        module_widget.setStyleSheet("QWidget { background-color: transparent; border-radius: 4px; }")
        module_layout = QHBoxLayout(module_widget)
        module_layout.setContentsMargins(15, 5, 5, 5)
        indicator_label = QLabel("")  
        indicator_label.setFixedSize(10, 10)
        self.module_indicators[module_name] = indicator_label
        module_label = QLabel(module_name)
        add_button = SideNavAddButton()
        add_button.setFixedSize(24, 24)
        add_button.clicked.connect(add_function)
        module_widget.mousePressEvent = lambda event: self.switch_module(module_name)
        module_layout.addWidget(indicator_label)
        module_layout.addWidget(module_label, 1)
        module_layout.addWidget(add_button)
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(5,0,5,0)
        container_layout.addWidget(module_widget)
        self.module_widgets.append({
            'widget': module_widget, 'label': module_label, 'add_btn': add_button
        })
        return container

    def switch_module(self, module_name):
        target_layer = self.module_layers.get(module_name)
        if not target_layer or self.layer_stack.currentWidget() == target_layer or self.fade_animation.state() == QAbstractAnimation.Running:
            return

        theme = THEMES[self.current_theme]
        if self.selected_module:
            self.selected_module.setStyleSheet(theme['indicator_inactive'])
        
        indicator_label = self.module_indicators.get(module_name)
        if indicator_label:
            self.selected_module = indicator_label
            self.selected_module.setStyleSheet(theme['indicator_active'])
        else:
            self.selected_module = None

        self.opacity_effect.setEnabled(True)
        def on_fade_out_finished():
            self.layer_stack.setCurrentWidget(target_layer)
            self.fade_animation.setDirection(QAbstractAnimation.Forward)
            self.fade_animation.finished.connect(on_fade_in_finished)
            self.fade_animation.start()
            try: self.fade_animation.finished.disconnect(on_fade_out_finished)
            except TypeError: pass
        
        def on_fade_in_finished():
            self.opacity_effect.setEnabled(False)
            try: self.fade_animation.finished.disconnect(on_fade_in_finished)
            except TypeError: pass

        self.fade_animation.finished.connect(on_fade_out_finished)
        self.fade_animation.setDirection(QAbstractAnimation.Backward)
        self.fade_animation.start()
        
    def setup_concept_layers(self):
        self.layer_stack = QStackedWidget()
        self.layer_stack.setStyleSheet("background-color: transparent;")
        self.editor_layer = EditorLayer()
        self.ini_maker_layer = IniMakerLayer()
        self.video_processing_layer = VideoProcessingLayer()
        self.custom_plugins_layer = CustomPluginsLayer()
        self.pyqt5_plugins_layer = PyQt5PluginsLayer()
        self.optimize_frame_layer = OptimizeFrameLayer()
        self.ini_maker_v2_layer = IniMakerV2Layer()
        self.home_layer = HomeLayer(self.web_profile, self)
        self.home_layer.home_loaded.connect(self.show_tutorial_on_home_load)
        self.plugin_maker_ai_layer = PluginMakerAILayer()
        self.tutorial_layer = TutorialLayer()
        self.settings_layer = SettingsLayer(self)

        self.module_layers = {
            "Video Editor": self.editor_layer, "INI File Maker": self.ini_maker_layer,
            "Video Processing": self.video_processing_layer, "HTML Plugins": self.custom_plugins_layer,
            "PyQt5 Plugins": self.pyqt5_plugins_layer, "Optimize Frame": self.optimize_frame_layer,
            "INI File Maker v2": self.ini_maker_v2_layer, "Home": self.home_layer,
            "Plugin Maker AI (Experimental)": self.plugin_maker_ai_layer,
            "Tutorial": self.tutorial_layer,
            "Settings": self.settings_layer
        }
        for layer in self.module_layers.values():
            self.layer_stack.addWidget(layer)
        self.layer_stack.setCurrentWidget(self.home_layer)

    def toggle_theme(self):
        new_theme = 'dark' if self.current_theme == 'light' else 'light'
        self.apply_theme(new_theme)
        
    def refresh_application(self):
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setIcon(QMessageBox.Warning)
        confirm_dialog.setText("Are you sure you want to refresh the application?")
        confirm_dialog.setInformativeText("This will restart the program. Any unsaved work will be lost.")
        confirm_dialog.setWindowTitle("Confirm Refresh")
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_dialog.setDefaultButton(QMessageBox.No)
        theme = THEMES[self.current_theme]
        confirm_dialog.setStyleSheet(theme['global'])
        if confirm_dialog.exec_() == QMessageBox.Yes:
            QApplication.instance().quit()
            os.execv(sys.executable, ['python'] + sys.argv)
    
    # --- FIX: Update process now asks the user if they want to create a backup. ---
    def start_update(self):
        # First, confirm the user wants to start the update process at all.
        confirm_dialog = QMessageBox(self)
        confirm_dialog.setIcon(QMessageBox.Question)
        confirm_dialog.setText("Are you sure you want to update?")
        confirm_dialog.setInformativeText("The application will download the latest version and restart. Any unsaved work will be lost.")
        confirm_dialog.setWindowTitle("Confirm Update")
        confirm_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirm_dialog.setDefaultButton(QMessageBox.No)
        
        if confirm_dialog.exec_() == QMessageBox.No:
            return # User cancelled the entire process.

        # Second, ask the user if they want to perform a backup.
        backup_dialog = QMessageBox(self)
        backup_dialog.setIcon(QMessageBox.Question)
        backup_dialog.setText("Create a backup before updating?")
        backup_dialog.setInformativeText("This is highly recommended. The backup will be stored in a folder next to your 'Scripts' directory.")
        backup_dialog.setWindowTitle("Backup Confirmation")
        backup_dialog.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        backup_dialog.setDefaultButton(QMessageBox.Yes) # Default to 'Yes' for safety.
        
        result = backup_dialog.exec_()

        if result == QMessageBox.Cancel:
            return # User cancelled.

        # Determine if a backup should be made based on the user's choice.
        should_backup = (result == QMessageBox.Yes)

        # Start the update thread, passing the user's choice.
        self.settings_layer.update_button.setEnabled(False)
        self.settings_layer.update_status_label.setText("Starting update process...")
        self.update_thread = UpdateThread(should_backup=should_backup)
        self.update_thread.progress.connect(self.on_update_progress)
        self.update_thread.finished.connect(self.on_update_finished)
        self.update_thread.start()

    def on_update_progress(self, message):
        self.settings_layer.update_status_label.setText(message)

    def on_update_finished(self, success, message):
        self.settings_layer.update_status_label.setText(message)
        if success:
            QMessageBox.information(self, "Update Successful", message)
            QTimer.singleShot(1000, self.refresh_application)
        else:
            QMessageBox.critical(self, "Update Failed", message)
            self.settings_layer.update_button.setEnabled(True)


    def apply_theme_to_widget(self, widget, theme_name):
        theme = THEMES[theme_name]
        if isinstance(widget, ModuleContainer):
            widget.setStyleSheet(theme['module_container'])
            if hasattr(widget, 'close_btn'):
                widget.close_btn.setStyleSheet(f"QPushButton {{ {theme['close_btn']} }} QPushButton:hover {{ {theme['close_btn_hover']} }}")

    def create_colored_icon(self, color):
        if not os.path.exists(self.plus_icon_path): return QIcon()
        pixmap = QPixmap(self.plus_icon_path)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color))
        painter.end()
        return QIcon(pixmap)

    def apply_theme(self, theme_name):
        self.current_theme = theme_name
        theme = THEMES[theme_name]
        
        QApplication.instance().setStyleSheet(theme['global'])
        
        self.top_bar.setStyleSheet(theme['top_bar'])
        self.toggle_btn.setStyleSheet(f"QPushButton {{ {theme['toggle_btn']} }} QPushButton:hover {{ {theme['toggle_btn_hover']} }}")
        self.software_name.setStyleSheet(theme['software_name'])
        icon_btn_style = f"QPushButton {{ {theme['icon_btn_normal']} }} QPushButton:hover {{ {theme['icon_btn_hover']} }}"
        self.home_btn.setStyleSheet(icon_btn_style)
        self.reset_tutorial_button_style()

        self.sidenav.setStyleSheet(theme['sidenav'])
        self.sidenav_title.setStyleSheet(theme['sidenav_title'])
        self.settings_btn.setStyleSheet(f"QPushButton {{ {theme['module_label']} text-align: left; padding-left: 20px; border: none; }} QPushButton:hover {{ {theme['module_widget_hover']} }}")

        for title in self.group_titles:
            title.setStyleSheet(f"QLabel {{ {theme['group_title']} }} QLabel:hover {{ {theme['group_title_hover']} }}")
        
        add_icon = self.create_colored_icon(theme['add_icon_color'])
        for item in self.module_widgets:
            item['widget'].setStyleSheet(f"QWidget:hover {{ {theme['module_widget_hover']} }}")
            item['label'].setStyleSheet(theme['module_label'])
            item['add_btn'].setStyleSheet(f"QPushButton {{ {theme['add_btn']} }} QPushButton:hover {{ {theme['add_btn_hover']} }}")
            item['add_btn'].setIcon(add_icon)
            item['add_btn'].setIconSize(QSize(18, 18))

        for name, indicator in self.module_indicators.items():
            if self.selected_module == indicator:
                indicator.setStyleSheet(theme['indicator_active'])
            else:
                indicator.setStyleSheet(theme['indicator_inactive'])
        
        for layer in self.module_layers.values():
            if hasattr(layer, 'note_label'):
                layer.note_label.setStyleSheet(theme['concept_layer_note'])
                layer.add_button_container.setStyleSheet(theme['concept_add_container'])
                layer.add_button.setStyleSheet(f"QPushButton {{ {theme['concept_add_btn']} }} QPushButton:hover {{ {theme['concept_add_btn_hover']} }}")
                layer.add_button.setIcon(add_icon)
                layer.add_button.setIconSize(QSize(80, 80))
                layer.add_button_shadow.setColor(QColor(theme['concept_shadow_color']))
            if hasattr(layer, 'container_layout'):
                for i in range(layer.container_layout.count()):
                    widget = layer.container_layout.itemAt(i).widget()
                    self.apply_theme_to_widget(widget, theme_name)
        
        sl = self.settings_layer
        sl.container.setStyleSheet(theme['settings_container'])
        sl.title_label.setStyleSheet(theme['settings_title'])
        sl.appearance_label.setStyleSheet(theme['settings_section_title'])
        sl.app_label.setStyleSheet(theme['settings_section_title'])
        sl.theme_button.setStyleSheet(theme['settings_button'])
        sl.refresh_button.setStyleSheet(theme['settings_button'])
        sl.update_button.setStyleSheet(theme['settings_button'])
        sl.theme_button.setText(f"Switch to {'Light' if theme_name == 'dark' else 'Dark'} Mode")

        if hasattr(self, 'tutorial_layer'):
            self.tutorial_layer.set_theme(theme_name)

        self.settings['theme'] = theme_name
        save_settings(self.settings)

    def toggle_sidenav(self):
        start = self.sidenav.width()
        end = 0 if start > 0 else 250
        try: self.sidenav_animation.finished.disconnect()
        except TypeError: pass
        if end == 0: self.sidenav_animation.finished.connect(lambda: self.sidenav.setVisible(False))
        else: self.sidenav.setVisible(True)
        self.sidenav_animation.setStartValue(start)
        self.sidenav_animation.setEndValue(end)
        self.sidenav_animation.start()

    def add_editor_module(self): self.editor_layer.add_module_container()
    def add_ini_maker_module(self): self.ini_maker_layer.add_module_container()
    def add_video_processing_module(self): self.video_processing_layer.add_module_container()
    def add_custom_plugins_module(self): self.custom_plugins_layer.add_module_container()
    def add_pyqt5_plugins_module(self): self.pyqt5_plugins_layer.add_module_container()
    def add_optimize_frame_module(self): self.optimize_frame_layer.add_module_container()
    def add_ini_maker_v2_module(self): self.ini_maker_v2_layer.add_module_container()
    def add_plugin_maker_ai_module(self): self.plugin_maker_ai_layer.add_module_container()
    
    def resizeEvent(self, event): super().resizeEvent(event)

    def toggle_group(self, group_title_label, content_container):
        is_expanded = not content_container.isVisible()
        group_title_label.setProperty("is_expanded", is_expanded)
        icon = "▼" if is_expanded else "▶"
        text = group_title_label.text().split(' ', 1)[1]
        group_title_label.setText(f"{icon} {text}")
        content_container.setVisible(is_expanded)
        if self.sidenav.isVisible():
            self.sidenav.setVisible(False)
            self.sidenav.setVisible(True)

    def show_tutorial(self):
        self.switch_module("Tutorial")
        if self.settings.get("show_tutorial_on_startup", True):
            self.settings["show_tutorial_on_startup"] = False
            save_settings(self.settings)
        theme = THEMES[self.current_theme]
        self.tutorial_btn.setStyleSheet(theme['tutorial_btn_closed'])
        QTimer.singleShot(2000, self.reset_tutorial_button_style)

    def show_tutorial_on_home_load(self):
        if self.settings.get("show_tutorial_on_startup", True):
            self.show_tutorial()

    def reset_tutorial_button_style(self):
        theme = THEMES[self.current_theme]
        self.tutorial_btn.setStyleSheet(f"QPushButton {{ {theme['icon_btn_normal']} }} QPushButton:hover {{ {theme['icon_btn_hover']} }}")

    def handle_download_request(self, download: QWebEngineDownloadItem):
        if download.state() == QWebEngineDownloadItem.DownloadRequested:
            suggested_path = os.path.join(os.path.expanduser('~'), 'Downloads', os.path.basename(download.path()))
            save_path, _ = QFileDialog.getSaveFileName(self, "Save File", suggested_path)
            if save_path:
                download.setPath(save_path)
                download.accept()
            else:
                download.cancel()

    def take_previews(self):
        self.modules_to_screenshot = [
            "Home", "Tutorial", "Video Editor", "INI File Maker", "Video Processing",
            "Optimize Frame", "INI File Maker v2", "HTML Plugins", "PyQt5 Plugins",
            "Plugin Maker AI (Experimental)"
        ]
        self.original_theme = self.current_theme
        self.original_module_widget = self.layer_stack.currentWidget()
        self.current_screenshot_index = 0
        self.current_screenshot_theme = 'light'
        QMessageBox.information(self, "Screenshot Process Started",
                                f"Starting to capture {len(self.modules_to_screenshot) * 2} previews. "
                                "The application window will change automatically. "
                                "Please wait until the 'Finished' message appears.")
        QTimer.singleShot(100, self._process_next_screenshot)

    def _process_next_screenshot(self):
        if self.current_screenshot_index >= len(self.modules_to_screenshot):
            self.apply_theme(self.original_theme)
            self.layer_stack.setCurrentWidget(self.original_module_widget)
            QMessageBox.information(self, "Success", "All previews have been saved to the 'previews' folder.")
            return

        module_name = self.modules_to_screenshot[self.current_screenshot_index]
        theme = self.current_screenshot_theme
        self.apply_theme(theme)
        self.switch_module(module_name)
        delay = 600
        QTimer.singleShot(delay, lambda: self._capture_and_proceed(module_name, theme))

    def _capture_and_proceed(self, module_name, theme):
        sanitized_name = ''.join(c for c in module_name if c.isalnum() or c in " _-").rstrip().replace(" ", "_")
        filename = os.path.join("previews", f"{sanitized_name}_{theme.capitalize()}.png")
        self.grab().save(filename)
        if self.current_screenshot_theme == 'light':
            self.current_screenshot_theme = 'dark'
        else:
            self.current_screenshot_theme = 'light'
            self.current_screenshot_index += 1
        QTimer.singleShot(50, self._process_next_screenshot)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
    QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
    QWebEngineSettings.globalSettings().setAttribute(QWebEngineSettings.PlaybackRequiresUserGesture, False)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec_())
