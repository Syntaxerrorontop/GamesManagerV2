import logging
import os
import time
import shutil
import subprocess
import ctypes
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTabWidget, QVBoxLayout
from PyQt5.QtGui import QFontDatabase, QFont

from src.utility.utility_functions import load_json, save_json#, powershell, process_running, kill_process
from src.utility.utility_vars import CONFIG_FOLDER, ASSET_FOLDER, CACHE_FOLDER
from src.utility.utility_classes import File
from src import Libary, Searcher, DownloadManager
from src.scraper import UniversalScraper

class TabWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        logging.debug("Init TabWidget")
        
        self.scraper = UniversalScraper(download_dir=CACHE_FOLDER, headless=False)
        self.scraper.start()
        self.scraper.goto("https://steamrip.com", wait_for_load=True)
        
        self.tab_info = {}
        self.last_tab = "Library"
        self.cookies = None
        
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { 
                border: none; 
                background: #222;
                border-radius: 15px;
            }
            QTabBar::tab {
                background: #444;
                color: white;
                padding: 10px;
                margin: 5px;
                border-radius: 10px;
                min-width: 287px;  /* Breite anpassen */
                max-width: 287px;
                min-height: 40px;  /* Höhe anpassen */
                max-height: 40px;
                font-size: 20px;
                font-family: 'Montserrat', sans-serif; /* Custom Font */
            }
            QTabBar::tab:selected {
                background: #666;
            }
        """)
        
        self.library_tab = Libary.Libary(self)
        self.download_manager = DownloadManager.DownloadManager(self)
        self.search_tab = Searcher.GameListWidget(self)
        self.settings_tab = QWidget()
        self.scripts_tab = QWidget()
        self.feedback_tab = QWidget()
        
        self.add_tab(self.library_tab, "Libary")
        self.add_tab(self.search_tab, "Search")
        self.add_tab(self.download_manager, "Downloads")
        self.add_tab(self.scripts_tab, "Scripts")
        self.add_tab(self.settings_tab, "Settings")
        self.add_tab(self.feedback_tab, "Feedback")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        
        self.tabs.currentChanged.connect(self._on_tab_switch)
    
    def pause_callback(self):
        self.download_manager.download_thread.pause()
    
    def stop_callback(self):
        self.download_manager.download_thread.stop()
    
    def resume_callback(self):
        self.download_manager.download_thread.resume()
    
    def update_callback(self, url):
        self.download_manager.start(url)
    
    def add_tab(self, tab, name):
        index = self.tabs.count()
        self.tabs.addTab(tab, name)
        self.tab_info[index] = name
    
    def _on_tab_switch(self, index):
        if self.tab_info[index] == "Libary":
            self.library_tab.load_games()
        self.last_tab = self.tab_info[index]

class Ui_MainWindow:
    def init(self, mainwindow: QMainWindow):
        self.mainwindow = mainwindow
        
        font_id = QFontDatabase.addApplicationFont(os.path.join(ASSET_FOLDER,"Montserrat-Regular.ttf"))
        if font_id != -1:
            font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
            self.mainwindow.setFont(QFont(font_family, 16))  # Set the default font
        
        self.mainwindow.setWindowTitle("lol")
        self.mainwindow.resize(1920, 1080)
        #self.mainwindow.setFixedSize(1920, 1080)

        
        self.tab_widget = TabWidget()
        self.mainwindow.setCentralWidget(self.tab_widget)
        
        self.mainwindow.setStyleSheet("""
            QMainWindow {
                background-color: #181818;
            }
        """)

def fix_config():
    config_games = load_json(os.path.join(os.getcwd(), "Config", "games.json"))
    if not "Games" in config_games.keys():
        logging.debug("Config is Correct!")
        return
    
    logging.warning("Config Corrupted!")
    logging.info("Please do not close the app while fixing!")
    
    games_from_key = config_games["Games"]
    
    for key, item in games_from_key.items():
        if key not in config_games.keys():
            config_games[key] = item
        
        else:
            try:
                if isinstance(item, list):
                    logging.warning(f"{key} is a list!")
                    logging.info("Removing it...")
                    config_games.pop(key)
                    continue
                
                logging.warning(f"{item['alias']} is badly corrupted. Fixxing")
                game = config_games[key]
                
                game["playtime"] += item["playtime"]
                game["categorys"] += item["categorys"]
                
                logging.warning("Trying to merge Critcal data...")
                time.sleep(0.2)
                if not game["args"] == item["args"]:
                    logging.warning("Args is different!")
                    if game["args"] == "":
                        game["args"] = item["args"]
                        
                if game["args"]== "[]":
                    game["args"] = ""
                        
                elif game["args"] == []:
                    game["args"] = ""
                
                if not game["exe"] == item["exe"]:
                    logging.warning("Exe is different!")
                    if game["exe"] == "":
                        game["exe"] = item["exe"]
                
                if not game["link"] == item["link"]:
                    logging.warning("Link is different!")
                    if game["link"] == "":
                        game["link"] = item["link"]
                
                if not game["alias"] == item["alias"]:
                    logging.warning("Alias is different!")
                    if game["alias"] == "":
                        game["alias"] = item["alias"]
                
                if not game["version"] == item["version"]:
                    logging.warning("Version is different!")
                    if game["version"] == "":
                        game["version"] = item["version"]
                game["categorys"] = list(set(game["categorys"]))
                config_games[key] = game
                logging.info("Done!")
            except Exception as e:
                logging.error(f"Error while merging {key} {e}")
            
    config_games.pop("Games")
    
    save_json(os.path.join(os.getcwd(), "Config", "games.json"), config_games)
    
    logging.info("Config fixed!")

def delete_unaccessary_folder():
    folders = [".Meta", "Cached", "Assets", "Config"]
    for folder in folders:
        if folder in os.listdir(os.getcwd()):
            if os.path.isdir(folder):
                shutil.rmtree(folder)
                logging.info(f"Deleted {folder}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    if not os.path.exists(os.path.join(CONFIG_FOLDER, ".check_folder")):
    
        File.check_existence(CONFIG_FOLDER, "Programm_info.json", create=True, add_conten={"fixxed_config": False, "unaccessary_folder": False, "excluded": False, "allow_exclusion_request": True}, use_json=True, quite=False)
        programm_info = load_json(os.path.join(CONFIG_FOLDER, "Programm_info.json"))
        
        if not programm_info["fixxed_config"]:
            fix_config()
            programm_info["fixxed_config"] = True
        
        if not programm_info["unaccessary_folder"]:
            delete_unaccessary_folder()
            programm_info["unaccessary_folder"] = True
        
        if not programm_info["excluded"] and programm_info["allow_exclusion_request"]:
            MB_YESNO = 0x04
            MB_ICONQUESTION = 0x30
            
            response = ctypes.windll.user32.MessageBoxW(
                None,
                "Hey!\nWe want to exclude the Current Folder!\nThis will remove the Risk of OnlineFix deletion\nDo you want to continue?\n*Note: This will be removed after uninstalling the app",
                "Powershell Exclusion",
                MB_YESNO | MB_ICONQUESTION
            )

        if response == 6:
            subprocess.run(f'powershell -Command "Start-Process powershell -ArgumentList \\"Add-MpPreference -ExclusionPath \'{os.getcwd()}\'\\" -Verb RunAs"', shell=True, check=True)
            programm_info["excluded"] = True
            programm_info["allow_exclusion_request"] = False
        
        elif response == 7:
            pass
        elif response == 5:
            programm_info["allow_exclusion_request"] = False
        
        save_json(os.path.join(CONFIG_FOLDER, "Programm_info.json"), programm_info)

        if programm_info == {"fixxed_config": True, "unaccessary_folder": True, "excluded": True, "allow_exclusion_request": False} or programm_info == {"fixxed_config": True, "unaccessary_folder": True, "excluded": False, "allow_exclusion_request": False}:
            os.makedirs(os.path.join(CONFIG_FOLDER, ".check_folder"))
    
    
    app = QApplication(sys.argv)
    MainWindow = QMainWindow()
    
    ui = Ui_MainWindow()
    ui.init(MainWindow)
    
    MainWindow.show()
    sys.exit(app.exec_())