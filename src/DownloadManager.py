from PyQt5.QtCore import Qt,  QThread, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, 
    QWidget, QProgressBar, QListWidget, QFrame, QMenu, QAction, QMessageBox
)
import os, time, json, requests, logging, string, re, random, ctypes, urllib.parse, threading, subprocess, shutil, glob
# from playwright.sync_api import sync_playwright  # Removed
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from .scraper import UniversalScraper
from .utility.utility_functions import save_json, load_json, hash_url, get_name_from_url, _get_version_steamrip, _game_naming
from .utility.utility_classes import Payload, Header, UserConfig
from .utility.utility_vars import CONFIG_FOLDER, CACHE_FOLDER, APPDATA_CACHE_PATH

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_working_proxy(proxy_file_path):
    """Read proxies from the file, shuffle them, and return the first working one."""
    
    try:
        # Load proxies from file
        with open(proxy_file_path, "r") as file:
            proxies = file.read().splitlines()

        random.shuffle(proxies)  # Shuffle proxies to try them in random order
        
        # Try each proxy until a working one is found
        for proxy in proxies:
            proxy_dict = {"https": proxy}  # Wrap proxy in dictionary
            try:
                # Test the proxy with a simple request
                response = requests.get("http://httpbin.org/ip", proxies=proxy_dict, timeout=10)
                if response.status_code == 200:
                    logging.info(f"Working proxy found: {proxy}")
                    return proxy_dict  # Return the working proxy
            except requests.RequestException as e:
                logging.warning(f"Proxy {proxy} failed, trying next one. Error: {e}")

    except FileNotFoundError:
        logging.error(f"Error: Proxy file '{proxy_file_path}' not found.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in get_working_proxy: {e}", exc_info=True)

    return None  # No working proxy found


class DirectLinkDownloader:
    @staticmethod
    def megadb(url) -> str:
        print("1. Konfiguriere den Schnueffler...")
    
        # Wir müssen Chrome sagen, dass er uns Zugriff auf die Netzwerk-Logs gibt
        options = webdriver.ChromeOptions()
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
        options.add_argument("--start-minimized")
        
        # Damit der Download nicht deinen Ordner vollspammt, setzen wir ihn auf ein Temp-Verzeichnis
        # oder ignorieren ihn. Hier lassen wir ihn kurz anlaufen, da wir eh gleich schließen.
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.minimize_window()
        try:
            # --- PHASE 1: Navigation ---
            driver.get(url)
            print("2. Seite geladen.")

            # Klick auf ersten "Free Download" (falls vorhanden)
            try:
                start_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='Free Download'] | //button[contains(text(), 'Free Download')]"))
                )
                start_btn.click()
            except:
                pass 

            # --- PHASE 2: Captcha & Wartezeit ---
            print("3. Löse Captcha automatisch...")
            try:
                WebDriverWait(driver, 5).until(
                    EC.frame_to_be_available_and_switch_to_it((By.XPATH, "//iframe[starts-with(@name, 'a-') and starts-with(@src, 'https://www.google.com/recaptcha')]"))
                )
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))).click()
                driver.switch_to.default_content()
            except:
                print("   -> (Manuelles Eingreifen beim Captcha evtl. nötig)")
                driver.switch_to.default_content()

            print("4. Warte auf den Countdown (Geduld)...")
            # Warten bis der finale Button klickbar ist
            final_btn = WebDriverWait(driver, 60).until(
                EC.element_to_be_clickable((By.ID, "downloadbtn"))
            )
            
            # --- PHASE 3: Der Zugriff ---
            print("5. Klicke Button und hoere Netzwerk ab...")
            
            # Zeitstempel merken, damit wir nur NEUE Requests anschauen
            driver.get_log("performance") # Löscht den alten Log-Puffer
            
            # Klick!
            driver.execute_script("arguments[0].click();", final_btn)
            
            # Jetzt scannen wir 10 Sekunden lang hektisch die Logs nach dem Download-Link
            found_url = None
            end_time = time.time() + 15
            
            while time.time() < end_time:
                logs = driver.get_log("performance")
                
                for entry in logs:
                    message = json.loads(entry["message"])["message"]
                    
                    # Wir suchen nach "Network.requestWillBeSent" Ereignissen
                    if message["method"] == "Network.requestWillBeSent":
                        request_url = message["params"]["request"]["url"]
                        
                        # --- DER FILTER ---
                        # Ein echter Download-Link bei MegaDB hat oft "/files/" oder "/d/" 
                        # oder endet auf typische Dateiendungen.
                        # Wir ignorieren .js, .css, .png, etc.
                        
                        if any(x in request_url for x in [".rar"]):
                            found_url = request_url
                            break
                        
                        # Manchmal sieht der Link auch so aus: https://s18.megadb.net/d/TOKEN/filename
                        if "/d/" in request_url and "megadb.net" in request_url:
                            found_url = request_url
                            break
                
                if found_url:
                    break
                time.sleep(0.5)

            if found_url:
                print("\n" + "="*60)
                print(f"TREFFER, MEISTER! Hier ist der Link:")
                print(f"{found_url}")
                print("="*60 + "\n")
                return found_url
            else:
                print("Kein eindeutiger File-Link im Netzwerkverkehr gefunden.")
                return None

        except Exception as e:
            print(f"Fehler: {e}")
        finally:
            print("Browser wird geschlossen.")
            driver.quit()
    
    @staticmethod
    def filecrypt(url) -> str:
        logging.debug(url)
        return -1
    
    @staticmethod
    def buzzheavier(url) -> str:
        """
        Lädt eine Datei von Buzzheavier herunter, basierend auf dem Link.
        Nutzt den HX-Request Trick, um den direkten Link zu erhalten.
        """
        print(f"Starte Buzzheavier-Vorgang fuer: {url}")
        
        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": url
        }

        try:
            # 1. Hauptseite abrufen (um Session/Cookies zu setzen)
            r_main = session.get(url, headers=headers)
            r_main.raise_for_status()
            
            # Versuche Dateinamen zu finden (im Titel oder h1)
            soup = BeautifulSoup(r_main.text, 'html.parser')
            filename = "downloaded_file.rar" # Fallback
            
            # Buzzheavier zeigt den Namen oft in einem text-2xl span oder title
            title_tag = soup.find("title")
            if title_tag:
                filename = title_tag.text.replace(" - Buzzheavier", "").strip()
            
            print(f"Gefundener Dateiname: {filename}")

            # 2. Download-Trigger senden
            # Buzzheavier nutzt htmx. Ein POST oder GET an /download mit HX-Request header liefert den Redirect.
            download_endpoint = url.rstrip('/') + "/download"
            headers["HX-Request"] = "true"
            
            r_trigger = session.get(download_endpoint, headers=headers, allow_redirects=False)
            
            # Der echte Link steht oft im 'hx-redirect' Header oder 'Location'
            direct_link = r_trigger.headers.get("hx-redirect") or r_trigger.headers.get("Location")
            return {"url": direct_link, "payload": {}, "headers": {}, "method": "get", "session": session}

        except Exception as e:
            logging.error(f"Downloader:buzzheavier Error: {e}")
            return -1
    
    @staticmethod
    def ficher(url) -> str:
        session = requests.Session()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Referer': url
        }

        print(f"1. Analysiere Seite: {url}")
        try:
            # 1. Seite abrufen
            response = session.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 2. Wir suchen exakt das Formular "f1", das im HTML zu sehen war
            form = soup.find("form", id="f1")
            if not form:
                return "Fehler: Formular 'f1' nicht gefunden. Layout geaendert?"

            # 3. Den versteckten Token "adz" suchen
            adz_input = form.find("input", {"name": "adz"})
            if not adz_input:
                return "Fehler: Token 'adz' nicht gefunden."
            
            adz_value = adz_input['value']
            print(f"   -> Token gefunden: {adz_value}")

            # 4. Die Action-URL aus dem Formular holen (wohin die Daten gesendet werden)
            post_url = form.get("action")
            if not post_url:
                post_url = url # Fallback auf die gleiche URL

            # 5. Wartezeit (Im HTML stand "var ct = 60;")
            print("2. Wartezeit laeuft (62 Sekunden Sicherheitsabstand)...")
            time.sleep(62)

            # 6. Payload bauen (nur das adz Feld ist im Formular wichtig)
            payload = {
                "adz": adz_value
            }

            print("3. Sende Download-Anfrage...")
            final_response = session.post(post_url, data=payload, headers=headers)
            
            # 7. Den finalen Link aus der Antwort extrahieren
            final_soup = BeautifulSoup(final_response.text, 'html.parser')
            
            # Auf der nächsten Seite ist der Link oft ein Button "Click here to download"
            # Wir suchen nach dem typischen Button-Style
            direct_link_btn = final_soup.find("a", class_="ok btn-general btn-orange")
            
            if direct_link_btn:
                return {"url": direct_link_btn['href'], "payload": {}, "headers": {}, "method": "get"} 
            else:
                with open("debug_step2.html", "w", encoding="utf-8") as f:
                    f.write(final_response.text)
                    
                return -1#"ehler: Finaler Link nicht gefunden (siehe debug_step2.html)."

        except Exception as e:
            return f"Kritischer Fehler: {e}"

    @staticmethod
    def datanode(url) -> str:
        try:
            ids = str(url).split("/")
            for index, id in enumerate(ids):
                if id == "datanodes.to":
                    _id = ids[index+1]
                    break
            
            headers = Header()
            headers.add_authority("datanodes.to")
            headers.add_method("POST")
            headers.add_hx_request("False")
            headers.add_path("/download")
            headers.add_referer("https://datanodes.to/download")
            headers.add_others("cookie", "lang=german; file_name=God-O-War-Ragnarok-SteamRIP.com.rar; file_code=guziknumxest; affiliate=dOtuOv3qRKAJ2fSUcUnMpzIdz6ueYkMmoXNiCfaBgZWSeYRZgi3SARRHh2jIQ8coMyT8QyluHsyloNJvM84bZAwuxsPtWbSQvkEtNJ2Q4PjOfEWpHkrD5ligTtBuVmWGIfRg; cf_clearance=ImOIuyght4VddGN1jz0xhgwguDk.8on7NtNs1WRyWOc-1737588193-1.2.1.1-Vxe_QzcgRNO3EvCAXYXDqtXZGPcLrWiPDHq5B86FMAX0bZrYs.nhOVNsNXdjHcL3n_Ce47.gWtmTAO8iYg94fuR5k.dO8KWKNtYAN3om7cgQncdgCI3qoap6EBJgRJU1HKT9AWB8yUg6vPGGB3GFGzpv98IEWIQbMF9UYU.4ndMBarRfZkr7vfl816ic4A16.d.1fe_.92OALnmsUZlFv4ut0MLcffjfq9mcDD60_2aGwD_1zOYg0sa4qZizjgZwK11vS7FJm4ro3t4VFy7AxB70XqYkt3sn800PiOKw9U0")
            headers.add_user_agent("Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Mobile Safari/537.36")
            
            payload = Payload()
            payload.add_dl("1")
            payload.add_id(_id)
            payload.add_method_free("Kostenloser Download >>")
            payload.add_method_premium("")
            payload.add_operation("download2")
            payload.add_referer("https://datanodes.to/download")
            payload.add_rand("")
            
            logging.info(f"Getting Direct download link with request: https://datanodes.to/download | Payload: {payload.get()} | Headers: {headers.get_headers()}")
            
            response = requests.post("https://datanodes.to/download", data=payload.get(), headers=headers.get_headers())
            
            url = urllib.parse.unquote(str(response.json()['url']))
            
            logging.info(f"Found Direct Download Link: {url}")
            
            return {"url": url, "payload": {}, "headers": {}, "method": "get"}
        except Exception as e:
            logging.error(f"Downloader:datanode Error: {e}")
            return -1
    
    @staticmethod
    def gofile(url) -> str:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
        from webdriver_manager.chrome import ChromeDriverManager
        logging.info("Downloader:gofile Generating download link using Selenium (Network Intercept) this may take up to 2 Minutes")
    
        # URL ID extrahieren (wird für den API-Filter benötigt)
        # z.B. https://gofile.io/d/AbCdE -> AbCdE
        _id = url.split("/")[-1]

        # Setup Chrome Options
        chrome_options = Options()
        chrome_options.add_argument("--headless") 
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        # WICHTIG: Performance Logging aktivieren, um Netzwerkverkehr zu sehen
        chrome_options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        logging.info("Downloader:gofile Launching Selenium Instance (Chromium)")
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        link = ""
        accounttoken = ""
        
        try:
            logging.info(f"Downloader:gofile Visiting {url} for Direct Download Link extraction")
            driver.get(url)

            logging.info("Downloader:gofile Waiting until successful link and cookie extraction.")
            
            start_time = time.time()
            timeout = 120  # 2 Minuten Timeout

            while not link or not accounttoken:
                # Timeout Check
                if time.time() - start_time > timeout:
                    logging.error("Downloader:gofile Timeout reached")
                    break

                # 1. Cookie Extraction
                if not accounttoken:
                    cookies = driver.get_cookies()
                    for cookie in cookies:
                        if cookie["name"] == "accountToken":
                            accounttoken = cookie["value"]
                            logging.info(f"Downloader:gofile Successful found Cookie: {accounttoken}")
                
                # 2. Link Extraction (via Netzwerk-Logs / API Interception)
                if not link:
                    try:
                        # Wir holen uns die Performance Logs (Netzwerkverkehr)
                        logs = driver.get_log("performance")
                        
                        for entry in logs:
                            message = json.loads(entry["message"])["message"]
                            
                            # Wir suchen nach "Network.responseReceived"
                            if message["method"] == "Network.responseReceived":
                                response_url = message["params"]["response"]["url"]
                                
                                # Prüfen, ob die URL die GoFile API für unsere Datei-ID ist
                                # Ähnlich wie: if response.url.startswith(f"https://api.gofile.io/contents/{_id}?")
                                if f"api.gofile.io/contents/{_id}" in response_url:
                                    request_id = message["params"]["requestId"]
                                    
                                    try:
                                        # Den Body der Antwort via CDP (Chrome DevTools) abrufen
                                        response_body = driver.execute_cdp_cmd(
                                            "Network.getResponseBody", 
                                            {"requestId": request_id}
                                        )
                                        
                                        body_json = json.loads(response_body['body'])
                                        
                                        # JSON parsen wie im originalen Playwright Script
                                        if "data" in body_json and "children" in body_json["data"]:
                                            file_id = list(body_json["data"]['children'].keys())[0]
                                            found_link = body_json["data"]['children'][file_id]["link"]
                                            
                                            if found_link:
                                                link = found_link
                                                logging.info(f"Downloader:gofile Successful found link via API: {link}")
                                                break # Schleife abbrechen, wir haben den Link
                                                
                                    except Exception as inner_e:
                                        # Manchmal ist der Body nicht mehr verfügbar oder leer
                                        pass
                    except Exception as e:
                        logging.debug(f"Error parsing logs: {e}")

                time.sleep(1) # Kurze Pause

            if link and accounttoken:
                return {
                    "url": link, 
                    "payload": {}, 
                    "headers": {"Cookie": f"accountToken={accounttoken}"}, 
                    "method": "get"
                }
            else:
                logging.error("Downloader:gofile Failed to extract Link or Token")
                return None

        except Exception as e:
            logging.error(f"Downloader:gofile Critical Error: {e}")
            return None
            
        finally:
            logging.info("Downloader:gofile Closing Selenium Driver")
            driver.quit()

class Downloader:
    @staticmethod
    def steamrip(url, data, scraper):
        try:
            page_content = scraper.get_html(url)
            
            logging.info("Downloader:steamrip Extracting downloadable links")
            
            found_links = {}
            
            for key, data_ in data["provider"].items():

                regex_finder = re.findall(data_["pattern"], page_content)
                
                if regex_finder and len(regex_finder) == 1:
                    found_links[key] = data_["formaturl"].format(detected_link = regex_finder[0])
                else:
                    found_links[key] = None
            
            logging.info(f"Downloader:steamrip Detected download links: {found_links}")
            
            logging.info(f"Downloader:steamrip Generating Filename")
            try:
                name = url[:-1].split("/")[-1].split("free-download")[0][:-1].replace("-", "_")
            except:
                logging.warning("Downloader:steamrip Error while generating name continuing with random name")
                name = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            
            return found_links, name
                
        except Exception as e:
            logging.error(f"Downloader:steamrip Error fetching the URL: {e}")
            return {}, "Unknown"

downloader_data = {
        "provider": {
            "gofile": {
                "pattern": r"gofile\.io/d/([a-zA-Z0-9]+)",
                "formaturl": "https://gofile.io/d/{detected_link}",
                "priority": 1,
                "downloader": DirectLinkDownloader.gofile,
                "enabled": True
            },
            "filecrypt": {
                "pattern": r'<a\s+href="\/\/(?:\w+\.)?filecrypt\.\w+\/Container\/([A-Za-z0-9]+)"',
                "formaturl": "https://www.filecrypt.cc/Container/{detected_link}",
                "priority": 2,
                "downloader": DirectLinkDownloader.filecrypt,
                "enabled": False
            },
            "buzzheavier": {
                "pattern": r'<a\s+href="\/\/buzzheavier\.com\/([^\"]+)"',
                "formaturl": "https://buzzheavier.com/{detected_link}",
                "priority": 3,
                "downloader": DirectLinkDownloader.buzzheavier,
                "enabled": True
            },
            "fichier": { #TODO: PATCH BUG -> DOES NOT WORK ENABLE TRY -> Miside
                "pattern": r'1fichier\.com/\?([^\"]+)',
                "formaturl": "https://1fichier.com/?{detected_link}",
                "priority": 5,
                "downloader": DirectLinkDownloader.ficher,
                "enabled": True
            },
            "datanode": {
                "pattern": r'<a\s+href="\/\/datanodes\.to\/([^\"]+)"',
                "formaturl": "https://datanodes.to/{detected_link}",
                "priority": 4,
                "downloader": DirectLinkDownloader.datanode,
                "enabled": True
            },
            "megadb": {
                "pattern": r'<a\s+href="\/\/megadb\.net\/([^\"]+)"',
                "formaturl": "https://megadb.net/{detected_link}",
                "priority": 6,
                "downloader": DirectLinkDownloader.megadb,
                "enabled": True
            },
        },
        "method": Downloader.steamrip,
        "compression": "rar",
    }

def _get_best_downloader(urls: dict, ignore:str = ""):
    __best_downloader, __best_downloader_key = None, None
    
    for key, download_link in urls.items():
        
        if key==ignore:
            continue
        
        if not downloader_data["provider"][key]["enabled"]:
            logging.warning(f"Downloader:main Provider: {key} is currently disabled")
            continue
        
        if download_link != None:
            if __best_downloader == None:
                
                __best_downloader = downloader_data["provider"][key]
                __best_downloader_key = key
                
                continue
            
            if downloader_data["provider"][key]["priority"] < __best_downloader["priority"]:
                __best_downloader = downloader_data["provider"][key]
                __best_downloader_key = key
    
    return __best_downloader, __best_downloader_key

class DownloadThread(QThread):
    progress = pyqtSignal(int)
    state = pyqtSignal(str)
    download_speed = pyqtSignal(str)
    estimated_time = pyqtSignal(str)
    started = pyqtSignal()
    finished = pyqtSignal()
    
    def __init__(self, parent):
        super().__init__()
        self.url: str = None
        self.my_parrent = parent
        self.is_installing = False
        self.running = False
        self.current_hash = None
        self.downloaded_bytes = 0
        self._resume_pos = 0
        self.max_speed = 0
        self._is_paused = False
        self._is_stopped = False
        self.total_size = 0
        self.pause_create = False
        self.num_parts = 0
        self.current_proxy = {}
        self.parts = {}
        self.total_downloaded = 0
        self.last_report_time = time.time()
        self.last_report_bytes = 0
        self.mega_db_worker_number = 12
        self.default_worker = 2
        self.success = False

    def cleanParams(self):
        self.url = None
        self.is_installing = False
        self.running = False
        self.current_hash = None
        self.downloaded_bytes = 0
        self._resume_pos = 0
        self._is_paused = False
        self._is_stopped = False
        self.total_size = 0
        self.current_proxy = {}
        self.parts = {}
        self.total_downloaded = 0
        self.last_report_time = time.time()
        self.last_report_bytes = 0
        self.mega_db_worker_number = 12
        self.success = False
        
    def set_params(self, url):
        self.url = url
        self.current_hash = hash_url(url)
        self.downloaded_bytes = 0
        self.success = False

    def run(self):
        self.state.emit("Checking version...")
        try:
            latest_version = _get_version_steamrip(self.url, self.my_parrent.scraper)
            
            # Access current_download safely
            if hasattr(self.my_parrent, 'download_manager'):
                manager = self.my_parrent.download_manager
                current_item = manager.current_download
                
                if current_item:
                    old_version = current_item.get("version", "Pending")
                    if old_version != latest_version and old_version != "Pending":
                        self.state.emit("Version mismatch. Cleaning cache...")
                        hash_val = hash_url(self.url)
                        rar_path = os.path.join(os.getcwd(), "DownloadCache", f"{hash_val}.rar")
                        if os.path.exists(rar_path):
                            try:
                                os.remove(rar_path)
                            except Exception as e:
                                logging.error(f"Failed to remove old rar: {e}")
                    
                    current_item["version"] = latest_version
                    manager._save_queue()
        except Exception as e:
            logging.error(f"Error checking version in thread: {e}")

        url_backup=self.url
        if not os.path.exists(os.path.join(os.getcwd(), "DownloadCache")):
            os.mkdir(os.path.join(os.getcwd(), "DownloadCache"))
        
        error = {
            -1: "1Ficher on cooldown"
        }
        if not self.url:
            logging.error("Error: No URL set!")
            self.state.emit("Error: No URL set!")
            return

        self.started.emit()
        self.state.emit(f"Preparing download...")
        self.running = True
        
        skip = False # Initialize skip flag

        __links, name = Downloader.steamrip(self.url, downloader_data, self.my_parrent.scraper)
        self.state.emit(f"Finding Best link...")
        __best_downloader, __best_downloader_key = _get_best_downloader(__links)
        
        if __best_downloader is None:
            logging.error("Download failed: Could not find a downloader.")
            return
        
        logging.info(f"Downloader: Best downloader: {__best_downloader_key}")
    
        __downloader_function = __best_downloader["downloader"]
        
        __download_request = __downloader_function(__links[__best_downloader_key])
        if isinstance(__download_request, int):
            logging.error(error[__download_request])
            logging.info("We are getting the next best Downlaoder")
            
            __best_downloader, __best_downloader_key = _get_best_downloader(__links, ignore=__best_downloader_key)
            if __best_downloader is None:
                logging.error("Download failed: Could not find a better Downloader...")
                return
            
            logging.info(f"Downloader: Best downloader: {__best_downloader_key}")
    
            __downloader_function = __best_downloader["downloader"]
            
            __download_request = __downloader_function(__links[__best_downloader_key])
        
        logging.info(f"Downloader: Starting the download with: {__download_request}")
        self.state.emit(f"Downloading...")

        if __best_downloader_key== "ficher":
            logging.debug("Ficher detected setting default worker to 1")
            self.default_worker = 1
            self.num_parts = 1
        
        elif __best_downloader_key == "gofile":
            logging.debug("Gofile detected setting default worker to 2")
            self.default_worker = 2
            self.num_parts = 2
        
        elif __best_downloader_key == "datanode":
            pass
        
        elif __best_downloader_key == "filecrypt":
            pass
        
        elif __best_downloader_key == "buzzheavier":
            logging.debug("Buzzheavier detected setting default worker to 2")
            self.default_worker = 5
            self.num_parts = 5
        
        if __best_downloader_key == "megadb":
                if isinstance(__download_request, int):
                    logging.error(f"Downloader:megadb Failed with code: {__download_request}")
                    self.state.emit("Download failed.")
                    return

                self.num_parts = self.mega_db_worker_number
                __download_url_megadb = __download_request["url"]

                response = requests.head(__download_url_megadb)
                file_size = int(response.headers.get('Content-Length', 0))
                self.total_size = file_size
                skip = False
                if os.path.exists(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")):
                    existing_size = os.path.getsize(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar"))
                    if existing_size == file_size:
                        logging.info("File already downloaded, skipping download.")
                        self.state.emit(f"File already downloaded, skipping download.")
                        skip = True
                
                part_size = file_size // self.mega_db_worker_number
                ranges = [(i * part_size, (i + 1) * part_size - 1) for i in range(self.mega_db_worker_number)]
                ranges[-1] = (ranges[-1][0], file_size - 1)

                if not skip:
                    try:
                        with ThreadPoolExecutor(max_workers=self.mega_db_worker_number) as executor:
                            futures = []
                            proxy = None
                            for i, (start, end) in enumerate(ranges):
                                
                                futures.append(executor.submit(self.download_part, i, start, end, file_size, __download_url_megadb))
                                time.sleep(2)
                                
                                while self.pause_create:
                                    QThread.msleep(100)

                            for future in futures:
                                try:
                                    future.result()
                                except Exception as e:
                                    logging.error(f"MegaDB download part failed: {e}")
                                    self.state.emit("Download failed.")
                                    return 
                    except Exception as e:
                        logging.error(f"MegaDB ThreadPool error: {e}")
                        self.state.emit("Download failed.")
                        return

                    if not self._is_stopped:
                        self.combine_parts()
        
        else:
            url = __download_request["url"]
            headers = __download_request["headers"]
            payload = __download_request["payload"]
            
            session = __download_request.get("session", None)
            
            if session==None:
                response = requests.get(url, headers=headers, data=payload, stream=True)
            else:
                response = session.get(url, headers=headers, data=payload, stream=True)
            file_size = int(response.headers.get('Content-Length', 0))
            response.close()
            self.total_size = file_size
            skip = False
            
            if os.path.exists(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")):
                    existing_size = os.path.getsize(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar"))
                    if existing_size == file_size:
                        logging.info("File already downloaded, skipping download.")
                        self.state.emit(f"File already downloaded, skipping download.")
                        skip = True
                
            if self.default_worker > 0:
                part_size = file_size // self.default_worker
                ranges = [(i * part_size, (i + 1) * part_size - 1) for i in range(self.default_worker)]
                ranges[-1] = (ranges[-1][0], file_size - 1)

                if not skip:
                    try:
                        with ThreadPoolExecutor(max_workers=self.default_worker) as executor:
                            futures = []
                            for i, (start, end) in enumerate(ranges):
                                time.sleep(0.5)
                                futures.append(executor.submit(self.download_part, i, start, end, file_size, url, headers, payload, self.default_worker, session=session))

                            for future in futures:
                                try:
                                    future.result()
                                except Exception as e:
                                    logging.error(f"Download part failed: {e}")
                                    self.state.emit("Download failed.")
                                    return
                    except Exception as e:
                         logging.error(f"ThreadPool error: {e}")
                         self.state.emit("Download failed.")
                         return

                    if not self._is_stopped:
                        self.combine_parts()
        
        if self._is_stopped:
            self.state.emit("Stopped.")
            return
            
        self.state.emit(f"Unpacking...")
        rar_path = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")
        
        folder_path = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}")
        
        if os.path.exists(folder_path):
            shutil.rmtree(folder_path)
        
        os.mkdir(folder_path)
        self.progress.emit(0)
        process = subprocess.Popen([os.path.join(APPDATA_CACHE_PATH, "Tools", "UnRAR.exe"), "x", "-y",rar_path, folder_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        start_time = time.time()
        
        try:
            while process.poll() is None:
                for line in process.stdout:
                    logging.debug(line.strip())
                    match = re.search(r'(\d+)%', line)
                    if match:
                        percent = int(match.group(1))
                        self.progress.emit(percent)
                        
                        if percent > 0:
                            elapsed_time = time.time() - start_time
                            estimated_total_time = elapsed_time / (percent / 100)
                            remaining_time = estimated_total_time - elapsed_time
                            
                            hours, rem = divmod(remaining_time, 3600)
                            minutes, seconds = divmod(rem, 60)
                            formatted_time = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
                            self.estimated_time.emit(formatted_time)

        except AttributeError:
            self.progress.emit(100)
        
        process.wait()
        logging.debug(f"Unpacking finished with code: {process.returncode}")

        if process.returncode != 0:
            if skip:
                self.state.emit("Cache corrupt. Retrying...")
                logging.warning("Unpacking failed on cached file. Deleting and retrying.")
                try:
                    os.remove(rar_path)
                except OSError:
                    pass
                self.run()
                return
            else:
                self.state.emit("Unpacking failed.")
                logging.error("Unpacking failed.")
                return

        rename_path = None
        for file in os.listdir(folder_path):
            if file == "_CommonRedist":
                continue
            if os.path.isdir(os.path.join(folder_path, file)):
                rename_path = os.path.join(folder_path, file)
        
        if not rename_path:
            self.state.emit("Error: Game folder not found.")
            logging.error("Unpacking successful but no game folder found.")
            return

        if os.path.exists(os.path.join(os.getcwd(), "Games", self.current_hash)):
            shutil.rmtree(os.path.join(os.getcwd(), "Games", self.current_hash))
        
        time.sleep(1)

        try:
            os.rename(rename_path, os.path.join(folder_path, self.current_hash))
            shutil.move(os.path.join(folder_path, self.current_hash), os.path.join(os.getcwd(), "Games"))
        except Exception as e:
             self.state.emit(f"Error moving files: {e}")
             logging.error(f"Error moving files: {e}")
             return
        
        exe_path = _game_naming(self.current_hash)
        logging.debug(exe_path)
        if not self.current_hash in exe_path:
            new_path = ""
            splitted = exe_path.split("\\")
            repalce_this = splitted[1]
            for part in splitted:
                if part == repalce_this:
                    part == self.current_hash
                
                new_path+=part
                if not part.endswith(".exe"):
                    new_path+="\\"
        data = load_json(os.path.join(CONFIG_FOLDER, "games.json"))
        if not self.current_hash in data.keys():
            data[self.current_hash] = {"args": [], "exe": exe_path, "name": self.current_hash, "alias": get_name_from_url(url_backup), "link": url_backup, "version": _get_version_steamrip(url_backup, self.my_parrent.scraper), "categorys": [], "playtime": 0}
        else:
            data[self.current_hash]["exe"] = exe_path
            data[self.current_hash]["version"] = _get_version_steamrip(url_backup, self.my_parrent.scraper)

        save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
        
        try:
            shutil.rmtree(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}"))
            os.remove(rar_path)
        except Exception as e:
            logging.warning(f"Cleanup failed: {e}")

        self.state.emit(f"Finished")
        self.success = True
        self.finished.emit()
    
    def download_file(self, url, headers, payload, total_size):
        filename = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")

        downloaded_size = 0
        if os.path.exists(filename):
            downloaded_size = os.path.getsize(filename)
            self.total_downloaded += downloaded_size

        if downloaded_size > 0:
            headers['Range'] = f"bytes={downloaded_size}-{total_size - 1}"

        response = requests.get(url, headers=headers, data=payload, stream=True)

        if response.status_code not in (200, 206):
            logging.error(f"Failed to request content. Status code: {response.status_code}")
            self.state.emit("Download failed~")
            return

        max_bytes_per_sec = int(self.max_speed) * 1024 if int(self.max_speed) > 0 else None
        chunk_size = 1024
        start_time = time.time()
        bytes_this_second = 0

        with open(filename, 'ab') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if self._is_stopped:
                    logging.error("Download stopped unexpectedly.")
                    self.state.emit("Download stopped~")
                    break
                if self._is_paused:
                    QThread.msleep(100)
                    continue
                if not chunk:
                    continue

                f.write(chunk)
                downloaded_size += len(chunk)
                bytes_this_second += len(chunk)

                self.total_downloaded += len(chunk)
                if downloaded_size!=0:
                    progress_percentage = (downloaded_size / total_size) * 100
                    self.progress.emit(int(progress_percentage))
                self.calculate_speed()

                if max_bytes_per_sec:
                    elapsed = time.time() - start_time
                    if elapsed < 1.0 and bytes_this_second >= max_bytes_per_sec:
                        time.sleep(1.0 - elapsed)
                        start_time = time.time()
                        bytes_this_second = 0
                    elif elapsed >= 1.0:
                        start_time = time.time()
                        bytes_this_second = 0

        if downloaded_size >= total_size:
            logging.info("Download completed successfully.")
            self.state.emit("Download completed~")

    def download_part(self, part_num, start, end, total_size, url, headers=None, payload=None, max_worker = 0, proxy=None, session=None):
        filename = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}_part_{part_num}")

        if max_worker!=0:
            self.mega_db_worker_number = max_worker
        
        if os.path.exists(filename):
            existing_size = os.path.getsize(filename)
            if existing_size >= (end - start + 1):
                logging.info(f"Part {part_num} already downloaded, skipping.")
                self.pause_create = False
                self.total_downloaded += existing_size
                try:
                    progress_percentage = (self.total_downloaded / total_size) * 100
                except ZeroDivisionError:
                    progress_percentage = 0
                self.progress.emit(int(progress_percentage))
                self.parts[part_num] = filename
                return
            start = existing_size + start
            self.total_downloaded += existing_size # Add resumed bytes to total
            try:
                progress_percentage = (self.total_downloaded / total_size) * 100
            except ZeroDivisionError:
                progress_percentage = 0
            self.progress.emit(int(progress_percentage))
            logging.info(f"Resuming part {part_num} from byte {start}.")
        if headers == None:
            headers = {'Range': f"bytes={start}-{end}"}
        else:
            headers['Range'] = f"bytes={start}-{end}"
        
        if session==None:
            response = requests.get(url, headers=headers, data=payload, stream=True, proxies=self.current_proxy)
        else:
            response = session.get(url, headers=headers, data=payload, stream=True, proxies=self.current_proxy)

        if response.status_code!=206 and response.status_code!=503:
            logging.error(f"Failed to request partial content for part {part_num}. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return
        
        if response.status_code == 503:
            logging.error(f"503 Service Unavailable for part {part_num}. Trying again with a new proxy.")
            logging.info(f"Trying again with a new proxy. {response.text}")
            self.pause_create = True
            return
        
        self.pause_create = False

        max_bytes_per_sec = int(self.max_speed) * 1024 / self.mega_db_worker_number if int(self.max_speed) > 0 else None
        chunk_size = 1024
        start_time = time.time()
        bytes_this_second = 0

        try:
            with open(filename, 'ab') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if self._is_stopped:
                        break
                    while self._is_paused:
                        QThread.msleep(100)
                    if not chunk:
                        continue
                    max_bytes_per_sec = int(self.max_speed) * 1024 / self.mega_db_worker_number if int(self.max_speed) > 0 else None
                    f.write(chunk)
                    self.total_downloaded += len(chunk)
                    try:
                        progress_percentage = (self.total_downloaded / total_size) * 100
                    except ZeroDivisionError:
                        progress_percentage = 0
                    self.progress.emit(int(progress_percentage))
                    self.calculate_speed()

                    if max_bytes_per_sec:
                        bytes_this_second += len(chunk)
                        elapsed = time.time() - start_time
                        if elapsed < 1.0 and bytes_this_second >= max_bytes_per_sec:
                            time.sleep(1.0 - elapsed)
                            start_time = time.time()
                            bytes_this_second = 0
                        elif elapsed >= 1.0:
                            start_time = time.time()
                            bytes_this_second = 0
            
            self.parts[part_num] = filename

        except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError, ConnectionResetError) as e:
            logging.error(f"Network error in part {part_num}: {e}")
            # Optionally: Mark this part as failed or implement retry logic here.
            # For now, we stop to avoid crashing the main application.
            # self.success = False # This is handled in the main thread logic
            return
        except Exception as e:
            logging.error(f"Unexpected error in part {part_num}: {e}", exc_info=True)
            return

    def combine_parts(self):
        if len(self.parts) < self.num_parts:
            self.state.emit("Error: Download failed. Not all parts were downloaded.")
            return
        
        self.state.emit("Merging parts...")
        output_file_path = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")
        
        merged_size = 0
        chunk_size = 1024 * 1024 * 5 # 5MB Chunk

        with open(output_file_path, 'wb') as output_file:
            for i in range(self.num_parts):
                if i not in self.parts:
                    self.state.emit(f"Error: Missing part {i}. Cannot combine files.")
                    return
                with open(self.parts[i], 'rb') as part_file:
                    while True:
                        chunk = part_file.read(chunk_size)
                        if not chunk:
                            break
                        output_file.write(chunk)
                        merged_size += len(chunk)
                        if self.total_size > 0:
                            progress_percentage = (merged_size / self.total_size) * 100
                            self.progress.emit(int(progress_percentage))

        for part_path in self.parts.values():
            try:
                os.remove(part_path)
            except Exception as e:
                logging.error(f"Failed to delete part {part_path}: {e}", exc_info=True)


    def calculate_speed(self):
        current_time = time.time()
        time_diff = current_time - self.last_report_time

        if time_diff >= 1:
            speed = (self.total_downloaded - self.last_report_bytes) / time_diff
            if not hasattr(self, "speed_history"):
                self.speed_history = []

            self.speed_history.append(speed)
            if len(self.speed_history) > 10:
                self.speed_history.pop(0)

            avg_speed = sum(self.speed_history) / len(self.speed_history)

            if avg_speed >= 1024**3:
                readable_speed = f"{avg_speed / (1024**3):.2f} GB/s"
            elif avg_speed >= 1024**2:
                readable_speed = f"{avg_speed / (1024**2):.2f} MB/s"
            elif avg_speed >= 1024:
                readable_speed = f"{avg_speed / 1024:.2f} KB/s"
            else:
                readable_speed = f"{avg_speed:.2f} B/s"
            self.download_speed.emit(readable_speed)

            if avg_speed > 0:
                remaining_bytes = self.total_size - self.total_downloaded
                remaining_seconds = int(remaining_bytes / avg_speed)

                hours, rem = divmod(remaining_seconds, 3600)
                minutes, seconds = divmod(rem, 60)
                formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                formatted_time = "Calculating..."

            self.estimated_time.emit(formatted_time)

            self.last_report_time = current_time
            self.last_report_bytes = self.total_downloaded

    def pause(self):
        self._is_paused = True

    def resume(self):
        self._is_paused = False

    def stop(self):
        self._is_stopped = True

class DownloadManager(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.my_parent = parent
        self.cookies = {}
        self.is_downloading = False
        self.download_queue = []
        self.current_download = None
        self.userconfig = UserConfig(CONFIG_FOLDER, "userconfig.json")
        
        # Initialize DownloadThread
        self.download_thread = DownloadThread(parent)
        self.download_thread.cookies = self.cookies
        self.download_thread.finished.connect(self._thread_finished)
        self.download_thread.started.connect(self._thread_started)
        self.download_thread.progress.connect(self._update_progress)
        self.download_thread.state.connect(self._update_state)
        self.download_thread.download_speed.connect(self._update_speed)
        self.download_thread.estimated_time.connect(self._update_estimated_time)

        self.init_ui()
        self._load_queue()
        self._update_queue_list()
        
        if self.download_queue:
            self._process_queue()

    def init_ui(self):
        self._apply_stylesheet()
        
        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- Header Section ---
        header_layout = QHBoxLayout()
        title_label = QLabel("Downloads")
        title_label.setObjectName("header_title")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)

        # --- Active Download Card ---
        self.active_card = QFrame()
        self.active_card.setObjectName("active_card")
        
        active_layout = QVBoxLayout(self.active_card)
        active_layout.setContentsMargins(20, 20, 20, 20)
        active_layout.setSpacing(15)

        # Active Download Title
        self.active_title_label = QLabel("No Active Download")
        self.active_title_label.setObjectName("active_title")
        active_layout.addWidget(self.active_title_label)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        active_layout.addWidget(self.progress_bar)

        # Stats Row (Speed, ETA, Status)
        stats_layout = QHBoxLayout()
        
        self.speed_label = QLabel("0 KB/s")
        self.speed_label.setObjectName("stat_label")
        
        self.eta_label = QLabel("--:--:--")
        self.eta_label.setObjectName("stat_label")
        
        self.status_detail_label = QLabel("Waiting...")
        self.status_detail_label.setObjectName("stat_label")
        self.status_detail_label.setAlignment(Qt.AlignRight)

        stats_layout.addWidget(self.speed_label)
        stats_layout.addWidget(self.eta_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.status_detail_label)
        active_layout.addLayout(stats_layout)

        # Controls Row
        controls_layout = QHBoxLayout()
        
        self.pause_button = QPushButton("Pause")
        self.resume_button = QPushButton("Resume")
        self.stop_button = QPushButton("Stop")
        
        for btn in [self.pause_button, self.resume_button, self.stop_button]:
            btn.setCursor(Qt.PointingHandCursor)

        self.pause_button.clicked.connect(self.pause)
        self.resume_button.clicked.connect(self.resume)
        self.stop_button.clicked.connect(self.stop)

        # Initial states
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)

        controls_layout.addWidget(self.pause_button)
        controls_layout.addWidget(self.resume_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addStretch()
        
        # Speed Limit Input
        speed_container = QWidget()
        speed_layout = QHBoxLayout(speed_container)
        speed_layout.setContentsMargins(0,0,0,0)
        
        speed_lbl = QLabel("Max Speed (KB/s):")
        speed_lbl.setObjectName("stat_label")
        
        self.speed_input = QLineEdit()
        self.speed_input.setFixedWidth(80)
        self.speed_input.setPlaceholderText("∞")
        self.speed_input.setValidator(QIntValidator(0, 9999999))
        self.speed_input.setText(str(self.userconfig.DOWNLOAD_SPEED))
        self.speed_input.textChanged.connect(self.set_max_speed_from_input)
        
        speed_layout.addWidget(speed_lbl)
        speed_layout.addWidget(self.speed_input)
        
        controls_layout.addWidget(speed_container)
        active_layout.addLayout(controls_layout)

        main_layout.addWidget(self.active_card)

        # --- Queue Section ---
        queue_label = QLabel("Queue")
        queue_label.setObjectName("queue_header")
        main_layout.addWidget(queue_label)

        self.queue_list = QListWidget()
        
        # Enable Drag & Drop for reordering
        self.queue_list.setDragDropMode(QListWidget.InternalMove)
        self.queue_list.setDefaultDropAction(Qt.MoveAction)
        self.queue_list.setSelectionMode(QListWidget.SingleSelection)
        
        # Context Menu
        self.queue_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._show_context_menu)
        
        # Connect signal to handle reordering
        self.queue_list.model().rowsMoved.connect(self._on_queue_order_changed)

        main_layout.addWidget(self.queue_list)
        
        # Queue Controls
        queue_controls_layout = QHBoxLayout()
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("remove_btn")
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(self._remove_selected_item)
        
        drop_hint = QLabel("Drag items to reorder")
        drop_hint.setObjectName("hint_label")
        
        queue_controls_layout.addWidget(remove_btn)
        queue_controls_layout.addStretch()
        queue_controls_layout.addWidget(drop_hint)
        
        main_layout.addLayout(queue_controls_layout)

    def _apply_stylesheet(self):
         try:
            with open("src/Downloads.qss", "r") as f:
                self.setStyleSheet(f.read())
         except:
             logging.warning("Could not load stylesheet src/Downloads.qss")

    def _show_context_menu(self, position):
        menu = QMenu()
        
        # Download Now Action
        download_now_action = QAction("Download Now", self)
        download_now_action.triggered.connect(self._download_now_action)
        menu.addAction(download_now_action)
        
        menu.addSeparator()

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self._remove_selected_item)
        menu.addAction(remove_action)
        
        menu.exec_(self.queue_list.mapToGlobal(position))

    def _download_now_action(self):
        row = self.queue_list.currentRow()
        if row < 0 or row >= len(self.download_queue):
            return
            
        logging.info(f"Prioritizing item at index {row}")
        
        # Move item to top
        item = self.download_queue.pop(row)
        self.download_queue.insert(0, item)
        self._save_queue()
        self._update_queue_list()
        
        # Select the moved item (now at index 0)
        self.queue_list.setCurrentRow(0)
        
        if self.is_downloading:
             # Stop current download to start the new top item
             logging.info("Stopping current download to start prioritized item...")
             self.should_process_queue_after_stop = True
             self.stop()
        else:
             self._process_queue()

    def _save_queue(self):
        with open(os.path.join(CONFIG_FOLDER, "downloads.json"), "w") as f:
            json.dump(self.download_queue, f, indent=4)

    def _load_queue(self):
        try:
            with open(os.path.join(CONFIG_FOLDER, "downloads.json"), "r") as f:
                self.download_queue = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.download_queue = []
            self._save_queue()

    def _update_queue_list(self):
        # Disconnect signal temporarily to prevent feedback loop
        try:
            self.queue_list.model().rowsMoved.disconnect(self._on_queue_order_changed)
        except TypeError:
            pass # Signal might not be connected yet

        self.queue_list.clear()
        for item in self.download_queue:
            self.queue_list.addItem(item.get("alias", get_name_from_url(item.get("url"))))
            
        # Reconnect signal
        self.queue_list.model().rowsMoved.connect(self._on_queue_order_changed)

    def start(self, url):
        # 1. Check Current Download
        if self.current_download and self.current_download.get("url") == url:
            logging.info(f"Skipping duplicate add: {url} is currently downloading.")
            return

        # 2. Check Queue
        for item in self.download_queue:
            if item.get("url") == url:
                logging.info(f"Skipping duplicate add: {url} is already in queue.")
                return

        # Add to queue
        download_item = {
            "url": url,
            "status": "queued",
            "version": "Pending"
        }
        self.download_queue.append(download_item)
        self._save_queue()
        
        # Add to UI
        self.queue_list.addItem(download_item.get("alias", get_name_from_url(url)))

        if not self.is_downloading:
            self._process_queue()

    def _process_queue(self):
        if not self.download_queue:
            self.active_title_label.setText("No Active Download")
            self.status_detail_label.setText("Idle")
            self.progress_bar.setValue(0)
            self.speed_label.setText("🚀 0 KB/s")
            self.eta_label.setText("⏱ --:--:--")
            return
        
        # Always take the first item from the (potentially reordered) queue
        self.current_download = self.download_queue[0]
        url = self.current_download["url"]
        game_name = get_name_from_url(url)
        
        self.is_downloading = True
        self.active_title_label.setText(f"{game_name}")
        self.status_detail_label.setText("Starting...")
        
        self.resume_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)

        # Create a new thread
        self.download_thread = DownloadThread(self.my_parent)
        self.download_thread.cookies = self.cookies
        self.download_thread.set_params(url)
        self.download_thread.finished.connect(self._thread_finished)
        self.download_thread.started.connect(self._thread_started)
        self.download_thread.progress.connect(self._update_progress)
        self.download_thread.state.connect(self._update_state)
        self.download_thread.download_speed.connect(self._update_speed)
        self.download_thread.estimated_time.connect(self._update_estimated_time)
        self.update_max_speed()
        self.download_thread.start()

    def _thread_finished(self):
        self.is_downloading = False
        success = self.download_thread.success
        self.download_thread.cleanParams()
        
        if success:
            self.current_download = None
            if self.download_queue:
                self.download_queue.pop(0)
            self._save_queue()
            self._update_queue_list()
            
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.progress_bar.setValue(0)
            self.speed_label.setText("0 KB/s")
            self.eta_label.setText("--:--:--")
            
            self._process_queue()
        else:
            # Download failed or stopped - Keep in queue
            self.pause_button.setEnabled(False)
            self.resume_button.setEnabled(True) # Enable to allow restart
            self.stop_button.setEnabled(False)
            logging.info("Download stopped or failed. Item remains in queue for restart.")
            self.status_detail_label.setText("Stopped/Failed")

            if hasattr(self, 'should_process_queue_after_stop') and self.should_process_queue_after_stop:
                self.should_process_queue_after_stop = False
                logging.info("Auto-restarting queue for prioritized item...")
                self._process_queue()
    
    def set_max_speed_from_input(self):
        speed = self.speed_input.text()
        if speed.isdigit():
            self.userconfig.DOWNLOAD_SPEED = int(speed)
            self.userconfig.save()
            self.update_max_speed()
    
    def update_max_speed(self):
        if self.download_thread:
            self.download_thread.max_speed = self.userconfig.DOWNLOAD_SPEED
    
    def resume(self):
        if self.download_thread.isRunning():
            self.download_thread.resume()
            self.status_detail_label.setText("Resumed")
        else:
            # Restart dead thread
            logging.info("Restarting download...")
            self._process_queue()
            
        self.resume_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
    
    def stop(self):
        if self.download_thread:
            self.download_thread.stop()
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.status_detail_label.setText("Stopping...")
    
    def pause(self):
        if self.download_thread:
            self.download_thread.pause()
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.status_detail_label.setText("Paused")
    
    def _update_progress(self, value):
        self.progress_bar.setValue(value)
    
    def _update_state(self, state):
        self.status_detail_label.setText(state)
    
    def _update_speed(self, speed):
        self.speed_label.setText(f"🚀 {speed}")
    
    def _update_estimated_time(self, estimated_time):
        self.eta_label.setText(f"⏱ {estimated_time}")
    
    def _remove_selected_item(self):
        current_row = self.queue_list.currentRow()
        if current_row < 0:
            return

        # Check if we are deleting the active download (always index 0 if downloading)
        if current_row == 0 and self.is_downloading:
            reply = QMessageBox.question(
                self, 
                "Stop Download?", 
                "This download is currently running. Stop and delete it?", 
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
            
            # Stop the thread
            self.download_thread.stop()
            self.download_thread.wait(2000) # Wait for thread to cleanup
            self.is_downloading = False
            self.status_detail_label.setText("Stopped/Deleted")

        # Remove from data
        if current_row < len(self.download_queue):
            removed_item = self.download_queue.pop(current_row)
            url = removed_item.get('url')
            logging.info(f"Removed from queue: {removed_item.get('alias', 'Unknown')}")
            self._save_queue()
            
            # Delete Cache Files
            self._delete_cache_files(url)
        
        # Remove from UI
        self.queue_list.takeItem(current_row)
        
        # If we deleted the active item (row 0), reset active card or start next
        if current_row == 0:
            self.current_download = None
            self.active_title_label.setText("No Active Download")
            self.progress_bar.setValue(0)
            self.speed_label.setText("🚀 0 KB/s")
            self.eta_label.setText("⏱ --:--:--")
            
            # Auto-start next if available
            if self.download_queue:
                self._process_queue()

    def _delete_cache_files(self, url):
        if not url: return
        
        try:
            file_hash = hash_url(url)
            cache_path = os.path.join(os.getcwd(), "DownloadCache")
            
            # Define patterns to delete
            targets = [
                os.path.join(cache_path, f"{file_hash}.rar"),       # The archive
                os.path.join(cache_path, f"{file_hash}"),           # The extraction folder
            ]
            # Add part files
            targets.extend(glob.glob(os.path.join(cache_path, f"{file_hash}_part_*")))
            
            for target in targets:
                if os.path.exists(target):
                    if os.path.isfile(target):
                        os.remove(target)
                        logging.info(f"Deleted cache file: {target}")
                    elif os.path.isdir(target):
                        shutil.rmtree(target)
                        logging.info(f"Deleted cache folder: {target}")
                        
        except Exception as e:
            logging.error(f"Error deleting cache files for {url}: {e}")

    def _on_queue_order_changed(self, parent, start, end, destination, row):
        # Reconstruct the queue list from the UI order
        new_queue = []
        for i in range(self.queue_list.count()):
            item_text = self.queue_list.item(i).text()
            # Find the matching item in the old queue (inefficient but functional for small lists)
            for download_item in self.download_queue:
                if download_item.get("alias") == item_text or get_name_from_url(download_item.get("url")) == item_text:
                    new_queue.append(download_item)
                    break
        
        if len(new_queue) == len(self.download_queue):
            self.download_queue = new_queue
            self._save_queue()
        else:
            # Fallback if matching failed (e.g. duplicates names)
            logging.warning("Queue reorder sync mismatch, reloading from file.")
            self._load_queue()
            self._update_queue_list()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self._remove_selected_item()
        else:
            super().keyPressEvent(event)
    
    def _thread_started(self):
        self.is_downloading = True
        logging.debug("Download thread started.")
