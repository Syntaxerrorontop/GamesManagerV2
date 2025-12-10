from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QTabWidget, QFormLayout)
from PyQt5.QtCore import Qt
from .utility.utility_functions import load_json, save_json, clean_unused_cache_files
from .utility.utility_vars import CONFIG_FOLDER
from .utility.config_updater import update_game_configs
import os

class Settings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.userconfig = load_json(os.path.join(CONFIG_FOLDER, "userconfig.json"))
        
        self.init_ui()
        self.setStyleSheet(self.get_stylesheet())

    def init_ui(self):
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Title
        title_label = QLabel("Settings")
        title_label.setObjectName("header_title")
        main_layout.addWidget(title_label)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setObjectName("settings_tabs")
        
        # --- Tab 1: General ---
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        general_layout.setContentsMargins(20, 20, 20, 20)
        general_layout.setSpacing(15)
        
        self.autoupdate_checkbox = QCheckBox("Enable Autoupdates")
        self.autoupdate_checkbox.setChecked(self.userconfig.get("autoupdates", False))
        self.autoupdate_checkbox.stateChanged.connect(self.autoupdate_changed)
        general_layout.addWidget(self.autoupdate_checkbox)
        
        self.clean_cache_btn = QPushButton("Clean Cache")
        self.clean_cache_btn.setCursor(Qt.PointingHandCursor)
        self.clean_cache_btn.setFixedWidth(200)
        self.clean_cache_btn.clicked.connect(self.run_clean_cache)
        general_layout.addWidget(self.clean_cache_btn)

        general_layout.addStretch()
        
        self.tabs.addTab(general_tab, "General")

        # --- Tab 2: Game Config ---
        config_tab = QWidget()
        config_layout = QVBoxLayout(config_tab)
        config_layout.setContentsMargins(20, 20, 20, 20)
        config_layout.setSpacing(20)

        # Form Layout for compact inputs
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignLeft)

        # Username Input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. Player123")
        self.username_input.setText(self.userconfig.get("default_username", ""))
        self.username_input.setFixedWidth(300) # Compact width
        self.username_input.textChanged.connect(self.save_settings)
        form_layout.addRow(QLabel("Default Username:"), self.username_input)

        # Language Input
        self.language_input = QLineEdit()
        self.language_input.setPlaceholderText("e.g. english")
        self.language_input.setText(self.userconfig.get("default_language", ""))
        self.language_input.setFixedWidth(300) # Compact width
        self.language_input.textChanged.connect(self.save_settings)
        form_layout.addRow(QLabel("Default Language:"), self.language_input)
        
        config_layout.addLayout(form_layout)

        # Force Update Button
        self.update_btn = QPushButton("Apply to All Games")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setFixedWidth(200)
        self.update_btn.clicked.connect(self.force_update_games)
        config_layout.addWidget(self.update_btn)
        
        config_layout.addStretch()

        self.tabs.addTab(config_tab, "Game Config")
        
        main_layout.addWidget(self.tabs)

    def autoupdate_changed(self, state):
        self.userconfig["autoupdates"] = bool(state)
        save_json(os.path.join(CONFIG_FOLDER, "userconfig.json"), self.userconfig)

    def run_clean_cache(self):
        count = clean_unused_cache_files()
        QMessageBox.information(self, "Cache Cleanup", f"Cleanup complete.\nRemoved {count} unused file(s).")

    def save_settings(self):
        self.userconfig["default_username"] = self.username_input.text()
        self.userconfig["default_language"] = self.language_input.text()
        save_json(os.path.join(CONFIG_FOLDER, "userconfig.json"), self.userconfig)

    def force_update_games(self):
        self.save_settings()
        try:
            update_game_configs(
                username=self.username_input.text(),
                language=self.language_input.text()
            )
            QMessageBox.information(self, "Success", "Game configurations updated successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update games: {e}")

    def get_stylesheet(self):
        return """
            /* Global Font */
            * {
                font-family: 'Montserrat', 'Segoe UI', sans-serif;
            }
            
            QWidget {
                background-color: #1a1a1a;
                color: #e0e0e0;
            }

            /* Header */
            #header_title {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
            }

            /* Tabs */
            QTabWidget::pane {
                border: 1px solid #333;
                border-radius: 6px; /* Rounded corners for the pane */
                background: #222;
                top: -1px; 
            }
            
            QTabBar::tab {
                background: #2b2b2b;
                color: #b0b0b0;
                padding: 8px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px; /* Rounded top corners for tabs */
                border-top-right-radius: 6px;
                font-weight: 500;
            }
            
            QTabBar::tab:selected {
                background: #222; /* Matches pane background */
                color: #ffffff;
                border-bottom: 2px solid #0078d7;
            }
            
            QTabBar::tab:hover:!selected {
                background: #333;
            }

            /* Labels */
            QLabel {
                color: #e0e0e0;
                font-size: 14px;
            }

            /* Checkbox */
            QCheckBox {
                font-size: 14px;
                color: #e0e0e0;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 4px; /* Rounded corners for checkbox indicator */
            }
            QCheckBox::indicator:checked {
                background-color: #0078d7;
                border: 1px solid #0078d7;
            }

            /* Input Fields */
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #333;
                border-radius: 6px; /* Rounded corners for input fields */
                padding: 6px; /* Reduced padding */
                font-size: 13px;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }

            /* Buttons */
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px; /* Rounded corners for buttons */
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """

    

    
