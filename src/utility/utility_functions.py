import os, hashlib, json, re, subprocess, psutil, logging, requests
from bs4 import BeautifulSoup

from .utility_vars import CACHE_FOLDER

STEAMRIP_VERSION_SELECTOR = "#the-post > div.entry-content.entry.clearfix > div.plus.tie-list-shortcode > ul > li:nth-child(6)"

def hash_url(url: str) -> str:
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def get_hashed_file(hash, extension):
    return f"{hash}{extension}"

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def get_name_from_url(url):
    myurl = url.replace("https://steamrip.com/", "")
    
    def ends_with_pattern(s):
        return bool(re.search(r"-[A-Za-z0-9]{2}/$", s))
    def ends_with_pattern2(s):
        return bool(re.search(r"-[A-Za-z0-9]{3}/$", s))
    if "free-download" in myurl.lower():
        data = myurl.split("free-download")[0]
    elif ends_with_pattern(url):
        data = myurl[:-3]
    
    elif ends_with_pattern2(url):
        data = myurl[:-4]
    
    else:
        data = myurl
    finished = data.replace("-", " ").title()
    return finished

def powershell(cmd, popen=False):
    if popen:
        return subprocess.Popen(["powershell", "-Command", cmd], text=True)
    else:
        return subprocess.run(["powershell", "-Command", cmd], text=True)

def process_running(name: str) -> bool:
    """Check if a process with this name is running"""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and proc.info['name'].lower() == name.lower():
            return True
    return False

def kill_process(name: str):
    """Kill a process by name"""
    logging.debug(f"Killing {name} ...")
    subprocess.run(["taskkill", "/F", "/IM", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def cloud_flare_request(url_r):
    url = "http://127.0.0.1:20080/get_page/"
    headers = {"Content-Type": "application/json"}
    data = {
        "cmd": "request.get",
        "url": url_r,
        "maxTimeout": 60000
    }
    response = requests.post(url, headers = headers, json = data)

    json_response = response.json()
    if json_response.get("status") != "ok":
        logging.error(f"Cloudflare request failed: {json_response}")
        return None
    best_cookies = {c['name']: c['value'] for c in json_response.get('solution').get('cookies') if c['name'] == 'cf_clearance'}
    logging.debug(f"Cloudflare cookies: {best_cookies}")
    return json_response.get('solution').get('response'), best_cookies

def get_png(page_content) -> str:
    soup = BeautifulSoup(page_content, "html.parser")
    soup.find()
    img_tag = soup.select_one("#tie-wrapper > div.container.fullwidth-featured-area-wrapper > div > div > figure > img")
    if img_tag and 'src' in img_tag.attrs:
        img_url = img_tag.attrs['srcset'].split(" ")[0]
    download_url = img_url
    return download_url

def _get_version_steamrip(url, scraper) -> str:
    if not url.startswith("https"):
        return ""
    response = scraper.get_html(url)
    soup = BeautifulSoup(response, 'html.parser')

    element = soup.select_one(selector=STEAMRIP_VERSION_SELECTOR)
    if element:
        try:
            version = element.text.strip().replace("Version: ", "")
            logging.debug(version)
            logging.debug(f"Request Successful: {url} Version: {version}")
            return version
        except Exception as e:
            logging.error(f"Error parsing version from element for {url}: {e}")
            return f"Error: Failed to parse version for {url}. Details: {e}"
    else:
        logging.warning(f"Element with selector '{STEAMRIP_VERSION_SELECTOR}' not found for {url}. Using fallback method...")
        element = soup.select_one(selector=".plus > ul:nth-child(1) > li:nth-child(6)")
        if element:
            try:
                version = element.text.strip().replace("Version: ", "")
                logging.debug(version)
                logging.debug(f"Request Successful: {url} Version: {version}")
                return version
            except Exception as e:
                logging.error(f"Error parsing version from fallback element for {url}: {e}")
                return f"Error: Failed to parse version from fallback for {url}. Details: {e}"
        else:
            logging.error(f"Neither primary nor fallback element found for version for {url}.")
            return f"Error: Version element not found for {url}."
def _game_naming(folder):
        logging.debug(f"Attempting to determine main executable for folder: {folder}")
        exes = []
        full_path_game_execution = None
        
        # First pass: look for a direct match in the root of the game folder
        for name in os.listdir(os.path.join(os.getcwd(), "Games", folder)):
            if name.endswith(".exe"):
                if "unity" not in name.lower(): # Exclude common engine executables if possible
                    full_path_game_execution = os.path.join("Games", folder, name)
                    logging.debug(f"Main executable found in root of {folder}: {full_path_game_execution}")
                    return full_path_game_execution
        
        # Second pass: recursive search within the game folder
        if full_path_game_execution is None:
            logging.debug(f"No direct executable found in {folder} root. Performing recursive search...")
            for path, subdirs, files in os.walk(os.path.join(os.getcwd(), "Games", folder)):
                if full_path_game_execution is not None:
                    break # Stop if already found in a deeper subdir
                for name in files:
                    if name.endswith(".exe"):
                        exes.append(os.path.join(path, name)) # Store full path for later
                        if folder.replace(" ", "").lower() in name.replace(" ", "").lower():
                            full_path_game_execution = os.path.join(path, name)
                            logging.debug(f"Main executable found during recursive search for {folder}: {full_path_game_execution}")
                            break
            
            # Fallback if no specific match, pick the first non-Unity exe
            if full_path_game_execution is None:
                logging.debug(f"No specific executable match for {folder}. Falling back to first non-Unity exe...")
                for file_path in exes:
                    if "unity" not in os.path.basename(file_path).lower():
                        full_path_game_execution = file_path
                        logging.debug(f"Fallback executable selected for {folder}: {full_path_game_execution}")
                        break
        
        if full_path_game_execution is None:
            logging.warning(f"Could not determine main executable for game folder: {folder}. Returning empty string.")
            return "" # Return empty if no executable found at all
            
        if not full_path_game_execution.startswith("Games"):
            full_path_game_execution = full_path_game_execution[len(os.getcwd()) + 1:]
            logging.debug(f"Adjusted executable path to relative: {full_path_game_execution}")
            
        return full_path_game_execution

def format_playtime(seconds):
    if not isinstance(seconds, (int, float)):
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"