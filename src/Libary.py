from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (QTreeWidgetItem, QTreeWidget, QVBoxLayout, QHBoxLayout, 
                             QLineEdit, QLabel, QPushButton, QInputDialog, QWidget, 
                             QFileDialog, QDialog, QCheckBox, QFrame, QSplitter)
import os
import time
import json
import logging
import threading
import subprocess
import psutil
import shutil

from .utility.utility_functions import (save_json, load_json, hash_url, get_name_from_url, 
                                        get_png, get_hashed_file, _game_naming, 
                                        _get_version_steamrip, format_playtime, )
from .utility.utility_vars import CONFIG_FOLDER, CACHE_FOLDER
from .GameDetailsWidget import GameDetailsWidget
from .utility.game_classes import Game, GameInstance

class ImageDownloader(QThread):
    finished = pyqtSignal(str)

    def __init__(self, url, path, scraper):
        super().__init__()
        self.url = url
        self.path = path
        self.scraper = scraper

    def run(self):
        try:
            image_url = get_png(self.scraper.get_html(self.url))
            self.scraper.download_file(image_url, self.path, )
            self.finished.emit(self.path)
        except Exception as e:
            logging.error(f"Failed to download image from {self.url}: {e}")
            self.finished.emit("")

class Libary(QWidget):
    update_list_signal = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.games = []
        self.selected_game = None
        self.my_parrent = parent
        self.cookies = None
        self.logger = logging.getLogger('GameLibrary')
        
        logging.basicConfig(level=logging.INFO)
        self.logger.info('Game Library initialized with basic logging')
        
        self.init_ui()
        self.load_games()

    def init_ui(self):
        self._create_widgets()
        self._create_layouts()
        self._connect_signals()
        self._apply_stylesheet()

        self.toggle_details(False)
        self.update_list()
        
        self.startup = True
        self.check_thread = threading.Thread(target=self.check_for_updates, daemon=True)

    def _create_widgets(self):
        self.game_data = {}
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search for games...")

        self.game_list = QTreeWidget()
        self.game_list.setHeaderHidden(True)

        self.details_widget = GameDetailsWidget(self)

    def _create_layouts(self):
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.search_bar)

        splitter = QSplitter(Qt.Horizontal)
        
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.addWidget(self.game_list)
        
        splitter.addWidget(list_widget)
        splitter.addWidget(self.details_widget)
        
        splitter.setSizes([300, 1000])

        main_layout.addWidget(splitter)

    def _connect_signals(self):
        self.search_bar.textChanged.connect(self.update_list)
        self.game_list.itemClicked.connect(self.show_game_details)
        self.update_list_signal.connect(self.update_list)

    def _apply_stylesheet(self):
        try:
            with open("src/Libary.qss", "r") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            self.logger.warning("Stylesheet not found.")

    def toggle_details(self, show):
        self.details_widget.setVisible(show)

    def load_games(self):
        self.games = []
        games_folder = os.path.join(os.getcwd(), "Games")
        if not os.path.exists(games_folder):
            os.makedirs(games_folder)
        
        cache_folder = CACHE_FOLDER
        if not os.path.exists(cache_folder):
            os.makedirs(cache_folder)

        game_files = os.listdir(games_folder)
        
        self.game_data = load_json(os.path.join(CONFIG_FOLDER , "games.json"))
        if not self.game_data:
             self.game_data = {}
        
        self.image_downloaders = []

        for key, game_info in self.game_data.items():
            is_installed = key in game_files
            
            if "categorys" not in game_info:
                game_info["categorys"] = []

            game_instance = Game(key, game_info.get("version", "N/A"), is_installed, 
                                 game_info.get("exe"), game_info.get("args"), 
                                 game_info.get("playtime"), game_info.get("link"), 
                                 game_info.get("alias"), game_info.get("categorys"), 
                                 libary_instance=self)
            self.games.append(game_instance)
            
            hash_val = hash_url(game_info['link'])
            extension = ".png"
            filename = get_hashed_file(hash_val, extension)
            full_image_path = os.path.join(cache_folder, filename)

            if not os.path.exists(full_image_path):
                downloader = ImageDownloader(game_info['link'], filename, self.my_parrent.scraper)
                downloader.finished.connect(self.on_image_downloaded)
                self.image_downloaders.append(downloader)
                downloader.start()

        if self.startup:
            self.startup = False
            self.check_thread.start()
            
        self.update_list()

    def on_image_downloaded(self, image_path):
        if self.selected_game and get_hashed_file(hash_url(self.selected_game.link), ".png") in image_path:
            self.details_widget.set_game(self.selected_game)

    def update_list(self):
        self.game_list.clear()
        search_text = self.search_bar.text().lower()

        sorted_games = {}
        for game in self.games:
            if search_text in game.name.lower() or (game.alias and search_text in game.alias.lower()):
                for category in game.categories:
                    if category not in sorted_games:
                        sorted_games[category] = []
                    sorted_games[category].append(game)

        if not sorted_games:
            no_games_item = QTreeWidgetItem(["No games found."])
            self.game_list.addTopLevelItem(no_games_item)
            self.details_widget.setVisible(False)
            return

        for category, games in sorted(sorted_games.items()):
            category_item = QTreeWidgetItem([f"{category}"])
            self.game_list.addTopLevelItem(category_item)
            category_item.setExpanded(True)

            for game in sorted(games, key=lambda g: g.alias or g.name):
                display_name = game.alias if game.alias else game.name
                game_item = QTreeWidgetItem([display_name])

                if "Not Installed" in game.categories:
                    game_item.setForeground(0, Qt.gray)
                category_item.addChild(game_item)

    def show_game_details(self, item, column):
        if item and item.parent():
            game_name = item.text(0)
            game_found = None
            for game in self.games:
                if (game.alias and game.alias == game_name) or (not game.alias and game.name == game_name):
                    game_found = game
                    break
            
            if game_found:
                self.selected_game = game_found
                self.details_widget.set_game(game_found)
                self.toggle_details(True)
    
    def cleanup(self):
        # Stop any running threads
        for downloader in self.image_downloaders:
            downloader.quit()
            downloader.wait()

    def check_for_updates(self):
        userconfig = load_json(os.path.join(CONFIG_FOLDER, "userconfig.json"))
        if not userconfig.get("autoupdates", False):
            return

        for game in self.games:
            if "Installed" in game.categories:
                game.check_for_update(self.my_parrent.scraper)
        self.update_list_signal.emit()