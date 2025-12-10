from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QSize
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QLineEdit, QDialog, QCheckBox, QFileDialog, QInputDialog,
                             QSizePolicy, QMessageBox, QScrollArea, QFrame)
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
            self.launch_button.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 6px; padding: 6px;")
            self.uninstall_button.setEnabled(False)
        else:
            self.launch_button.setText("Launch")
            self.launch_button.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 6px; padding: 6px;")
            self.uninstall_button.setEnabled(True)

    def init_ui(self):
        # Main Layout
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)

        # Scroll Area for entire details content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setSpacing(15)
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # --- Header (Name + Version) ---
        header_layout = QHBoxLayout()
        self.name_label = QLabel()
        self.name_label.setObjectName("name_label")
        self.name_label.setStyleSheet("font-size: 26px; font-weight: bold; color: white;")
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        self.version_label = QLabel()
        self.version_label.setStyleSheet("font-size: 14px; color: #aaa;")
        header_layout.addWidget(self.version_label)
        self.content_layout.addLayout(header_layout)

        # --- Main Image (Large & Centered) ---
        main_image_container = QWidget()
        main_image_layout = QHBoxLayout(main_image_container)
        main_image_layout.setContentsMargins(0, 10, 0, 10)
        
        self.main_image = QLabel()
        self.main_image.setFixedSize(720, 405) # 16:9 Large format
        self.main_image.setStyleSheet("border: 1px solid #444; border-radius: 8px; background: #222;")
        self.main_image.setAlignment(Qt.AlignCenter)
        
        main_image_layout.addStretch()
        main_image_layout.addWidget(self.main_image)
        main_image_layout.addStretch()
        
        self.content_layout.addWidget(main_image_container)

        # --- Screenshots Section ---
        screenshots_header = QLabel("Screenshots")
        screenshots_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #ddd; margin-left: 5px;")
        self.content_layout.addWidget(screenshots_header)

        # Horizontal scroll area for screenshots
        image_scroll = QScrollArea()
        image_scroll.setWidgetResizable(True)
        image_scroll.setFixedHeight(250) # Reduced height since main image is moved
        image_scroll.setFrameShape(QFrame.NoFrame)
        image_scroll.setStyleSheet("background: transparent;")
        
        image_container = QWidget()
        self.image_layout = QHBoxLayout(image_container)
        self.image_layout.setSpacing(15)
        self.image_layout.setContentsMargins(0, 0, 0, 0)
        
        # Screenshots
        self.screenshot1 = QLabel()
        self.screenshot1.setFixedSize(384, 216) # Smaller 16:9 for gallery
        self.screenshot1.setStyleSheet("border: 1px solid #444; border-radius: 8px; background: #222;")
        self.screenshot1.setAlignment(Qt.AlignCenter)
        self.image_layout.addWidget(self.screenshot1)
        
        self.screenshot2 = QLabel()
        self.screenshot2.setFixedSize(384, 216)
        self.screenshot2.setStyleSheet("border: 1px solid #444; border-radius: 8px; background: #222;")
        self.screenshot2.setAlignment(Qt.AlignCenter)
        self.image_layout.addWidget(self.screenshot2)
        
        self.image_layout.addStretch()
        image_scroll.setWidget(image_container)
        self.content_layout.addWidget(image_scroll)

        # --- Info Section ---
        info_frame = QFrame()
        info_frame.setStyleSheet("background-color: #252525; border-radius: 8px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        
        self.playtime_label = QLabel()
        self.playtime_label.setStyleSheet("font-size: 14px; color: #ddd;")
        info_layout.addWidget(self.playtime_label)

        self.categories_label = QLabel()
        self.categories_label.setStyleSheet("font-size: 14px; color: #ddd;")
        info_layout.addWidget(self.categories_label)

        self.args_bar = QLineEdit()
        self.args_bar.setPlaceholderText("Launch Arguments...")
        self.args_bar.setStyleSheet("background: #333; border: 1px solid #444; padding: 5px; border-radius: 4px; color: white;")
        self.args_bar.textChanged.connect(self.arg_callback)
        info_layout.addWidget(self.args_bar)
        
        self.content_layout.addWidget(info_frame)

        # --- Action Buttons ---
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(10)
        
        self.launch_button = self._create_btn("Launch", "#27ae60")
        self.launch_button.clicked.connect(self.toggle_game_state)
        
        self.install_button = self._create_btn("Install", "#2980b9")
        self.install_button.clicked.connect(self.install)
        
        self.update_button = self._create_btn("Update", "#f39c12")
        self.update_button.clicked.connect(self.install)
        
        self.uninstall_button = self._create_btn("Uninstall", "#c0392b")
        self.uninstall_button.clicked.connect(self.uninstall)
        
        self.button_layout.addWidget(self.launch_button)
        self.button_layout.addWidget(self.install_button)
        self.button_layout.addWidget(self.update_button)
        self.button_layout.addWidget(self.uninstall_button)
        self.button_layout.addStretch()
        
        self.content_layout.addLayout(self.button_layout)

        # --- Tools Section (Secondary Actions) ---
        tools_layout = QHBoxLayout()
        tools_layout.setSpacing(10)
        
        self.add_cat_btn = self._create_btn("Add Category", "#888", outline=True)
        self.add_cat_btn.clicked.connect(self.add_to_category)
        
        self.rem_cat_btn = self._create_btn("Remove Category", "#888", outline=True)
        self.rem_cat_btn.clicked.connect(self.remove_from_category)
        
        self.path_btn = self._create_btn("Set Path", "#888", outline=True)
        self.path_btn.clicked.connect(self.set_path)
        
        self.rem_acc_btn = self._create_btn("Remove Game", "#c0392b", outline=True)
        self.rem_acc_btn.clicked.connect(self.remove_from_account)

        tools_layout.addWidget(self.add_cat_btn)
        tools_layout.addWidget(self.rem_cat_btn)
        tools_layout.addWidget(self.path_btn)
        tools_layout.addWidget(self.rem_acc_btn)
        tools_layout.addStretch()

        self.content_layout.addLayout(tools_layout)
        self.content_layout.addStretch()

    def _create_btn(self, text, bg_color, outline=False):
        btn = QPushButton(text)
        
        if outline:
            style = f"""
                QPushButton {{
                    background-color: transparent;
                    color: {bg_color};
                    border: 1px solid {bg_color};
                    border-radius: 6px;
                    font-weight: 600;
                    padding: 6px 12px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: {bg_color};
                    color: white;
                }}
            """
        else:
            style = f"""
                QPushButton {{
                    background-color: {bg_color};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-weight: bold;
                    padding: 8px 16px; 
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {bg_color}99;
                }}
            """
            
        btn.setStyleSheet(style)
        btn.setCursor(Qt.PointingHandCursor)
        # Remove fixed width to allow flexible sizing based on text
        # btn.setFixedWidth(120) 
        return btn

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
                
                # Remove cached images
                hash_val = hash_url(self.game.link)
                files_to_remove = [
                    os.path.join(CACHE_FOLDER, f"{hash_val}.png"),
                    os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_1.jpg"),
                    os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_1.png"),
                    os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_2.jpg"),
                    os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_2.png")
                ]
                
                for fpath in files_to_remove:
                    if os.path.exists(fpath):
                        try:
                            os.remove(fpath)
                        except OSError:
                            pass
                            
                self.libary.load_games()

    def set_game(self, game):
        self.game = game
        self.last_running_state = None # Force update
        display_name = game.alias if game.alias else game.name
        self.name_label.setText(display_name)
        self.version_label.setText(f"v{game.version}")
        self.playtime_label.setText(f"Playtime: {format_playtime(game.playtime)}")
        self.categories_label.setText(f"Categories: {', '.join(game.categories)}")
        self.args_bar.setText(game.args)

        # Helper to load image to label
        def load_img(label, path):
            if os.path.exists(path):
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    label.setPixmap(pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    label.setVisible(True)
                else:
                    label.setVisible(False)
            else:
                label.setVisible(False)

        hash_val = hash_url(game.link)
        
        # 1. Main Image
        main_path = os.path.join(CACHE_FOLDER, f"{hash_val}.png")
        load_img(self.main_image, main_path)
        
        # 2. Screenshots (try jpg then png)
        # Check extensions manually or assume jpg as preferred
        s1_path = os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_1.jpg")
        if not os.path.exists(s1_path): s1_path = os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_1.png")
        
        s2_path = os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_2.jpg")
        if not os.path.exists(s2_path): s2_path = os.path.join(CACHE_FOLDER, f"{hash_val}_screenshot_2.png")

        load_img(self.screenshot1, s1_path)
        load_img(self.screenshot2, s2_path)

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
