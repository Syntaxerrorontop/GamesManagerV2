from PyQt5.QtCore import Qt,  QThread, pyqtSignal
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QWidget, QProgressBar
import os, time, json, requests, logging, string, re, random, ctypes, urllib.parse, threading, subprocess, shutil
from playwright.sync_api import sync_playwright
from concurrent.futures import ThreadPoolExecutor

from .utility.utility_functions import save_json, load_json, hash_url, get_name_from_url, _get_version_steamrip, _game_naming
from .utility.utility_classes import Payload, Header, UserConfig
from .utility.utility_vars import CONFIG_FOLDER, CACHE_FOLDER

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
                    print(f"Working proxy found: {proxy}")
                    return proxy_dict  # Return the working proxy
            except requests.RequestException:
                logging.warning(f"Proxy {proxy} failed, trying next one.")
                time.sleep(0.1)  # Small delay before trying next proxy

    except FileNotFoundError:
        print(f"Error: Proxy file '{proxy_file_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None  # No working proxy found

class MegaDB:
    def __init__(self):
        self.dl = None
    
    def download_link(self, url):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, timeout=60000)
            ctx = browser.new_context()
            page = ctx.new_page()
            self.dl = None

            page.on("response", self.on_response)
            logging.debug(f"Navigating to {url}")
            page.goto(url, wait_until="networkidle")
            frame = page.frame_locator("iframe[title='reCAPTCHA']")
            # Click the checkbox inside the iframe
            frame.locator("#recaptcha-anchor").click()
            checkbox = frame.locator("#recaptcha-anchor")
            # Click the checkbox (may trigger challenge)
            checkbox.click()
            logging.debug("Clicked reCAPTCHA checkbox")
            checkbox.wait_for(state="attached")  # ensure element exists
            frame.locator("#recaptcha-anchor[aria-checked='true']").wait_for(timeout=0)  # wait until checked
            download_btn = page.wait_for_selector("#downloadbtn", timeout=10000)
            # Click the download button
            page.wait_for_selector("#countdown", state="hidden", timeout=0)  # timeout=0 waits indefinitely
            logging.debug("Countdown finished ✅")
            download_btn.click()
            logging.debug("Clicked download button ✅")
            while not self.dl:
                time.sleep(0.001)
            browser.close()
            return self.dl
    
    def on_response(self, response):
        try:
            if "https://megadb.net/download" == response.url and 302 == response.status:
                logging.info(f"Detected download redirect: {response.url}")
                logging.info(f"Headers: {response.headers}")
                logging.info(f"Status: {response.status}")
                logging.info(f"location: {response.headers.get('location')}")
                logging.info(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
                self.dl = response.headers.get("location")
        except Exception as e:
            logging.error("on_response error:", e)

class DirectLinkDownloader:
    @staticmethod
    def megadb(url) -> str:
        try:
            link = None
            mega_db_helper = MegaDB()
            link = mega_db_helper.download_link(url)
            logging.info("Downloader:megadb Waiting for download link")
            while link == None:
                time.sleep(0.1)
        except KeyboardInterrupt:
            logging.info("Downloader:megadb Server stopped")
            
        return {"url": link, "payload": {}, "headers": {}, "method": "get"}
    
    @staticmethod
    def filecrypt(url) -> str:
        logging.debug(url)
        return None
    
    @staticmethod
    def buzzheavier(url) -> str:
        logging.debug(url)
        return {"url": url.replace(r"/f/", r"/") + "/download", "payload": {}, "headers": {} , "method": "get"}
    
    @staticmethod
    def ficher(url) -> str:
        try:
            logging.info("Downloader:1Ficher Using Ficher this can take up to 3 Minutes")
            steps = ["#cmpwelcomebtnyes > a", "#cmpbntyestxt", "#dlw"]
            
            with sync_playwright() as p:
                logging.info("Downloader:1Ficher Creating Broswser intance")
                browser = p.webkit.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                logging.info("Downloader:1Ficher Successfull")
                
                page.goto(url)
                logging.info("Downloader:1Ficher Site loading finished")
                if page.locator("#closeButton").count() > 0:
                    ctypes.windll.user32.MessageBoxW(0, "1Ficher file hosting has a limitation of max downloads\n1 per houre this process will be stopped", "1ficher is on cooldown", 0x40 | 0x1)  
                    page.close()
                    browser.close()
                    return -1

                for step in steps:
                    start_time = time.time()  # Record the start time
                    page.wait_for_selector(step, timeout=1000000)
                    if step == "#dlw":
                        time.sleep(60)
                        page.click(step)                
                    elapsed_time = time.time() - start_time  # Calculate elapsed time
                    logging.info(f"Downloader:1Ficher EXECUTED: {step} in {elapsed_time:.2f} seconds")
                
                page.wait_for_selector("body > div.alc > div:nth-child(6) > a", timeout=5000)
                link = page.locator("body > div.alc > div:nth-child(6) > a").get_attribute("href")
                page.close()
                browser.close()
            
            return {"url": link, "payload": {}, "headers": {}, "method": "get"}
        except Exception as e:
            logging.error(f"Downloader:1Ficher Error: {e}")
            return -1

    @staticmethod
    def datanode(url) -> str:
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
    
    @staticmethod
    def gofile(url) -> str:
        logging.info("Downloader:gofile Generating download link using gofile this may take up to 2 Minutes")
        _id = url.split("/")[-1]
        with sync_playwright() as p:
            logging.info("Downloader:gofile Launching playwright Instance (Chromium)")
            # Launch the browser
            browser = p.webkit.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            link = ""
            accounttoken = ""

            def on_response(response):
                nonlocal link, page, browser, _id
                if response.url.startswith(f"https://api.gofile.io/contents/{_id}?"):
                    logging.info("Downloader:gofile Data Retrieved")
                    try:
                        
                        data = json.loads(response.text())
                        file = list(data["data"]['children'].keys())[0]
                        link = data["data"]['children'][file]["link"]
                        logging.debug(link)
                    except Exception as e:
                        logging.error(f"Downloader:gofile Failed to get response body: {e}")
                        
            page.on("response", on_response)

            logging.info(f"Downloader:gofile Visiting {url} for Direct Download Link extraction")
            page.goto(url)
            
            logging.info("Downloader:gofile Waiting until successfull link and cookie extraction if this take longer then 2 Minutes please close the Programm")
            
            while not link and not accounttoken:
                page.wait_for_timeout(1000)
                
                if not accounttoken:
                    cookies = context.cookies()
                    for cookie in cookies:
                        if cookie["name"] == "accountToken":
                            accounttoken = cookie["value"]
                            logging.info(f"Downloader:gofile Successfull found Cookie: {accounttoken}")
            
            logging.info(f"Downloader:gofile Successfull found link: {link}")
            
            page.close()
            browser.close()
            return {"url": link, "payload": {}, "headers": {"Cookie": f"accountToken={accounttoken}"}, "method": "get"}

class Downloader:
    @staticmethod
    def steamrip(url, data, scraper):
        try:
            #response = requests.get(url, cookies=cookies)
            
            #response.raise_for_status()
            
            #page_content = response.text
            page_content = scraper.get_html(url)
            
            for i in page_content.split("script"):
                if "DOWNLOAD" in i:
                    print
                    #logging.debug(i)
                    pass
            
            logging.info("Downloader:steamrip Extracting downloadable links")
            
            found_links = {}
            
            for key, data in data["provider"].items():

                regex_finder = re.findall(data["pattern"], page_content)
                
                if regex_finder and len(regex_finder) == 1:
                    found_links[key] = data["formaturl"].format(detected_link = regex_finder[0])
                else:
                    found_links[key] = None
            
            logging.info(f"Downloader:steamrip Detected download links: {found_links}")
            
            logging.info(f"Downloader:steamrip Generating Filename")
            try:
                name = url[:-1].split("/")[-1].split("free-download")[0][:-1].replace("-","_")
            except:
                logging.warning("Downloader:steamrip Error while generating name continuing with random name")
                name = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            
            return found_links, name
                
        except requests.RequestException as e:
            logging.error(f"Downloader:steamrip Error fetching the URL: {e}")

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
                "pattern": r'<a\s+href="\/\/buzzheavier\.com\/([^"]+)"',
                "formaturl": "https://buzzheavier.com/{detected_link}",
                "priority": 5,
                "downloader": DirectLinkDownloader.buzzheavier,
                "enabled": False
            },
            "fichier": {
                "pattern": r'1fichier\.com/\?([^"]+)',
                "formaturl": "https://1fichier.com/?{detected_link}",
                "priority": 3,
                "downloader": DirectLinkDownloader.ficher,
                "enabled": True
            },
            "datanode": {
                "pattern": r'<a\s+href="\/\/datanodes\.to\/([^"]+)"',
                "formaturl": "https://datanodes.to/{detected_link}",
                "priority": 4,
                "downloader": DirectLinkDownloader.datanode,
                "enabled": True
            },
            "megadb": {
                "pattern": r'<a\s+href="\/\/megadb\.net\/([^"]+)"',
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
        self.total_downloaded = 0  # Initialize total downloaded bytes
        self.last_report_time = time.time()
        self.last_report_bytes = 0
        self.mega_db_worker_number = 12
        self.default_worker = 2

    def cleanParams(self):
        """Reset URL and installation state."""
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
        self.total_downloaded = 0  # Initialize total downloaded bytes
        self.last_report_time = time.time()
        self.last_report_bytes = 0
        self.mega_db_worker_number = 12
        
    def set_params(self, url):
        """Set URL and installation state without creating a new thread."""
        self.url = url
    
        self.current_hash = hash_url(url)
        self.downloaded_bytes = 0

    def run(self):
        url_backup=self.url
        if not os.path.exists(os.path.join(os.getcwd(), "DownloadCache")):
            os.mkdir(os.path.join(os.getcwd(), "DownloadCache"))
        
        error = {
            -1: "1Ficher on cooldown"
        }
        if not self.url:
            self.state.emit("Error: No URL set!")
            return

        self.started.emit()
        self.state.emit(f"Preparing download...")
        self.running = True

        __links, name = Downloader.steamrip(self.url, downloader_data, self.my_parrent.scraper)
        self.state.emit(f"Finding Best link...")
        __best_downloader, __best_downloader_key = _get_best_downloader(__links)
        
        if __best_downloader is None:
            logging.error("Could not find a downloader")
            return
        
        logging.info(f"Downloader: Best downloader: {__best_downloader_key}")
    
        __downloader_function = __best_downloader["downloader"]
        
        __download_request = __downloader_function(__links[__best_downloader_key])
        if isinstance(__download_request, int):
            logging.error(error[__download_request])
            logging.info("We are getting the next best Downlaoder")
            
            __best_downloader, __best_downloader_key = _get_best_downloader(__links, ignore=__best_downloader_key)
            if __best_downloader is None:
                logging.error("Could not find a better Downloader...")
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
            pass
        
        if __best_downloader_key == "megadb":
                self.num_parts = self.mega_db_worker_number
                __download_url_megadb = __download_request["url"]

                response = requests.head(__download_url_megadb)
                file_size = int(response.headers.get('Content-Length', 0))
                self.total_size = file_size  # Store the total size for progress calculation
                skip = False
                if os.path.exists(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")):
                    existing_size = os.path.getsize(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar"))
                    if existing_size == file_size:
                        logging.info("File already downloaded, skipping download.")
                        self.state.emit(f"File already downloaded, skipping download.")
                        skip = True
                
                # Calculate part size and ranges
                part_size = file_size // self.mega_db_worker_number
                ranges = [(i * part_size, (i + 1) * part_size - 1) for i in range(self.mega_db_worker_number)]
                ranges[-1] = (ranges[-1][0], file_size - 1)  # Ensure last part gets the remainder

                if not skip:
                    # Download parts in parallel using ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=self.mega_db_worker_number) as executor:
                        futures = []
                        proxy = None
                        for i, (start, end) in enumerate(ranges):
                            
                            futures.append(executor.submit(self.download_part, i, start, end, file_size, __download_url_megadb))
                            time.sleep(2)
                            
                            while self.pause_create:
                                QThread.msleep(100)

                        # Wait for all futures to complete
                        for future in futures:
                            future.result()

                    # Combine parts after download
                    if not self._is_stopped:
                        self.combine_parts()
        
        else:
            url = __download_request["url"]
            headers = __download_request["headers"]
            payload = __download_request["payload"]
            
            response = requests.head(url, headers=headers, data=payload)
            file_size = int(response.headers.get('Content-Length', 0))
            self.total_size = file_size  # Store the total size for progress calculation
            skip = False
            
            if os.path.exists(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")):
                    existing_size = os.path.getsize(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar"))
                    if existing_size == file_size:
                        logging.info("File already downloaded, skipping download.")
                        self.state.emit(f"File already downloaded, skipping download.")
                        skip = True
                
                # Calculate part size and ranges
            if self.default_worker > 0:
                part_size = file_size // self.default_worker
                ranges = [(i * part_size, (i + 1) * part_size - 1) for i in range(self.default_worker)]
                ranges[-1] = (ranges[-1][0], file_size - 1)  # Ensure last part gets the remainder

                if not skip:
                        # Download parts in parallel using ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=self.default_worker) as executor:
                        futures = []
                        for i, (start, end) in enumerate(ranges):
                            time.sleep(0.5)
                            futures.append(executor.submit(self.download_part, i, start, end, file_size, url, headers, payload, self.default_worker))

                            # Wait for all futures to complete
                        for future in futures:
                            future.result()

                    if not self._is_stopped:
                        self.combine_parts()
            else:
                if not skip:
                    self.download_file(url, headers, payload, file_size)
        
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
        process = subprocess.Popen([os.path.join(os.getcwd(), "Tools", "UnRAR.exe"), "x", "-y",rar_path, folder_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered output
            universal_newlines=True
        )
        try:
            while process.poll() is None:
                for line in process.stdout:
                    print(line)
                    match = re.search(r'(\d+)%', line)
                    if match:
                        percent = int(match.group(1))  # Extract percentage
                        self.progress.emit(percent)  # Emit the progress signal

        except AttributeError:
            self.progress.emit(100)
        
        process.wait()
        
        logging.debug(process.returncode)
        for file in os.listdir(folder_path):
            if file == "_CommonRedist":
                continue
            if os.path.isdir(os.path.join(folder_path, file)):
                rename_path = os.path.join(folder_path, file)
        
        if os.path.exists(os.path.join(os.getcwd(), "Games", self.current_hash)):
            shutil.rmtree(os.path.join(os.getcwd(), "Games", self.current_hash))
        
        time.sleep(1)

        os.rename(rename_path, os.path.join(folder_path, self.current_hash))
        
        shutil.move(os.path.join(folder_path, self.current_hash), os.path.join(os.getcwd(), "Games"))
        
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
            data[self.current_hash] = {"args": [], "exe": exe_path, "name": self.current_hash, "alias": get_name_from_url(url_backup), "link": url_backup, "version": _get_version_steamrip(url_backup), "categorys": [], "playtime": 0}
        else:
            data[self.current_hash]["exe"] = exe_path
            data[self.current_hash]["version"] = _get_version_steamrip(url_backup)

        save_json(os.path.join(CONFIG_FOLDER, "games.json"), data)
        
        shutil.rmtree(os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}"))
        os.remove(rar_path)
        self.state.emit(f"Finished")
        self.finished.emit()
    
    def download_file(self, url, headers, payload, total_size):
        """Download a single file with resume, pause, stop, and optional speed limit (0 = unlimited)."""
        filename = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")

        # Resume support
        downloaded_size = 0
        if os.path.exists(filename):
            downloaded_size = os.path.getsize(filename)
            self.total_downloaded += downloaded_size
            #if downloaded_size >= total_size:
            #    logging.info("File already fully downloaded. Skipping.")
            #    self.progress.emit(100)
            #    self.state.emit("Download already completed~")
            #    return

        # Only set Range header if we need to resume
        if downloaded_size > 0:
            headers['Range'] = f"bytes={downloaded_size}-{total_size - 1}"

        response = requests.get(url, headers=headers, data=payload, stream=True)

        if response.status_code not in (200, 206):
            logging.error(f"Failed to request content. Status code: {response.status_code}")
            self.state.emit("Download failed~")
            return

        # Speed limiting setup
        max_bytes_per_sec = self.max_speed * 1024 if self.max_speed > 0 else None
        chunk_size = 1024
        start_time = time.time()
        bytes_this_second = 0

        with open(filename, 'ab') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if self._is_stopped:
                    logging.info("Download stopped.")
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

                # Emit progress
                self.total_downloaded += len(chunk)
                if downloaded_size!=0:
                    progress_percentage = (downloaded_size / total_size) * 100
                    self.progress.emit(int(progress_percentage))
                self.calculate_speed()

                # Limit speed if enabled
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

    def download_part(self, part_num, start, end, total_size, url, headers=None, payload=None, max_worker = 0,proxy=None):
        """Download a part of the file with resume, pause, stop, and optional speed limit."""
        filename = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}_part_{part_num}")

        if max_worker!=0:
            self.mega_db_worker_number = max_worker
        
        # Resume support
        if os.path.exists(filename):
            existing_size = os.path.getsize(filename)
            if existing_size >= (end - start + 1):
                logging.info(f"Part {part_num} already downloaded, skipping.")
                self.pause_create = False
                self.total_downloaded += existing_size
                progress_percentage = (self.total_downloaded / total_size) * 100
                self.progress.emit(int(progress_percentage))
                self.parts[part_num] = filename
                return
            start = existing_size + start
            logging.info(f"Resuming part {part_num} from byte {start}.")
        if headers == None or headers == {}:
            headers = {'Range': f"bytes={start}-{end}"}
        else:
            headers['Range'] = f"bytes={start}-{end}"
        response = requests.get(url, headers=headers, data=payload, stream=True, proxies=self.current_proxy)

        if response.status_code!=206 and response.status_code!=503:
            logging.error(f"Failed to request partial content for part {part_num}. Status code: {response.status_code}")
            logging.error(f"Response: {response.text}")
            return
        
        if response.status_code == 503:
            logging.error(f"503 Service Unavailable for part {part_num}. Trying again with a new proxy.")
            logging.info(f"Trying again with a new proxy. {response.text}")
            self.pause_create = True
            #self.current_proxy = get_working_proxy(os.path.join(os.getcwd(), "Cached", "proxy.txt"))
            #self.download_part(part_num, start, end, total_size, url, headers, payload, max_worker)
            return
        
        self.pause_create = False

        # Speed limiting
        max_bytes_per_sec = self.max_speed * 1024 / self.mega_db_worker_number if self.max_speed > 0 else None
        chunk_size = 1024
        start_time = time.time()
        bytes_this_second = 0

        with open(filename, 'ab') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if self._is_stopped:
                    break
                while self._is_paused:
                    QThread.msleep(100)
                if not chunk:
                    continue
                max_bytes_per_sec = self.max_speed * 1024 / self.mega_db_worker_number if self.max_speed > 0 else None
                f.write(chunk)
                self.total_downloaded += len(chunk)
                progress_percentage = (self.total_downloaded / total_size) * 100
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

    def combine_parts(self):
        if len(self.parts) < self.num_parts:
            self.state.emit("Error: Download failed. Not all parts were downloaded.")
            return

        output_file_path = os.path.join(os.getcwd(), "DownloadCache", f"{self.current_hash}.rar")
        with open(output_file_path, 'wb') as output_file:
            for i in range(self.num_parts):
                if i not in self.parts:
                    self.state.emit(f"Error: Missing part {i}. Cannot combine files.")
                    return
                with open(self.parts[i], 'rb') as part_file:
                    output_file.write(part_file.read())

        # Teile löschen nach dem Kombinieren
        for part_path in self.parts.values():
            try:
                os.remove(part_path)
            except Exception as e:
                print(f"Failed to delete part {part_path}: {e}")


    def calculate_speed(self):
        """Calculate and emit download speed and estimated remaining time with smoothing."""
        current_time = time.time()
        time_diff = current_time - self.last_report_time

        if time_diff >= 1:
            # Calculate raw speed
            speed = (self.total_downloaded - self.last_report_bytes) / time_diff
            # Keep history of speeds
            if not hasattr(self, "speed_history"):
                self.speed_history = []

            self.speed_history.append(speed)
            if len(self.speed_history) > 10:
                self.speed_history.pop(0)

            # Compute average speed over last 10 reports
            avg_speed = sum(self.speed_history) / len(self.speed_history)

            # Format average speed
            if avg_speed >= 1024**3:
                readable_speed = f"{avg_speed / (1024**3):.2f} GB/s"
            elif avg_speed >= 1024**2:
                readable_speed = f"{avg_speed / (1024**2):.2f} MB/s"
            elif avg_speed >= 1024:
                readable_speed = f"{avg_speed / 1024:.2f} KB/s"
            else:
                readable_speed = f"{avg_speed:.2f} B/s"
            self.download_speed.emit(readable_speed)

            # Estimated time based on average speed
            if avg_speed > 0:
                remaining_bytes = self.total_size - self.total_downloaded
                remaining_seconds = int(remaining_bytes / avg_speed)

                hours, rem = divmod(remaining_seconds, 3600)
                minutes, seconds = divmod(rem, 60)
                formatted_time = f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                formatted_time = "Calculating..."

            self.estimated_time.emit(formatted_time)

            # Update last checkpoint
            self.last_report_time = current_time
            self.last_report_bytes = self.total_downloaded

    def pause(self):
        """Pause the download."""
        self._is_paused = True

    def resume(self):
        """Resume the download."""
        self._is_paused = False

    def stop(self):
        """Stop the download."""
        self._is_stopped = True

class DownloadManager(QWidget):
    def __init__(self, parent):
        super().__init__()
        self.my_parent = parent
        self.cookies = {}
        self.is_downloading = False
        self.userconfig = UserConfig(CONFIG_FOLDER, "userconfig.json")
        self.download_thread = DownloadThread(parent)
        self.download_thread.cookies = self.cookies

        self.download_thread.finished.connect(self._thread_finished)
        self.download_thread.started.connect(self._thread_started)
        self.download_thread.progress.connect(self._update_progress)
        self.download_thread.state.connect(self._update_state)
        self.download_thread.download_speed.connect(self._update_speed)
        self.download_thread.estimated_time.connect(self._update_estimated_time)

        layout = QVBoxLayout()

        # State label
        self.state_label = QLabel("Waiting for download...", self)
        self.state_label.setAlignment(Qt.AlignCenter)
        self.state_label.setStyleSheet("color: #ffffff; font-size: 18px; padding: 10px;font-family: 'Montserrat', sans-serif;")
        layout.addWidget(self.state_label)

        # Download progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #555555;
                border-radius: 10px;
                height: 20px;
                padding: 2px;
                font-family: 'Montserrat', sans-serif;
            }
            QProgressBar::chunk {
                background-color: #66cc66;
                border-radius: 10px;
                font-family: 'Montserrat', sans-serif;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        speed_label = QLabel("Max Speed (KB/s):", self)
        speed_label.setStyleSheet("color: #ffffff; font-size: 14px;font-family: 'Montserrat', sans-serif;")
        layout.addWidget(speed_label)

        self.speed_input = QLineEdit(self)
        self.speed_input.setValidator(QIntValidator(0, 1000000, self))
        self.speed_input.setPlaceholderText("0 = unlimited")
        self.speed_input.setText(str(self.userconfig.DOWNLOAD_SPEED))
        self.speed_input.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #666666;
                border-radius: 8px;
                font-family: 'Montserrat', sans-serif;
            }
        """)
        layout.addWidget(self.speed_input)
        #self.set_speed_button.clicked.connect(self.set_max_speed_from_input)
        self.speed_input.textChanged.connect(self.set_max_speed_from_input)
        # Estimated time label
        self.estimated_time_label = QLabel("Estimated time: 00:00", self)
        self.estimated_time_label.setAlignment(Qt.AlignCenter)
        self.estimated_time_label.setStyleSheet("color: #ffffff; font-size: 14px;font-family: 'Montserrat', sans-serif;")
        layout.addWidget(self.estimated_time_label)
        self.speed_lable = QLabel("Speed")
        self.speed_lable.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.speed_lable.setStyleSheet("color: #ffffff; font-size: 14px;font-family: 'Montserrat', sans-serif;")
        layout.addWidget(self.speed_lable)
        # Buttons
        button_layout = QHBoxLayout()

        self.pause_button = QPushButton("Pause", self)
        self.pause_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 12px;
                padding: 10px;
                font-size: 16px;
                font-family: 'Montserrat', sans-serif;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.pause)
        button_layout.addWidget(self.pause_button)

        self.resume_button = QPushButton("Resume", self)
        self.resume_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 12px;
                padding: 10px;
                font-size: 16px;
                font-family: 'Montserrat', sans-serif;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        self.resume_button.setEnabled(False)
        self.resume_button.clicked.connect(self.resume)
        button_layout.addWidget(self.resume_button)

        self.stop_button = QPushButton("Stop", self)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 12px;
                padding: 10px;
                font-size: 16px;
                font-family: 'Montserrat', sans-serif;
            }
            QPushButton:hover {
                background-color: #e53935;
            }
        """)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        # Set layout for the window
        self.setLayout(layout)
    
    def set_max_speed_from_input(self):
        speed = self.speed_input.text()
        if speed.isdigit():
            data = load_json(os.path.join(CONFIG_FOLDER, "userconfig.json"))
            
            data["speed"] = speed
            
            save_json(os.path.join(CONFIG_FOLDER, "userconfig.json"), data)
            
            self.userconfig = UserConfig(CONFIG_FOLDER, "userconfig.json", quite=True)
            
            self.update_max_speed()
    
    def update_max_speed(self):
        self.download_thread.max_speed = int(self.userconfig.DOWNLOAD_SPEED)
    
    def resume(self):
        self.download_thread.resume()
        self.resume_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
    
    def stop(self):
        self.download_thread.stop()
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.is_downloading = False
    
    def pause(self):
        self.download_thread.pause()
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.stop_button.setEnabled(True)
    
    def _update_progress(self, value):
        # Update the progress bar
        self.progress_bar.setValue(value)
    
    def _update_state(self, state):
        # Update the state label
        self.state_label.setText(f"State: {state}")
    
    def _update_speed(self, speed):
        # Update the speed label
        self.speed_lable.setText(f"Speed: {speed}")
    
    def _update_estimated_time(self, estimated_time):
        # Update the estimated time label
        self.estimated_time_label.setText(f"Estimated Time: {estimated_time}")
    
    def _thread_started(self):
        self.is_downloading = True
        logging.debug("Download thread started.")
    
    def _thread_finished(self):
        self.download_thread.cleanParams()
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.is_downloading = False
        logging.debug("Download thread finished.")
    
    def start(self, url):
        if self.is_downloading:
            logging.warning("Downlaod Already Runnin!")
            return
        self.resume_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.is_downloading = True
        # Create a new instance every time
        self.download_thread = DownloadThread(self.my_parent)
        self.download_thread.set_params(url)

        # Reconnect signals
        self.download_thread.finished.connect(self._thread_finished)
        self.download_thread.started.connect(self._thread_started)
        self.download_thread.progress.connect(self._update_progress)
        self.download_thread.state.connect(self._update_state)
        self.download_thread.download_speed.connect(self._update_speed)
        self.download_thread.estimated_time.connect(self._update_estimated_time)

        # Start the thread
        self.download_thread.start()