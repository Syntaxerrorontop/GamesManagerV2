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
                                        get_png, get_screenshots, get_hashed_file, _game_naming, 
                                        _get_version_steamrip, format_playtime, )
from .utility.utility_vars import CONFIG_FOLDER, CACHE_FOLDER
from .GameDetailsWidget import GameDetailsWidget
from .utility.game_classes import Game, GameInstance

class MediaDownloader(QThread):
    finished = pyqtSignal(str)

    def __init__(self, url, hash_val, cache_folder, scraper):
        super().__init__()
        self.url = url
        self.hash_val = hash_val
        self.cache_folder = cache_folder
        self.scraper = scraper

    def run(self):
        try:
            # 1. Fetch HTML once
            html_content = self.scraper.get_html(self.url)
            
            # 2. Handle Main Image
            main_img_name = f"{self.hash_val}.png"
            main_img_path = os.path.join(self.cache_folder, main_img_name)
            
            if not os.path.exists(main_img_path):
                try:
                    image_url = get_png(html_content)
                    if image_url:
                        # Pass only filename, scraper handles the directory
                        self.scraper.download_file(image_url, filename=main_img_name)
                except Exception as e:
                    logging.error(f"Failed to download main image for {self.url}: {e}")

            # 3. Handle Screenshots
            screenshot_urls = get_screenshots(html_content)
            for i, shot_url in enumerate(screenshot_urls):
                # Extract extension from URL, default to .jpg if missing
                ext = "jpg"
                if "." in shot_url.split("/")[-1]:
                     ext = shot_url.split("/")[-1].split(".")[-1]
                     # Basic validation of extension
                     if len(ext) > 4 or "/" in ext: 
                         ext = "jpg"

                shot_name = f"{self.hash_val}_screenshot_{i+1}.{ext}"
                shot_path = os.path.join(self.cache_folder, shot_name)
                
                # Check if file exists (ignoring extension mismatch for now, just checking existence)
                if not os.path.exists(shot_path):
                    try:
                        self.scraper.download_file(shot_url, filename=shot_name)
                    except Exception as e:
                        logging.error(f"Failed to download screenshot {i+1} for {self.url}: {e}")

            # Emit main image path for UI update
            self.finished.emit(main_img_path)

        except Exception as e:
            logging.error(f"MediaDownloader failed for {self.url}: {e}")
            self.finished.emit("")

class Libary(QWidget):
    update_list_signal = pyqtSignal()
    start_media_download_signal = pyqtSignal(str, str)

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
        # Defer game loading to allow UI to render first
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, self.load_games)

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
        self.start_media_download_signal.connect(self.start_media_downloader)

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
        
        self.media_downloaders = []

        # 1. Fast: Populate Game Objects and UI
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
        
        self.update_list()
        
        if self.startup:
            self.startup = False
            self.check_thread.start()

        # 2. Background: Check for missing media
        threading.Thread(target=self._background_media_check, args=(cache_folder,), daemon=True).start()

    def _background_media_check(self, cache_folder):
        """Checks for missing media in a background thread and signals to download if needed."""
        for game in self.games:
            hash_val = hash_url(game.link)
            
            # Check for Main Image (png)
            main_img_exists = os.path.exists(os.path.join(cache_folder, f"{hash_val}.png"))
            
            # Check for Screenshots (check for likely extensions)
            # We assume existence if ANY valid extension exists for that slot
            extensions = [".png", ".jpg", ".jpeg"]
            
            screen1_exists = any(os.path.exists(os.path.join(cache_folder, f"{hash_val}_screenshot_1{ext}")) for ext in extensions)
            screen2_exists = any(os.path.exists(os.path.join(cache_folder, f"{hash_val}_screenshot_2{ext}")) for ext in extensions)
            
            if not main_img_exists or not screen1_exists or not screen2_exists:
                self.start_media_download_signal.emit(game.link, hash_val)
                time.sleep(0.05) 

    def start_media_downloader(self, link, hash_val):
        """Slot to start the media downloader from the main thread."""
        downloader = MediaDownloader(link, hash_val, CACHE_FOLDER, self.my_parrent.scraper)
        downloader.finished.connect(self.on_media_downloaded)
        self.media_downloaders.append(downloader)
        downloader.start()

    def on_media_downloaded(self, image_path):
        if self.selected_game and image_path and str(hash_url(self.selected_game.link)) in image_path:
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
        for downloader in self.media_downloaders:
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