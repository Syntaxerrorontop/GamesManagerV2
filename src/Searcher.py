import os
import logging
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QListWidget, QPushButton,
    QLabel, QMessageBox, QListWidgetItem
)

from .utility.utility_functions import save_json, load_json, hash_url, get_name_from_url, cloud_flare_request
from .utility.utility_vars import CONFIG_FOLDER, CACHE_FOLDER

# Scraper
def fetch_game_list(scraper):
    try:
        response = scraper.get_html("https://steamrip.com/games-list-page/")
        data = {}
        if response:
            soup = BeautifulSoup(response, "html.parser")
            game_list_container = soup.select_one("#tie-block_1793 > div > div.mag-box-container.clearfix")

            if game_list_container:
                for upper_container in game_list_container.find_all(class_="az-list-container"):
                    for item in upper_container.find_all(class_="az-list"):
                        for game in item.find_all(class_="az-list-item"):
                            href = game.find("a")["href"]
                            url = "https://steamrip.com" + href
                            game_name = get_name_from_url(url)
                            data[game_name] = href
                save_json(os.path.join(CACHE_FOLDER,"CachedGameList.json"), data)
            else:
                logging.error("Game list not found in HTML.")
                data = load_json(os.path.join(CACHE_FOLDER,"CachedGameList.json"),)
        else:
            logging.error(f"Failed to fetch page: {response.status_code}")
            data = load_json(os.path.join(CACHE_FOLDER,"CachedGameList.json"),)
    except Exception as e:
        logging.error(f"Error fetching game list: {e}")
        data = load_json(os.path.join(CACHE_FOLDER,"CachedGameList.json"),)

    return data
# Stylized GameListWidget
class GameListWidget(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.call_here = parent
        self.setStyleSheet(self.stylesheet())
        self.data = fetch_game_list(self.call_here.scraper)
        self.selected_game = None
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Left side (search + list)
        left_layout = QVBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Suche nach Spielen...")
        self.search_input.textChanged.connect(self.update_filter)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("gameList")
        self.list_widget.itemClicked.connect(self.game_selected)

        left_layout.addWidget(self.search_input)
        left_layout.addWidget(self.list_widget)

        # Right side (info + buttons)
        right_layout = QVBoxLayout()
        self.info_label = QLabel("No game selected")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("infoLabel")

        self.add_btn = QPushButton("Add to Library")
        self.download_btn = QPushButton("Download")

        self.add_btn.clicked.connect(self.add_to_library)
        self.download_btn.clicked.connect(self.download_game)

        right_layout.addWidget(self.info_label)
        right_layout.addWidget(self.add_btn)
        right_layout.addWidget(self.download_btn)
        right_layout.addStretch()

        # Layout proportions
        main_layout.addLayout(left_layout, 3)
        main_layout.addLayout(right_layout, 1)

        # Populate list
        self.update_list(self.data.keys())

    def update_filter(self):
        query = self.search_input.text().lower()
        filtered = [key for key in self.data.keys() if query in key.lower()]
        self.update_list(filtered)

    def update_list(self, keys):
        self.list_widget.clear()
        for key in sorted(keys):
            item = QListWidgetItem(key)
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.list_widget.addItem(item)

    def game_selected(self, item):
        self.selected_game = item.text()
        self.info_label.setText(f"Selected:\n{self.selected_game}")

    def add_to_library(self):
        if not self.selected_game:
            QMessageBox.warning(self, "No Selection", "Please select a game.")
            return
        url = "https://steamrip.com" + self.data[self.selected_game]
        
        data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
        if not hash_url(url) in data.keys():
            data[hash_url(url)] = {"args": "", "playtime": 0, "exe": "", "version": "", "link": url, "alias": get_name_from_url(url), "categorys": []}
            
            save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
        
        else:
            logging.warning("Game already in libary")

    def download_game(self):
        if not self.selected_game:
            QMessageBox.warning(self, "No Selection", "Please select a game.")
            return
        url = "https://steamrip.com" + self.data[self.selected_game]
        if url:
            if not hash_url(url) in os.listdir(os.path.join(os.getcwd(), "Games")):
                self.call_here.update_callback(url)
            else:
                logging.warning("Game Already Downlaoded")
        else:
            QMessageBox.critical(self, "Error", "Download URL not found.")

    def stylesheet(self):
        return """
            QWidget {
                background-color: #222;
                color: white;
                font-size: 16px;
                font-family: 'Montserrat', sans-serif;
            }
            QLineEdit {
                background: #333;
                border: 2px solid #444;
                border-radius: 10px;
                padding: 8px;
                color: white;
            }
            QListWidget#gameList {
                background: #333;
                border-radius: 10px;
                padding: 5px;
                color: white;
                border: none;
            }
            QListWidget#gameList::item {
                padding: 5px;
            }
            QListWidget#gameList::item:selected {
                background-color: #444;
                border-radius: 6px;
            }
            QLabel#infoLabel {
                background-color: #2c2c2c;
                border: 1px solid #3c3c3c;
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 10px;
            }
            QPushButton {
                background-color: #3a3a3a;
                border: 1px solid #5a5a5a;
                border-radius: 10px;
                padding: 8px;
                color: white;
            }
            QPushButton:hover {
                background-color: #505050;
            }
            QPushButton:pressed {
                background-color: #3f3f3f;
            }
        """

