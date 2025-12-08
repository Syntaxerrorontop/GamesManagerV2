import logging
import os
import time
import subprocess
import psutil
import threading

from .utility_functions import _get_version_steamrip, save_json, load_json
from .utility_vars import CONFIG_FOLDER

class GameInstance:
    def __init__(self, name, path, args, parrent, libary_instance=None):
        self.game_name = name
        self.executable_path = path
        self.logger = getattr(parrent, 'logger', logging.getLogger('GameInstance'))
        self.libary_instance = libary_instance
        
        if os.path.exists(path):
            self.executable_path = os.path.join(os.getcwd(), path)
        
        self._start_time: float = 0
        self.args = args
        self.parrent = parrent
        self.__process = None
    
    def start(self):
        if self.parrent.is_running:
            return
        self.parrent.is_running = True
        self._start_time = time.time()
        run_data = [self.executable_path] + self.args
        self.__process = subprocess.Popen(run_data, cwd=os.path.dirname(self.executable_path))

    def wait(self):
        if self.__process:
            self.__process.wait()
        played_time = time.time() - self._start_time
        self.update_playtime(played_time)
        self.parrent.is_running = False

    def close(self):
        if not self.__process:
            return
        try:
            parent = psutil.Process(self.__process.pid)
            for child in parent.children(recursive=True):
                child.terminate()
            parent.terminate()
            parent.wait(timeout=5)
            if parent.is_running():
                parent.kill()
        except psutil.NoSuchProcess:
            pass
        self.__process = None
    
    def update_playtime(self, playtime: float):
        config_path = os.path.join(CONFIG_FOLDER, "games.json")
        data = load_json(config_path)
        if self.game_name in data:
            old_playtime = float(data[self.game_name].get("playtime", 0))
            new_playtime = int(old_playtime + playtime)
            data[self.game_name]["playtime"] = new_playtime
            save_json(config_path, data)

class Game:
    def __init__(self, name, version, is_installed, start_path, args, playtime, link, alias ,categories=[], libary_instance=None):
        # Set up basic logger
        self.logger = logging.getLogger('Game')
        self.libary_instance = libary_instance
        
        self.args = args
        self.name = name
        self.version = version
        self.start_path = start_path
        self.playtime = playtime
        self.link = link
        self.alias = alias
        self.has_update = None
        self.is_running = False

        # Create a copy of categories to avoid modifying the persistent config
        self.categories = list(categories) if categories else []
        
        # Clean up existing status tags
        if "Installed" in self.categories:
            self.categories.remove("Installed")
        if "Not Installed" in self.categories:
            self.categories.remove("Not Installed")

        if is_installed:
            self.categories.insert(0, "Installed")
        else:
            self.categories.insert(0, "Not Installed")
        
        if is_installed:
            if isinstance(args, str):
                self.run_instance = GameInstance(name, start_path, args.split(" "), self, libary_instance)
            elif isinstance(args, list):
                self.run_instance = GameInstance(name, start_path, args, self, libary_instance)
        else:
            self.run_instance = None
    
    def start(self):
        self.logger.info(f"🏁 Starting game: {self.name}")
        
        if not self.run_instance:
            self.logger.error(f"🚫 Cannot start {self.name} - no run instance (game not installed?)")
            return
            
        try:
            self.run_instance.start()
            _game_thread = threading.Thread(target=self.run_instance.wait, daemon=True)
            _game_thread.start()
        except Exception as e:
            self.logger.error(f"🚫 Failed to start {self.name}: {e}")

    def stop(self):
        self.logger.info(f"🛑 Stopping game: {self.name}")
        if self.run_instance:
            self.run_instance.close()
    
    def check_for_update(self, scraper):
        if self.has_update is None:
            try:
                remote_version = _get_version_steamrip(self.link, self.libary_instance.my_parrent.scraper)
                self.has_update = remote_version != self.version
            except Exception as e:
                self.logger.error(f"🚫 Error checking updates for {self.name}: {e}")
                self.has_update = False
        return self.has_update
