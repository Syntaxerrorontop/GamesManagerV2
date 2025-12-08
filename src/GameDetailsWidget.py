from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QDialog, QCheckBox, QFileDialog, QInputDialog,
                             QSizePolicy, QMessageBox)
import os
import shutil
import json
import logging
from .utility.utility_functions import save_json, load_json, hash_url, get_hashed_file, format_playtime
from .utility.utility_vars import CACHE_FOLDER, CONFIG_FOLDER
from .utility.game_classes import GameInstance

class GameDetailsWidget(QWidget):
    def __init__(self, libary, parent=None):
        super().__init__(parent)
        self.libary = libary
        self.logger = logging.getLogger('GameDetails')
        self.init_ui()
        self.install_button.clicked.connect(self.install)
        self.launch_button.clicked.connect(self.toggle_game_state)
        self.update_button.clicked.connect(self.install)
        self.uninstall_button.clicked.connect(self.uninstall)
        self.add_category_button.clicked.connect(self.add_to_category)
        self.remove_from_category_button.clicked.connect(self.remove_from_category)
        self.remove_from_account_button.clicked.connect(self.remove_from_account)
        self.manuel_path_button.clicked.connect(self.set_path)
        self.args_bar.textChanged.connect(self.arg_callback)

        self.check_timer = QTimer(self)
        self.check_timer.setInterval(500)
        self.check_timer.timeout.connect(self.update_ui_state)
        self.check_timer.start()
        self.last_running_state = None

    def toggle_game_state(self):
        if hasattr(self, 'game'):
            if self.game.is_running:
                self.stop_game()
            else:
                self.launch_game()

    def launch_game(self):
        if hasattr(self, 'game'):
            self.game.start()
            self.update_ui_state()

    def stop_game(self):
        if hasattr(self, 'game'):
            self.game.stop()
            self.update_ui_state()

    def update_ui_state(self):
        if not hasattr(self, 'game'):
            return
            
        is_running = self.game.is_running
        
        # Only update if state changed
        if self.last_running_state == is_running:
            return
            
        self.last_running_state = is_running
        
        if is_running:
            self.launch_button.setText("Stop Game")
            self.launch_button.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
            self.uninstall_button.setEnabled(False)
            self.uninstall_button.setToolTip("Cannot uninstall while game is running")
        else:
            self.launch_button.setText("Launch")
            self.launch_button.setStyleSheet("")
            self.uninstall_button.setEnabled(True)
            self.uninstall_button.setToolTip("")

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- Image ---
        self.image_label = QLabel()
        self.image_label.setMinimumSize(640, 360)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("border: 1px solid #444; border-radius: 8px;")
        main_layout.addWidget(self.image_label)

        # --- Details ---
        details_layout = QVBoxLayout()
        main_layout.addLayout(details_layout)

        self.name_label = QLabel()
        self.name_label.setObjectName("name_label")
        details_layout.addWidget(self.name_label)

        info_layout = QHBoxLayout()
        details_layout.addLayout(info_layout)
        
        self.version_label = QLabel()
        self.version_label.setObjectName("version_label")
        info_layout.addWidget(self.version_label)

        self.playtime_label = QLabel()
        self.playtime_label.setObjectName("playtime_label")
        info_layout.addWidget(self.playtime_label)

        self.categories_label = QLabel()
        self.categories_label.setObjectName("categories_label")
        details_layout.addWidget(self.categories_label)

        self.args_bar = QLineEdit()
        self.args_bar.setPlaceholderText("Enter arguments...")
        details_layout.addWidget(self.args_bar)

        # --- Buttons ---
        button_grid = QVBoxLayout()
        main_layout.addLayout(button_grid)

        row1_layout = QHBoxLayout()
        button_grid.addLayout(row1_layout)
        
        self.launch_button = QPushButton("Launch")
        row1_layout.addWidget(self.launch_button)

        self.install_button = QPushButton("Install")
        row1_layout.addWidget(self.install_button)
        
        row2_layout = QHBoxLayout()
        button_grid.addLayout(row2_layout)

        self.update_button = QPushButton("Install Update")
        row2_layout.addWidget(self.update_button)

        self.uninstall_button = QPushButton("Uninstall")
        self.uninstall_button.setStyleSheet("background-color: #c0392b;")
        row2_layout.addWidget(self.uninstall_button)

        row3_layout = QHBoxLayout()
        button_grid.addLayout(row3_layout)

        self.add_category_button = QPushButton("Add to Category")
        row3_layout.addWidget(self.add_category_button)

        self.remove_from_category_button = QPushButton("Remove from Category")
        row3_layout.addWidget(self.remove_from_category_button)

        self.remove_from_account_button = QPushButton("Remove from Account")
        button_grid.addWidget(self.remove_from_account_button)

        self.manuel_path_button = QPushButton("Set Game Path")
        button_grid.addWidget(self.manuel_path_button)
        
    def remove_from_account(self):
        if not hasattr(self, 'game'):
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Removal")
        dialog.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; font-size: 14px; }
            QLabel { font-size: 14px; }
            QPushButton { background: #444; border: none; padding: 8px 15px; border-radius: 8px; color: white; }
            QPushButton:hover { background: #555; }
        """)

        layout = QVBoxLayout()
        label = QLabel("Are you sure you want to permanently remove this game from your account?")
        layout.addWidget(label)
        
        button_layout = QHBoxLayout()
        yes_button = QPushButton("Yes")
        no_button = QPushButton("No")
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        yes_button.clicked.connect(dialog.accept)
        no_button.clicked.connect(dialog.reject)
        
        if dialog.exec():
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            if self.game.name in data:
                del data[self.game.name]
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
                self.libary.load_games()

        
    def set_game(self, game):
        self.game = game
        self.last_running_state = None # Force update
        display_name = game.alias if game.alias else game.name
        self.name_label.setText(display_name)
        self.version_label.setText(f"Version: {game.version}")
        self.playtime_label.setText(f"Playtime: {format_playtime(game.playtime)}")
        self.categories_label.setText(f"Categories: {', '.join(game.categories)}")
        self.args_bar.setText(game.args)

        # Handle image loading
        image_path = os.path.join(CACHE_FOLDER, get_hashed_file(hash_url(game.link), ".png"))
        self.logger.info(f"Loading image from: {image_path}")
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                self.image_label.setVisible(True)
            else:
                self.image_label.setText("Failed to load image")
                self.image_label.setVisible(True)
        else:
            self.logger.warning(f"Image not found at: {image_path}")
            self.image_label.setText("No Image")
            self.image_label.setVisible(True)


        # Update button visibility
        is_installed = "Installed" in game.categories
        self.launch_button.setVisible(is_installed)
        self.uninstall_button.setVisible(is_installed)
        self.update_button.setVisible(bool(is_installed and game.has_update))
        self.install_button.setVisible(not is_installed)

    def arg_callback(self, text):
        if hasattr(self, 'game'):
            self.game.args = text
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            if self.game.name in data:
                data[self.game.name]["args"] = text
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)

    def install(self):
        if hasattr(self, 'game'):
            self.libary.my_parrent.update_callback(self.game.link)

    def uninstall(self):
        if hasattr(self, 'game') and self.game.is_running:
            QMessageBox.warning(self, "Cannot Uninstall", "Please stop the game before uninstalling.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Confirm Uninstall")
        dialog.setStyleSheet("""
            QDialog { background-color: #2b2b2b; color: white; font-size: 14px; }
            QCheckBox, QLabel { font-size: 14px; }
            QPushButton { background: #444; border: none; padding: 8px 15px; border-radius: 8px; color: white; }
            QPushButton:hover { background: #555; }
        """)

        layout = QVBoxLayout()
        label = QLabel("Are you sure you want to uninstall this game?")
        layout.addWidget(label)
        delete_saves_checkbox = QCheckBox("Also delete save data")
        layout.addWidget(delete_saves_checkbox)
        
        button_layout = QHBoxLayout()
        yes_button = QPushButton("Yes")
        no_button = QPushButton("No")
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        yes_button.clicked.connect(lambda: self.confirm_uninstall(dialog, delete_saves_checkbox.isChecked()))
        no_button.clicked.connect(dialog.reject)
        dialog.exec()

    def confirm_uninstall(self, dialog, delete_saves):
        dialog.accept()
        if hasattr(self, 'game') and not self.game.is_running:
            try:
                shutil.rmtree(os.path.join(os.getcwd(), "Games", self.game.name))
                self.libary.load_games()
            except FileNotFoundError:
                self.logger.error("Game folder not found for uninstall.")

    def add_to_category(self):
        if not hasattr(self, 'game'):
            return

        new_category, ok = QInputDialog.getText(self, "New Category", "Enter category name:")
        if ok and new_category and new_category not in ["Installed", "Not Installed"]:
            if new_category not in self.game.categories:
                self.game.categories.append(new_category)
                
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            if self.game.name in data and new_category not in data[self.game.name]["categorys"]:
                data[self.game.name]["categorys"].append(new_category)
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
                
            self.libary.update_list()

    def remove_from_category(self):
        if not hasattr(self, 'game'):
            return

        selected_item = self.libary.game_list.selectedItems()
        if not selected_item:
            return
            
        parent_item = selected_item[0].parent()

        if parent_item:
            category_name = parent_item.text(0)

            if category_name in ["Installed", "Not Installed"]:
                return

            if category_name in self.game.categories:
                self.game.categories.remove(category_name)
            
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            if self.game.name in data and category_name in data[self.game.name]["categorys"]:
                data[self.game.name]["categorys"].remove(category_name)
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)

            self.libary.update_list()

    def set_path(self):
        if not hasattr(self, 'game'):
            return
            
        path = os.path.join(os.getcwd(), "Games", self.game.name)
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Executable File", path, "Executable Files (*.exe)")
        
        if file_path:
            rel_path = os.path.relpath(file_path, os.getcwd()).replace("/", "\\")
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            if self.game.name in data:
                data[self.game.name]["exe"] = rel_path
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
                
                # Update current game object
                self.game.start_path = rel_path
                args = self.game.args
                if isinstance(args, str):
                    args_list = args.split(" ")
                elif isinstance(args, list):
                    args_list = args
                else:
                    args_list = []
                    
                self.game.run_instance = GameInstance(self.game.name, rel_path, args_list, self.game, self.libary)
                self.logger.info(f"Updated game path to: {rel_path}")
