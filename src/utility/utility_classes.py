import logging, os, json

from .utility_functions import load_json, save_json

class Payload:
    def __init__(self):
        logging.debug("Payload created")
        self._payload = {}
    
    def add_operation(self, operation):
        logging.debug(f"PAYLOAD: operation added: {operation}")
        self._payload["op"] = operation
    
    def add_id(self, id):
        logging.debug(f"PAYLOAD: id added: {id}")
        self._payload["id"] = id
    
    def add_rand(self, rand):
        logging.debug(f"PAYLOAD: rand added: {rand}")
        self._payload["rand"] = rand
    
    def add_referer(self, referer):
        logging.debug(f"PAYLOAD: referer added: {referer}")
        self._payload["referer"] = referer
    
    def add_method_free(self, method):
        logging.debug(f"PAYLOAD: free_method added: {method}")
        self._payload["method_free"] = method
    
    def add_method_premium(self, method):
        logging.debug(f"PAYLOAD: premium_method added: {method}")
        self._payload["method_premium"] = method
    
    def add_dl(self, dl):
        logging.debug(f"PAYLOAD: dl added: {dl}")
        self._payload["dl"] = dl
    
    def get(self):
        logging.debug(f"Payload generated: {self._payload}")
        return self._payload

class Header:
    def __init__(self):
        self._headers = {}
    
    def add_user_agent(self, user_agent):
        self._headers['user-agent'] = user_agent
    
    def add_authority(self, authority):
        self._headers['authority'] = authority
    
    def add_method(self, method):
        self._headers['method'] = method
    
    def add_path(self, path):
        self._headers["path"] = path
    
    def add_referer(self, referer):
        self._headers['referer'] = referer
    
    def add_hx_request(self, hx_request):
        self._headers['hx_request'] = hx_request
    
    def add_others(self, key, value):
        self._headers[key] = value
    
    def get_headers(self):
        return self._headers

class File:
    @staticmethod
    def check_existence(in_path, file_name, create = True, add_conten = "", use_json = False, quite=False) -> bool:
        if not quite:
            logging.debug(f"Checking {file_name} existence in {in_path}.")

        if not file_name in os.listdir(in_path):
            if not quite:
                logging.debug(f"File not found")
            with open(os.path.join(in_path, file_name), "w") as file:
                file.close()
                if not quite:
                    logging.debug(f"File created: {create} {file_name}")
                
                if add_conten != "":
                    with open(os.path.join(in_path, file_name), "w") as file:
                        if use_json:
                            json.dump(add_conten, file, indent=4)
                        else:
                            file.write(add_conten)
                        file.close()
                    if not quite:
                        logging.debug(f"Added content to {file_name}")
                
                return True
            
            return False
        if not quite:
            logging.debug("File already exists")
        
        return True

class UserConfig:
    def __init__(self, in_path, filename, quite=False):
        
        default_data = {"install_commen_redist": True, "shutil_move_error_replace": True, "search": {"games": True, "movies": False, "series": False}, "start_up_update": True, "speed": 0, "excluded": False, "exclude_message": True}
        
        File.check_existence(in_path, filename, add_conten=default_data, use_json=True, quite=quite)
        
        self._path = os.path.join(in_path, filename)
        self._data = load_json(self._path)
        logging.debug("Verifying Config")
        adding = {}
        for key, item in default_data.items():
            if not key in self._data.keys():
                adding[key] = item
            
            if isinstance(item, dict):
                for sub_key, sub_i in item.items():
                    if not sub_key in self._data[key].keys():
                        adding[key][sub_key] = sub_i
        
        if adding != {}:
            self._data.update(adding)
            
            save_json(os.path.join(in_path, filename), self._data)
        
        self.SHUTIL_MOVE_ERROR_REPLACE = self._data["shutil_move_error_replace"]
        self.INSTALL_COMMENREDIST_STEAMRIP = self._data["install_commen_redist"]
        
        self.SEARCH_GAMES = self._data["search"]
        self.SEARCH_MOVIES = self._data["search"]["movies"]
        self.SEARCH_SERIES = self._data["search"]["series"]
        
        self.UPDATE_ON_STARTUP_ONLY = self._data["start_up_update"]
        
        self.DOWNLOAD_SPEED = self._data["speed"]
        
        self.EXCLUDE_MESSAGE = self._data["exclude_message"]
        self.EXCLUDED = self._data["excluded"]