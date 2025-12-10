import os, hashlib, json, re, subprocess, psutil, logging, requests
from bs4 import BeautifulSoup
import urllib.parse

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

def get_screenshots(page_content) -> list:
    """
    Extracts up to 2 screenshot URLs by locating the 'SCREENSHOTS' header within .entry-content.
    Scans elements immediately following the header until the next section starts.
    """
    screenshots = []
    try:
        soup = BeautifulSoup(page_content, "html.parser")
        
        # 1. Restrict search to main content area to avoid sidebar/footer noise
        content_area = soup.select_one(".entry-content")
        if not content_area:
            content_area = soup # Fallback
            
        # 2. Find the marker
        target_marker = content_area.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'span', 'strong', 'b', 'p'] 
                                            and 'SCREENSHOTS' in tag.get_text(strip=True).upper())
        
        if target_marker:
            # 3. Scan forward until we hit the next section header or find enough images
            # We iterate through all next elements (tags) in document order
            for tag in target_marker.find_all_next():
                # Stop if we hit a new section header (e.g. "System Requirements")
                if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] and tag != target_marker:
                    # Ignore empty headers or headers nested inside the marker (unlikely)
                    if tag.get_text(strip=True): 
                        break
                
                if tag.name == 'a':
                    href = tag.get('href')
                    if not href: continue
                    
                    processed_href = href

                    # Handle Pinterest
                    if "pinterest.com/pin/create/button/" in href:
                        try:
                            parsed = urllib.parse.urlparse(href)
                            qs = urllib.parse.parse_qs(parsed.query)
                            if 'media' in qs:
                                processed_href = qs['media'][0]
                        except: pass

                    # Relative URLs
                    if processed_href.startswith("/"):
                        processed_href = "https://steamrip.com" + processed_href
                    
                    # Validation
                    if "/wp-content/uploads/" in processed_href:
                        if any(ext in processed_href.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                            if processed_href not in screenshots:
                                screenshots.append(processed_href)
                                if len(screenshots) >= 2:
                                    break
        else:
             logging.warning("Could not find 'SCREENSHOTS' section.")

    except Exception as e:
        logging.error(f"Error extracting screenshots: {e}")
    
    return screenshots


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

def clean_unused_cache_files() -> int:
    """
    Deletes files in CACHE_FOLDER that do not correspond to any game in games.json.
    Returns the number of files deleted.
    """
    count = 0
    try:
        from .utility_vars import CONFIG_FOLDER, CACHE_FOLDER # Ensure imports inside if moved, but they are global in file
        games_data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
        active_hashes = set(games_data.keys())
        
        if not os.path.exists(CACHE_FOLDER):
            return 0

        for filename in os.listdir(CACHE_FOLDER):
            # Skip known non-hash files
            if filename in ["CachedGameList.json"]:
                continue
            
            # Extract potential hash (first 32 chars)
            if len(filename) >= 32:
                file_hash = filename[:32]
                
                # Verify if it looks like an MD5 hash (hexadecimal)
                if re.match(r'^[0-9a-fA-F]{32}', file_hash):
                    if file_hash not in active_hashes:
                        try:
                            os.remove(os.path.join(CACHE_FOLDER, filename))
                            logging.info(f"Cleaned unused cache file: {filename}")
                            count += 1
                        except Exception as e:
                            logging.error(f"Failed to remove {filename}: {e}")
    except Exception as e:
        logging.error(f"Error during cache cleanup: {e}")
        
    return count