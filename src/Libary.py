from PyQt5.QtCore import Qt,  QThread, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QTreeWidgetItem, QTreeWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QInputDialog, QWidget, QFileDialog, QDialog, QCheckBox
import os, time, json, logging, threading, subprocess, psutil, shutil

from .utility.utility_functions import save_json, load_json, hash_url, get_name_from_url, get_png, get_hashed_file, _game_naming, _get_version_steamrip
from .utility.utility_vars import CONFIG_FOLDER, CACHE_FOLDER

class GameInstance:
    def __init__(self, name, path, args, play_button, parrent):
        self.game_name = name
        self.executable_path = path
        
        # Get logger from parent
        self.logger = getattr(parrent, 'logger', logging.getLogger('GameInstance'))
        
        self.logger.debug(f"🎮 Creating GameInstance for: {name}")
        
        if os.path.exists(path):
            self.executable_path = os.path.join(os.getcwd(), path)
            self.logger.info(f"✅ Game executable found: {self.executable_path}")
        else:
            self.logger.error(f"🚫 Path not found: {path}")
        
        self._start_time: float = 0
        self.args = args
        self.logger.debug(f"🔧 Game arguments: {args}")
        
        self.parrent = parrent
        self.__process = None
        self.qt_play_button = play_button
        
        self.logger.info(f"🎯 GameInstance created successfully for '{name}'")
    
    def _start_playtime(self):
        self._start_time = time.time()
        self.logger.debug(f"⏱️ Playtime tracking started for {self.game_name}")
    
    def start(self):
        self.logger.info(f"🚀 Starting game: {self.game_name}")
        
        if self.__process:
            self.logger.warning(f"⚠️ Game {self.game_name} already running, stopping first...")
            self.close()
            self.qt_play_button.setText("Play")
            return None
            
        self.parrent.is_running = True
        self.qt_play_button.setText("Beenden")
        
        self.logger.debug(f"📁 Executable path: {self.executable_path}")
        self.logger.debug(f"📝 Working directory: {os.path.dirname(self.executable_path)}")
        
        self._start_playtime()
        run_data = [self.executable_path] + self.args
        
        try:
            self.__process = subprocess.Popen(run_data, cwd=os.path.dirname(self.executable_path))
            self.logger.info(f"✅ Game {self.game_name} started successfully (PID: {self.__process.pid})")
        except Exception as e:
            self.logger.error(f"🚫 Failed to start {self.game_name}: {e}")
            self.parrent.is_running = False
            self.qt_play_button.setText("Play")
    
    def wait(self):
        if self.__process:
            self.logger.info(f"⏳ Waiting for {self.game_name} to finish...")
            try:
                return_code = self.__process.wait()
                self.logger.info(f"🏁 Game {self.game_name} finished with exit code: {return_code}")
            except AttributeError:
                self.logger.warning(f"⚠️ Process for {self.game_name} was unexpectedly terminated")
        else:
            self.logger.warning(f"⚠️ Cannot wait for {self.game_name} - no process running")

        played_time = time.time() - self._start_time
        self.logger.info(f"⏱️ {self.game_name} played for {played_time:.2f} seconds")
        self.qt_play_button.setText("Starten")
        self.update_playtime(played_time)

    
    def close(self):
        self.logger.info(f"🚫 Closing {self.game_name}...")
        
        if not self.__process:
            self.logger.warning(f"⚠️ No process to close for {self.game_name}")
            self.parrent.is_running = False
            return
            
        try:
            parent = psutil.Process(self.__process.pid)
            self.logger.debug(f"🔍 Found parent process (PID: {parent.pid})")
            
            children = parent.children(recursive=True)
            if children:
                self.logger.debug(f"👶 Terminating {len(children)} child processes...")
                for child in children:
                    child.terminate()
            
            self.logger.debug(f"🚫 Terminating parent process {parent.pid}...")
            parent.terminate()
            parent.wait(timeout=5)
            
            if parent.is_running():
                self.logger.warning(f"⚔️ Process {parent.pid} didn't terminate gracefully, forcing kill...")
                parent.kill()
            
            self.__process = None
            self.logger.info(f"✅ Successfully closed {self.game_name}")
            
        except psutil.NoSuchProcess:
            self.logger.debug(f"💭 Process for {self.game_name} no longer exists")
            self.__process = None
            self.start()
        except Exception as e:
            self.logger.error(f"🚫 Error closing {self.game_name}: {e}")
        
        self.parrent.is_running = False
    
    def update_playtime(self, playtime: float):
        self.logger.debug(f"💾 Updating playtime for {self.game_name}: +{playtime:.2f}s")
        
        try:
            config_path = os.path.join(CONFIG_FOLDER, "games.json")
            data = load_json(config_path)
            
            if self.game_name not in data:
                self.logger.warning(f"⚠️ Game {self.game_name} not found in games.json, creating entry...")
                data[self.game_name] = {"playtime": 0}
            
            old_playtime = float(data[self.game_name].get("playtime", 0))
            new_playtime = int(old_playtime + playtime)
            
            data[self.game_name]["playtime"] = new_playtime
            save_json(config_path, data)
            
            self.logger.info(f"✅ Playtime updated for {self.game_name}: {old_playtime:.0f}s → {new_playtime}s")
            
        except json.JSONDecodeError as e:
            self.logger.error(f"🚫 JSON decode error while saving playtime: {e}")
        except FileNotFoundError as e:
            self.logger.error(f"📁 Games config file not found: {e}")
        except Exception as e:
            self.logger.error(f"🚫 Unexpected error updating playtime: {e}")

class Game:
    def __init__(self, name, version, is_installed, start_path, args, playtime, link, alias, play_button ,categories=[]):
        # Set up basic logger
        self.logger = logging.getLogger('Game')
        self.logger.debug(f"🎮 Creating Game object: {name}")
        
        if is_installed:
            categories = ["Installed"] + categories
            self.logger.debug(f"✅ Game {name} is installed")
        else:
            categories = ["Not Installed"] + categories
            self.logger.debug(f"📦 Game {name} is not installed")
            
        self.args = args
        self.name = name
        self.version = version
        self.start_path = start_path
        self.playtime = playtime
        self.link = link
        self.alias = alias
        self.has_update = None
        self.categories = categories
        self.is_running = False
        
        if is_installed:
            self.logger.debug(f"🚀 Creating GameInstance for {name}...")
            if isinstance(args, str):
                self.run_instance = GameInstance(name, start_path, args.split(" "), play_button, self)
            elif isinstance(args, list):
                self.run_instance = GameInstance(name, start_path, args, play_button, self)
        else:
            self.logger.debug(f"❌ Not creating GameInstance for uninstalled game: {name}")
            self.run_instance = None
        
        self.logger.info(f"✅ Game '{name}' initialized successfully")
    
    def start(self):
        self.logger.info(f"🏁 Starting game: {self.name}")
        
        if not self.run_instance:
            self.logger.error(f"🚫 Cannot start {self.name} - no run instance (game not installed?)")
            return
            
        try:
            self.run_instance.start()
            _game_thread = threading.Thread(target=self.run_instance.wait, daemon=True)
            _game_thread.start()
            self.logger.info(f"🚀 Game {self.name} launched in background thread")
        except Exception as e:
            self.logger.error(f"🚫 Failed to start {self.name}: {e}")
            self.logger.error(f"🛠️ Please check the executable path manually")
    
    def check_for_update(self, scraper):
        if self.has_update == None:
            self.logger.debug(f"🔄 Checking for updates for {self.name}...")
            try:
                remote_version = _get_version_steamrip(self.link, scraper)
                self.has_update = remote_version != self.version
                
                if self.has_update:
                    self.logger.info(f"🆕 Update available for {self.name}: {self.version} → {remote_version}")
                else:
                    self.logger.debug(f"✅ {self.name} is up to date (v{self.version})")
                    
            except Exception as e:
                self.logger.error(f"🚫 Error checking updates for {self.name}: {e}")
                self.has_update = False
        else:
            self.logger.debug(f"📝 Using cached update status for {self.name}: {self.has_update}")
            
        return self.has_update

class FolderWatcher(QThread):
    folder_changed = pyqtSignal(str)  # Signal, wenn sich die Ordnerstruktur ändert

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path
        self.running = True
        self.last_state = self.get_folder_state()

    def get_folder_state(self):
        """Speichert die aktuelle Struktur (Dateien + Unterordner)"""
        folder_state = set()
        for root, dirs, files in os.walk(self.folder_path):
            for name in files:
                folder_state.add(os.path.join(root, name))
            for name in dirs:
                folder_state.add(os.path.join(root, name))
        return folder_state

    def run(self):
        """Läuft dauerhaft und überprüft Änderungen"""
        while self.running:
            time.sleep(1)  # Prüft alle 2 Sekunden
            current_state = self.get_folder_state()
            if current_state != self.last_state:
                self.folder_changed.emit("")
                self.last_state = current_state

    def stop(self):
        """Stoppt den Thread"""
        self.running = False

class Libary(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.games = []
        self.selected_game = None
        self.my_parrent = parent
        self.cookies = None
        
        # Setup colorful Minecraft-style logging using scraper's system
        try:
            self.my_parrent.scraper._setup_colored_logging()
            self.logger = logging.getLogger('GameLibrary')
            self.logger.info('🎮 Game Library initialized with colorful logging!')
        except AttributeError:
            # Fallback if scraper doesn't have the method yet
            self.logger = logging.getLogger('GameLibrary')
            logging.basicConfig(level=logging.INFO)
            self.logger.info('Game Library initialized with basic logging')
        
        self.init_ui()
        self.load_games()

    def init_ui(self):
        layout = QVBoxLayout()
        self.game_data = {}
        self.setStyleSheet("""
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
            QTreeWidget {
                background: #333;
                border-radius: 10px;
                padding: 5px;
                color: white;
                border: none;
            }
            QTreeWidget::item {
                padding: 5px;
            }
            QTreeWidget::header {
                background: #333;
                color: white;
                border: none;
                font-size: 14px;
            }
            QPushButton {
                background: #444;
                border: none;
                padding: 10px;
                border-radius: 10px;
                color: white;
            }
            QPushButton:hover {
                background: #555;
            }
        """)
        
        self.watcher = FolderWatcher(os.path.join(os.getcwd(), "Games"))
        self.watcher.folder_changed.connect(self.load_games)
        self.watcher.start()

        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Suche nach Spielen...")
        self.search_bar.textChanged.connect(self.update_list)
        self.search_bar.setMaximumWidth(580)
        layout.addWidget(self.search_bar)
        content_layout = QHBoxLayout()
        self.game_list = QTreeWidget()
        self.game_list.setHeaderLabels(["Spiele und Kategorien"])
        self.game_list.setHeaderHidden(True)  # Versteckt den Header
        self.game_list.setStyleSheet("QTreeWidget::item { background: transparent; }")
        self.game_list.setMaximumWidth(600)
        #self.game_list.setDragEnabled(True)  # Aktiviert das Ziehen
        #self.game_list.setAcceptDrops(True)  # Aktiviert das Ablege
        #self.game_list.setDragDropMode(QAbstractItemView.InternalMove)  # Ermöglicht das Verschieben innerhalb des Widgets
        self.game_list.itemClicked.connect(self.show_game_details)
        content_layout.addWidget(self.game_list)

        self.details_widget = QWidget()
        self.details_layout = QVBoxLayout()
        self.details_label = QLabel("Wähle ein Spiel aus der Liste.")
        self.details_layout.addWidget(self.details_label)

        self.launch_button = QPushButton("Starten")
        self.launch_button.setFixedWidth(300)
        self.launch_button.clicked.connect(lambda: self.selected_game.start())
        self.remove_from_category_button = QPushButton("Remove from Category")
        self.remove_from_category_button.setFixedWidth(300)
        self.remove_from_category_button.clicked.connect(self.remove_from_category)
        self.uninstall_button = QPushButton("Deinstallieren")
        self.uninstall_button.setFixedWidth(300)
        self.uninstall_button.clicked.connect(self.uninstall)
        self.remove_category_button = QPushButton("Remove Category")
        self.remove_category_button.setFixedWidth(300)
        self.remove_category_button.clicked.connect(self.remove_selected_category)
        self.add_category_button = QPushButton("Zur Kategorie hinzufügen")
        self.add_category_button.setFixedWidth(300)
        self.add_category_button.clicked.connect(self.add_to_category)
        
        self.install_button = QPushButton("📥 Installieren")
        self.install_button.setFixedWidth(300)
        self.install_button.setVisible(False)
        self.install_button.clicked.connect(self.install)
        
        self.update_button = QPushButton("🔄 Update installieren")
        self.update_button.setFixedWidth(300)
        self.update_button.setVisible(False)
        self.update_button.clicked.connect(self.install)
        
        self.image_label = QLabel()
        self.image_label.setFixedSize(1280, 720)
        
        
        self.args_bar = QLineEdit()
        self.args_bar.setPlaceholderText("Gib hier deine Argumente ein...")  # Optionaler Platzhaltertext
        self.args_bar.textChanged.connect(self.arg_callback)
        self.args_bar.setStyleSheet("""
            QLineEdit {
                background: #333;
                border: 2px solid #444;
                border-radius: 10px;
                padding: 8px;
                color: white;
                 font-family: 'Montserrat', sans-serif;  /* Use the system default font */
            }""")
        
         # Layout for buttons and actions
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.install_button)
        button_layout.addWidget(self.launch_button)
        button_layout.addStretch()
        button_layout.addWidget(self.update_button)
        button_layout.addStretch()
        button_layout.addWidget(self.uninstall_button)

        # Category buttons (add/remove)
        category_layout = QHBoxLayout()
        category_layout.addWidget(self.add_category_button)
        category_layout.addStretch()
        category_layout.addWidget(self.remove_from_category_button)
        
        self.manuel_path_button = QPushButton("Set Game Path")
        self.manuel_path_button.setFixedWidth(300)
        self.manuel_path_button.clicked.connect(self.set_path)
        self.manuel_path_button.setVisible(False)
        
        faile_safe_layout = QHBoxLayout()
        faile_safe_layout.addStretch()
        faile_safe_layout.addWidget(self.manuel_path_button)

        # Main container for the buttons and category controls
        button_container_layout = QVBoxLayout()
        button_container_layout.addStretch()
        button_container_layout.addWidget(self.args_bar)
        button_container_layout.addLayout(category_layout)  # Add category controls
        button_container_layout.addLayout(button_layout)  # Add main action buttons
        button_container_layout.addLayout(faile_safe_layout)
        button_container_layout.addWidget(self.remove_category_button)

        # Main layout for the details widget
        self.details_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignTop)  # Add image at the top
        self.details_layout.addLayout(button_container_layout)

        # Set layout for the details widget
        self.details_widget.setLayout(self.details_layout)

        # Add everything to the main content layout
        content_layout.addWidget(self.details_widget)
        layout.addLayout(content_layout)

        # Set the main layout for the window
        self.setLayout(layout)

        self.toggle_details(False)
        self.update_list()
        
        self.startup = True
        self.check_thread = threading.Thread(target=self.check_for_updates, daemon=True)
    
    def uninstall(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Deinstallation bestätigen")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2b2b2b;
                color: white;
                font-size: 14px;
            }
            QCheckBox, QLabel {
                font-size: 14px;
            }
            QPushButton {
                background: #444;
                border: none;
                padding: 8px 15px;
                border-radius: 8px;
                color: white;
            }
            QPushButton:hover {
                background: #555;
            }
        """)

        layout = QVBoxLayout()

        label = QLabel("Möchtest du das Spiel wirklich deinstallieren?")
        layout.addWidget(label)

        delete_saves_checkbox = QCheckBox("Speicherdaten ebenfalls löschen")
        delete_saves_checkbox.setChecked(False)
        layout.addWidget(delete_saves_checkbox)

        button_layout = QHBoxLayout()
        yes_button = QPushButton("Ja")
        no_button = QPushButton("Nein")
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        layout.addLayout(button_layout)

        dialog.setLayout(layout)

        # Button-Callbacks
        yes_button.clicked.connect(lambda: self.confirm_uninstall(dialog, delete_saves_checkbox.isChecked()))
        no_button.clicked.connect(dialog.reject)

        dialog.exec()
    
    def confirm_uninstall(self, dialog, delete_saves):
        dialog.accept()
        if self.selected_game and not self.selected_game.is_running:
            shutil.rmtree(os.path.join(os.getcwd(), "Games", self.selected_game.name))
            self.toggle_details(False)
            self.load_games()

    
    def set_path(self):
        path = os.path.join(os.getcwd(), "Games", self.selected_game.name)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable File",
            path,
            "Executable Files (*.exe)"
        )
        file_path = file_path[len(os.getcwd())+1:].replace("/", "\\")
        data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
        data[self.selected_game.name]["exe"] = file_path
        save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
    
    def check_for_updates(self):
        for game in self.games:
            if game.categories[0] == "Not Installed":
                continue
            logging.debug(f"Checking for updates for {game.name}...")
            game.check_for_update(self.my_parrent.scraper)
            time.sleep(1)
            
    def install(self):
        self.my_parrent.update_callback(self.selected_game.link)

    def load_games(self):
        self.games = []
        games_folder = os.path.join(os.getcwd(), "Games")
        if not os.path.exists(games_folder):
            os.makedirs(games_folder)
        
        cache_folder = CACHE_FOLDER
        if not os.path.exists(cache_folder):
            os.makedirs(cache_folder)

        game_files = os.listdir(games_folder)
        #if not game_files:
        #    self.details_label.setText("Keine Spiele gefunden.")
            #return
        
        self.game_data = load_json(os.path.join(CONFIG_FOLDER , "games.json"))
        append_later = []
        pop_later = []
        #self.games = [Game(game, "1.0", True, "w", [],0,"httpslol","THIS IS AN BUG PLEASE REPORT") for game in game_files]
        for key, game in self.game_data.items():
            is_installed = False
            if key in game_files:
                is_installed = True
            if not "categorys" in self.game_data[key].keys():
                self.game_data[key]["categorys"] = []
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), self.game_data)
            game_instance = Game(key, self.game_data[key]["version"], is_installed, self.game_data[key]["exe"], self.game_data[key]["args"], self.game_data[key]["playtime"], self.game_data[key]["link"], self.game_data[key]["alias"], self.launch_button,self.game_data[key]["categorys"])
            self.games.append(game_instance)
            hash = hash_url(self.game_data[key]['link'])
            extension = ".png"

            if self.game_data[key]['alias'] == "":
                self.game_data[key]['alias'] = get_name_from_url(self.game_data[key]['link'])
                os.rename(os.path.join(os.getcwd(), "Games", key), os.path.join(os.getcwd(), "Games", hash))
                temp_data = self.game_data[key]
                append_later.append({"key": hash, "data": temp_data})
                pop_later.append(key)
            if not get_hashed_file(hash, extension) in os.listdir(cache_folder):
                self.my_parrent.scraper.download_file(get_png(self.my_parrent.scraper.get_html(self.game_data[key]['link'])), get_hashed_file(hash, extension))#download_file(self.game_data[key]['link'], os.path.join(cache_folder, get_hashed_file(hash, extension)))
            else:
                logging.debug(f"Image already exists: {hash}")
                #self.game_data[hash] = temp_data
                #self.game_data[hash]['alias'] = get_name_from_url(self.game_data[hash]['link'])
            if is_installed and not os.path.exists(os.path.join(os.getcwd(), self.game_data[key]["exe"]) and self.game_data[key]["exe"] == ""):
                #print("why", os.path.join(os.getcwd(), self.game_data[key]["exe"]))
                path = _game_naming(hash)
                self.game_data[key]["exe"] = path

            elif self.game_data[key]["exe"] == "" and is_installed:
                path = _game_naming(hash)
                self.game_data[key]["exe"] = path
        for item in pop_later:
            try:
                self.game_data.pop(item)
            except KeyError:
                pass
        for item in append_later:
            self.game_data[item["key"]] = item["data"]

        save_json(os.path.join(CONFIG_FOLDER, "games.json"), self.game_data)
        #for key in pop_later:
        #    self.game_data.pop(key)
        
        if self.startup:
            self.startup = False
            self.check_thread.start()
            
        self.update_list()
        

    def update_list(self):
        self.game_list.clear()
        search_text = self.search_bar.text().lower()

        sorted_games = {}
        for game in self.games:
            if search_text in game.name.lower():
                for category in game.categories:
                    if category not in sorted_games:
                        sorted_games[category] = []
                    sorted_games[category].append(game)

        if not sorted_games:
            self.game_list.addTopLevelItem(QTreeWidgetItem(["Keine Spiele gefunden."]))
            self.toggle_details(False)
            return

        for category, games in sorted(sorted_games.items()):
            category_item = QTreeWidgetItem([f"{category}"])
            self.game_list.addTopLevelItem(category_item)
            category_item.setExpanded(True)

            for game in games:
                if game.alias=="":
                    game_item = QTreeWidgetItem([f"{game.name}"])
                else:
                    game_item = QTreeWidgetItem([f"{game.alias}"])
                if "Not Installed" in game.categories:
                    game_item.setForeground(0, Qt.gray)  # Setzt den Text grau
                category_item.addChild(game_item)

    def remove_selected_category(self):
        selected_item = self.game_list.selectedItems()
        
        if not selected_item:
            return
        
        selected_item = selected_item[0]  # Get the first selected item
        if not selected_item.parent():  # Only proceed if it's a category
            category_name = selected_item.text(0)

            # Ensure the category is not "Installed" or "Not Installed"
            if category_name in ["Installed", "Not Installed"]:
                return  # Cannot remove system-defined categories

            # Update all games to remove the category
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            for game in self.games:
                if category_name in game.categories:
                    game.categories.remove(category_name)
                    key = game.name
                    if category_name in data[key]["categorys"]:
                        data[key]["categorys"].remove(category_name)

            # Save updated JSON data
            save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)

            # Remove category from UI
            self.game_list.takeTopLevelItem(self.game_list.indexOfTopLevelItem(selected_item))

            # Refresh the UI
            self.update_list()

    def arg_callback(self, text):
        self.selected_game.args = text
        data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
        self.selected_game.name
        data[self.selected_game.name]["args"] = text
        save_json(os.path.join(CONFIG_FOLDER, "games.json"),data)
    
    def show_game_details(self, item):
        if item.parent():
            game_name = item.text(0)
            category_name = item.parent().text(0)
            for game in self.games:
                if game.alias == game_name:
                    self.details_label.setText(f"Name: {game.name}\nVersion: {game.version}\nKategorien: {', '.join(game.categories)}")
                    # Construct the image path
                    image_path = os.path.join(CACHE_FOLDER, get_hashed_file(hash_url(game.link), ".png"))
                    self.selected_game = game
                    # Load and display the image
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        self.image_label.setPixmap(pixmap)
                        self.image_label.setVisible(True)  # Show image label if the image exists
                    else:
                        self.image_label.setVisible(False)  # Hide if image doesn't exist
                        
                        
                    is_installed = "Installed" in game.categories
                    self.toggle_details(False, skip=True)
                    self.args_bar.setText(str(game.args))
                    self.args_bar.setVisible(True)
                    self.manuel_path_button.setVisible(True)
                    if is_installed:
                        self.launch_button.setVisible(True)
                        self.uninstall_button.setVisible(True)
                        if game.has_update != None:
                            self.update_button.setVisible(game.has_update)
                    else:
                        self.install_button.setVisible(True)
                    
                    if category_name not in ["Installed", "Not Installed"]:
                        self.remove_from_category_button.setVisible(True)
                    else:
                        self.remove_from_category_button.setVisible(False)
                    # Standardmäßig alle Buttons verstecken
                    #self.launch_button.setVisible(False)
                    #self.uninstall_button.setVisible(False)
                    #self.update_button.setVisible(False)
                    #self.install_button.setVisible(False)
                    #self.add_category_button.setVisible(False)

                    #if is_installed:
                    #    self.launch_button.setVisible(True)
                    #    self.uninstall_button.setVisible(True)
                    #    self.update_button.setVisible(game.has_update)  # Nur zeigen, wenn ein Update verfügbar ist
                    #else:
                    #    self.install_button.setVisible(True)

                    # "Zur Kategorie hinzufügen" immer anzeigen
                    self.add_category_button.setVisible(True)
                    break
        else:
            category_name = item.text(0)
            self.toggle_details(False, skip=True)
            if category_name not in ["Installed", "Not Installed"]:
                self.remove_category_button.setVisible(True)
                

    def add_to_category(self):
        if not self.selected_game:
            return

        new_category, ok = QInputDialog.getText(self, "Neue Kategorie", "Kategorie eingeben:")
        if new_category in ["Installed", "Not Installed"]:
            pass
        elif ok and new_category:
            if new_category not in self.selected_game.categories:
                self.selected_game.categories.append(new_category)
            new_category
            key = self.selected_game.name
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            data[key]["categorys"].append(new_category)
            save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
                
            self.update_list()
    
    def remove_from_category(self):
        if not self.selected_game:
            return

        # Get the selected item and its parent category
        selected_item = self.game_list.selectedItems()[0]
        parent_item = selected_item.parent()

        if parent_item:
            category_name = parent_item.text(0)

            # Ensure the category is not "Installed" or "Not Installed"
            if category_name in ["Installed", "Not Installed"]:
                return  # Cannot remove from system-defined categories

            # Remove the category from the selected game's categories
            self.selected_game.categories.remove(category_name)
            
            # Update the data file
            key = self.selected_game.name
            data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
            if category_name in data[key]["categorys"]:
                data[key]["categorys"].remove(category_name)
                save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)

            # Remove the category from the UI by removing the parent item
            parent_item.takeChildren()  # Remove all children (games) of the category
            self.game_list.takeTopLevelItem(self.game_list.indexOfTopLevelItem(parent_item))  # Remove the parent category item

            # Refresh the game list UI to update the categories
            self.update_list()

    def toggle_details(self, visible, skip=False):
        self.details_label.setVisible(visible)
        self.launch_button.setVisible(visible)
        self.uninstall_button.setVisible(visible)
        self.add_category_button.setVisible(visible)
        self.update_button.setVisible(visible)
        self.install_button.setVisible(visible)
        self.remove_from_category_button.setVisible(visible)
        self.remove_category_button.setVisible(visible)
        self.args_bar.setVisible(visible)
        self.manuel_path_button.setVisible(visible)
        if not visible and not skip:
            self.details_label.setText("Wähle ein Spiel aus der Liste.")
    
    def cleanup(self):
        self.watcher.stop()