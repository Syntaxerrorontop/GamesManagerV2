"""
Universal Web Scraper - A comprehensive scraping class that handles everything:
- Cloudflare challenges automatically
- HTML extraction and parsing
- Element clicking and interaction
- Asset downloading (images, files, etc.)
- Session persistence across requests
- Advanced anti-detection measures
"""
import os
import time
import logging
import platform
import re
from typing import Optional, Dict, Any, List, Union
from urllib.parse import urljoin, urlparse
import requests
from pathlib import Path
import psutil
import win32gui
import win32con
import win32process

# Install dependencies if needed

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located, title_is, staleness_of, element_to_be_clickable
from selenium.common import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup

# Challenge detection patterns
CHALLENGE_TITLES = ['Just a moment...', 'DDoS-Guard', 'Please verify you are human']
CHALLENGE_SELECTORS = [
    # Cloudflare
    '#cf-challenge-running', '.ray_id', '.attack-box', '#cf-please-wait', 
    '#challenge-spinner', '#trk_jschal_js', '#turnstile-wrapper', '.lds-ring',
    'td.info #js_info', 'div.vc div.text-box h2',
    # reCAPTCHA
    '.g-recaptcha', '[data-sitekey]', '.recaptcha-checkbox', 'iframe[src*="recaptcha"]',
    # hCaptcha
    '.h-captcha', '[data-hcaptcha-sitekey]', 'iframe[src*="hcaptcha"]',
    # Cloudflare Turnstile
    '.cf-turnstile', '[data-cf-turnstile-sitekey]'
]

# CAPTCHA specific selectors
CAPTCHA_SELECTORS = {
    'recaptcha_v2': {
        'checkbox': '.recaptcha-checkbox-border',
        'iframe': 'iframe[src*="recaptcha"]',
        'challenge_frame': 'iframe[src*="recaptcha"][src*="bframe"]'
    },
    'hcaptcha': {
        'checkbox': '.hcaptcha-checkbox',
        'iframe': 'iframe[src*="hcaptcha"]'
    },
    'turnstile': {
        'widget': '.cf-turnstile',
        'checkbox': '.cf-turnstile-wrapper'
    }
}

class UniversalScraper:
    """
    A comprehensive web scraper that handles Cloudflare challenges, 
    HTML extraction, clicking, and asset downloading.
    """
    
    def __init__(self, headless: bool = True, timeout: int = 30, download_dir: str = "."):
        """
        Initialize the Universal Scraper
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for operations
            download_dir: Directory to save downloaded files
        """
        self.driver = None
        self.headless = headless
        self.timeout = timeout
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.user_agent = None
        self.current_url = None
        self.session = requests.Session()
        
        # Setup colorful Minecraft-style logging
        self._setup_colored_logging()
        self.logger = logging.getLogger('UniversalScraper')
        
        # Set log level based on headless mode (less verbose when headless)
        if headless:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.DEBUG)
        
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        
    def _setup_colored_logging(self):
        """Setup colorful Minecraft-style logging with colors and brackets"""
        try:
            # Try to import colorama for Windows color support
            import colorama
            colorama.init(autoreset=True)
            
            # ANSI color codes
            class Colors:
                # Log level colors (Minecraft-inspired)
                DEBUG = '\033[37m'      # White
                INFO = '\033[32m'       # Green  
                WARNING = '\033[33m'    # Yellow
                ERROR = '\033[31m'      # Red
                CRITICAL = '\033[35m'   # Magenta
                
                # Component colors
                TIME = '\033[90m'       # Dark Gray
                THREAD = '\033[36m'     # Cyan
                FUNCTION = '\033[94m'   # Light Blue
                RESET = '\033[0m'       # Reset
                BOLD = '\033[1m'        # Bold
                
        except ImportError:
            # Fallback if colorama not available
            class Colors:
                DEBUG = WARNING = ERROR = CRITICAL = INFO = ''
                TIME = THREAD = FUNCTION = RESET = BOLD = ''
        
        class MinecraftFormatter(logging.Formatter):
            """Custom formatter with Minecraft-style colored output"""
            
            def format(self, record):
                # Create timestamp using the formatter's formatTime method
                timestamp = self.formatTime(record, self.datefmt)
                
                # Get thread name (proper thread name, not just ID)
                import threading
                current_thread = threading.current_thread()
                thread_name = current_thread.name if current_thread.name != 'MainThread' else 'Main'
                
                # If thread name is too long, shorten it
                if len(thread_name) > 12:
                    thread_name = thread_name[:12] + '...'
                    
                # Add thread ID for identification if needed
                if hasattr(record, 'thread'):
                    thread_id = record.thread
                    if thread_name == 'Main':
                        thread_name = f'Main-{thread_id}'
                    else:
                        thread_name = f'{thread_name}#{thread_id}'
                
                # Color mapping for log levels
                level_colors = {
                    'DEBUG': Colors.DEBUG,
                    'INFO': Colors.INFO,
                    'WARNING': Colors.WARNING,
                    'ERROR': Colors.ERROR,
                    'CRITICAL': Colors.CRITICAL
                }
                
                level_color = level_colors.get(record.levelname, Colors.INFO)
                
                # Format: [TIME][THREAD][LEVEL][COMPONENT] Message
                formatted_message = (
                    f"{Colors.TIME}[{timestamp}]"
                    f"{Colors.THREAD}[{thread_name}]"
                    f"{level_color}[{record.levelname}]"
                    f"{Colors.FUNCTION}[{record.name}:{record.funcName}:{record.lineno}]{Colors.RESET} "
                    f"{level_color}{record.getMessage()}{Colors.RESET}"
                )
                
                return formatted_message
        
        # Create and configure the formatter
        formatter = MinecraftFormatter()
        formatter.datefmt = '%H:%M:%S'  # Just time, no date needed
        
        # Configure root logger
        root_logger = logging.getLogger()
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create console handler with our formatter
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Add handler to root logger
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.DEBUG)
        
        # Also create a custom logger for selenium to reduce noise
        selenium_logger = logging.getLogger('selenium')
        selenium_logger.setLevel(logging.WARNING)
        
        urllib3_logger = logging.getLogger('urllib3')
        urllib3_logger.setLevel(logging.WARNING)
        
        uc_logger = logging.getLogger('undetected_chromedriver')
        uc_logger.setLevel(logging.INFO)
        
    def start(self) -> None:
        """Initialize the browser"""
        if self.driver is None:
            self.driver = self._create_webdriver()
            self._update_requests_session()
            
    def close(self) -> None:
        """Close the browser and cleanup"""
        if self.driver:
            try:
                if os.name == 'nt':
                    self.driver.close()
                self.driver.quit()
            except Exception as e:
                self.logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None
                
    def _create_webdriver(self) -> uc.Chrome:
        """Create undetected Chrome webdriver with optimal settings"""
        self.logger.info("Creating undetected Chrome webdriver...")
        
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-search-engine-choice-screen')
        options.add_argument('--disable-setuid-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--no-zygote')
        options.add_argument('--disable-blink-features=AutomationControlled')
        # Note: Some Chrome options may not be compatible with all versions
        
        # ARM architecture support
        if platform.machine().startswith(('arm', 'aarch')):
            options.add_argument('--disable-gpu-sandbox')
            
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--ignore-ssl-errors')
        
        # Language setting
        language = os.environ.get('LANG', 'en-US')
        options.add_argument(f'--accept-lang={language}')
        
        # Windows headless mode
        windows_headless = self.headless
        
        try:
            driver = uc.Chrome(
                options=options, 
                windows_headless=windows_headless,
                headless=self.headless,
                use_subprocess=True,
            )
            
            def hide_chrome_windows():
                chrome_names = ["chrome.exe", "chromedriver.exe"]

                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] in chrome_names:
                        pid = proc.info['pid']
                        def callback(hwnd, _):
                            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                            if found_pid == pid:
                                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                        win32gui.EnumWindows(callback, None)

            hide_chrome_windows()
            self.logger.info(f"Browser Hiden on Windows")
            # Execute script to remove webdriver property
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Get user agent
            self.user_agent = driver.execute_script("return navigator.userAgent")
            self.logger.info(f"Browser User-Agent: {self.user_agent}")
            
            return driver
            
        except Exception as e:
            self.logger.error(f"Error creating webdriver: {e}")
            raise
            
    def _update_requests_session(self) -> None:
        """Update requests session with current browser cookies and headers"""
        if not self.driver:
            return
            
        # Clear existing cookies
        self.session.cookies.clear()
        
        # Copy cookies from browser
        for cookie in self.driver.get_cookies():
            self.session.cookies.set(
                cookie['name'], 
                cookie['value'], 
                domain=cookie.get('domain'),
                path=cookie.get('path', '/')
            )
        
        # Update headers
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def _detect_challenge(self) -> bool:
        """Detect if there's a Cloudflare challenge"""
        if not self.driver:
            return False
            
        page_title = self.driver.title
        
        # Check title-based detection
        for title in CHALLENGE_TITLES:
            if title.lower() == page_title.lower():
                self.logger.info(f"Challenge detected by title: {page_title}")
                return True
        
        # Check selector-based detection
        for selector in CHALLENGE_SELECTORS:
            found_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            if len(found_elements) > 0:
                self.logger.info(f"Challenge detected by selector: {selector}")
                return True
        
        return False
        
    def _wait_for_challenge_completion(self, timeout: int = None) -> bool:
        """Wait for Cloudflare challenge to complete"""
        timeout = timeout or self.timeout
        self.logger.info("Waiting for challenge to complete...")
        
        html_element = self.driver.find_element(By.TAG_NAME, "html")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Wait until challenge titles disappear
                for title in CHALLENGE_TITLES:
                    WebDriverWait(self.driver, 1).until_not(title_is(title))
                
                # Wait until challenge selectors disappear
                for selector in CHALLENGE_SELECTORS:
                    WebDriverWait(self.driver, 1).until_not(
                        presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                
                break
                
            except TimeoutException:
                continue
        
        # Wait for redirect
        try:
            WebDriverWait(self.driver, 2).until(staleness_of(html_element))
        except TimeoutException:
            pass
        
        self.logger.info("Challenge resolution complete!")
        return True
        
    def goto(self, url: str, wait_for_load: bool = True) -> Dict[str, Any]:
        """
        Navigate to a URL and handle challenges
        
        Args:
            url: URL to navigate to
            wait_for_load: Wait for page to fully load
            
        Returns:
            Dict with page information
        """
        if not self.driver:
            self.start()
            
        self.logger.info(f"Navigating to: {url}")
        self.driver.get(url)
        self.current_url = url
        
        # Handle challenges
        if self._detect_challenge():
            self.logger.info("Cloudflare challenge detected, waiting for resolution...")
            self._wait_for_challenge_completion()
        
        # Wait for page load if requested
        if wait_for_load:
            time.sleep(2)
            
        # Update requests session with new cookies
        self._update_requests_session()
        
        result = {
            'url': self.driver.current_url,
            'title': self.driver.title,
            'status': 'success',
            'cookies': len(self.driver.get_cookies())
        }
        
        self.logger.info(f"✓ Successfully accessed: {result['url']}")
        return result
        
    def get_html(self, url: str = None, wait_for_load = True) -> str:
        """
        Get HTML content from current page or navigate to URL
        
        Args:
            url: Optional URL to navigate to first
            
        Returns:
            HTML content as string
        """
        if url:
            self.goto(url, wait_for_load=wait_for_load)
        
        if not self.driver:
            raise Exception("No active browser session")
            
        return self.driver.page_source
        
    def get_soup(self, url: str = None) -> BeautifulSoup:
        """
        Get BeautifulSoup object for current page or navigate to URL
        
        Args:
            url: Optional URL to navigate to first
            
        Returns:
            BeautifulSoup object
        """
        html = self.get_html(url)
        return BeautifulSoup(html, 'html.parser')
        
    def find_element(self, selector: str, by: str = "css") -> Any:
        """
        Find a single element by CSS selector or XPath
        
        Args:
            selector: CSS selector or XPath
            by: 'css' or 'xpath'
            
        Returns:
            WebElement or None
        """
        if not self.driver:
            raise Exception("No active browser session")
            
        try:
            if by.lower() == "css":
                return self.driver.find_element(By.CSS_SELECTOR, selector)
            elif by.lower() == "xpath":
                return self.driver.find_element(By.XPATH, selector)
            else:
                raise ValueError("by must be 'css' or 'xpath'")
        except NoSuchElementException:
            return None
            
    def find_elements(self, selector: str, by: str = "css") -> List[Any]:
        """
        Find multiple elements by CSS selector or XPath
        
        Args:
            selector: CSS selector or XPath
            by: 'css' or 'xpath'
            
        Returns:
            List of WebElements
        """
        if not self.driver:
            raise Exception("No active browser session")
            
        if by.lower() == "css":
            return self.driver.find_elements(By.CSS_SELECTOR, selector)
        elif by.lower() == "xpath":
            return self.driver.find_elements(By.XPATH, selector)
        else:
            raise ValueError("by must be 'css' or 'xpath'")
            
    def click(self, selector: str, by: str = "css", wait: bool = True) -> bool:
        """
        Click on an element
        
        Args:
            selector: CSS selector or XPath
            by: 'css' or 'xpath'
            wait: Wait for element to be clickable
            
        Returns:
            True if clicked successfully
        """
        try:
            if wait:
                if by.lower() == "css":
                    element = WebDriverWait(self.driver, self.timeout).until(
                        element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                else:
                    element = WebDriverWait(self.driver, self.timeout).until(
                        element_to_be_clickable((By.XPATH, selector))
                    )
            else:
                element = self.find_element(selector, by)
                
            if element:
                # Scroll to element
                self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
                time.sleep(0.5)
                
                # Try regular click first
                try:
                    element.click()
                except Exception:
                    # If regular click fails, try JavaScript click
                    self.driver.execute_script("arguments[0].click();", element)
                
                self.logger.info(f"✓ Clicked element: {selector}")
                return True
            else:
                self.logger.warning(f"Element not found: {selector}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error clicking element {selector}: {e}")
            return False
            
    def type_text(self, selector: str, text: str, by: str = "css", clear: bool = True) -> bool:
        """
        Type text into an input field
        
        Args:
            selector: CSS selector or XPath
            text: Text to type
            by: 'css' or 'xpath'
            clear: Clear field before typing
            
        Returns:
            True if successful
        """
        try:
            element = self.find_element(selector, by)
            if element:
                if clear:
                    element.clear()
                element.send_keys(text)
                self.logger.info(f"✓ Typed text into: {selector}")
                return True
            else:
                self.logger.warning(f"Element not found: {selector}")
                return False
        except Exception as e:
            self.logger.error(f"Error typing text into {selector}: {e}")
            return False
            
    def wait_for_element(self, selector: str, by: str = "css", timeout: int = None) -> Any:
        """
        Wait for an element to appear
        
        Args:
            selector: CSS selector or XPath
            by: 'css' or 'xpath'
            timeout: Timeout in seconds
            
        Returns:
            WebElement or None
        """
        timeout = timeout or self.timeout
        try:
            if by.lower() == "css":
                element = WebDriverWait(self.driver, timeout).until(
                    presence_of_element_located((By.CSS_SELECTOR, selector))
                )
            else:
                element = WebDriverWait(self.driver, timeout).until(
                    presence_of_element_located((By.XPATH, selector))
                )
            return element
        except TimeoutException:
            return None
            
    def wait_for_element_attribute(self, selector: str, attribute: str, expected_value: str = None, 
                                   by: str = "css", timeout: int = None, wait_for_change: bool = False) -> bool:
        """
        Wait for an element's attribute to have a specific value or to change
        
        Args:
            selector: CSS selector or XPath
            attribute: Attribute name (e.g., 'hidden', 'class', 'style')
            expected_value: Expected attribute value (None means attribute should exist)
            by: 'css' or 'xpath'
            timeout: Timeout in seconds
            wait_for_change: If True, wait for attribute to change from current value
            
        Returns:
            True if condition met, False if timeout
        
        Examples:
            # Wait for element to become hidden
            scraper.wait_for_element_attribute('.loading', 'hidden')
            
            # Wait for element to have specific class
            scraper.wait_for_element_attribute('#status', 'class', 'completed')
            
            # Wait for style attribute to change
            scraper.wait_for_element_attribute('.modal', 'style', wait_for_change=True)
        """
        timeout = timeout or self.timeout
        self.logger.debug(f"Waiting for element '{selector}' attribute '{attribute}' = '{expected_value}'")
        
        try:
            element = self.find_element(selector, by)
            if not element:
                self.logger.warning(f"Element '{selector}' not found")
                return False
            
            # Get initial value if waiting for change
            initial_value = None
            if wait_for_change:
                initial_value = element.get_attribute(attribute)
                self.logger.debug(f"Initial attribute value: '{initial_value}'")
            
            def check_attribute():
                current_element = self.find_element(selector, by)
                if not current_element:
                    return False
                    
                current_value = current_element.get_attribute(attribute)
                
                if wait_for_change:
                    return current_value != initial_value
                elif expected_value is None:
                    # Just check if attribute exists (not None)
                    return current_value is not None
                else:
                    # Check for specific value
                    if attribute == 'class':
                        # For class attribute, check if expected_value is in the class list
                        return expected_value in (current_value or '').split()
                    else:
                        return current_value == expected_value
            
            # Wait for condition
            start_time = time.time()
            while time.time() - start_time < timeout:
                if check_attribute():
                    self.logger.debug(f"Attribute condition met for '{selector}'")
                    return True
                time.sleep(0.5)
            
            self.logger.warning(f"Timeout waiting for attribute condition on '{selector}'")
            return False
            
        except Exception as e:
            self.logger.error(f"Error waiting for element attribute: {e}")
            return False
    
    def wait_for_captcha(self, timeout: int = 60, auto_solve: bool = True) -> Dict[str, Any]:
        """
        Wait for and optionally attempt to solve CAPTCHAs
        
        Args:
            timeout: Maximum time to wait for CAPTCHA completion
            auto_solve: Attempt to automatically solve simple CAPTCHAs
            
        Returns:
            Dict with CAPTCHA status and type information
        
        Examples:
            # Wait for any CAPTCHA to be solved (manually or automatically)
            result = scraper.wait_for_captcha(timeout=60)
            
            # Just detect CAPTCHA without trying to solve
            result = scraper.wait_for_captcha(auto_solve=False)
        """
        self.logger.info("Checking for CAPTCHAs...")
        
        result = {
            'captcha_detected': False,
            'captcha_type': None,
            'solved': False,
            'time_taken': 0
        }
        
        start_time = time.time()
        
        try:
            # Check for different types of CAPTCHAs
            captcha_info = self._detect_captcha_type()
            
            if not captcha_info['detected']:
                self.logger.debug("No CAPTCHA detected")
                return result
            
            result['captcha_detected'] = True
            result['captcha_type'] = captcha_info['type']
            
            self.logger.info(f"CAPTCHA detected: {captcha_info['type']}")
            
            if auto_solve:
                self.logger.info("Attempting to solve CAPTCHA...")
                solved = self._attempt_captcha_solve(captcha_info, timeout)
                result['solved'] = solved
                
                if solved:
                    self.logger.info("CAPTCHA solved successfully!")
                else:
                    self.logger.warning("CAPTCHA could not be solved automatically")
            else:
                # Wait for manual solving
                self.logger.info("Waiting for manual CAPTCHA solving...")
                solved = self._wait_for_captcha_completion(captcha_info, timeout)
                result['solved'] = solved
            
            result['time_taken'] = time.time() - start_time
            return result
            
        except Exception as e:
            self.logger.error(f"Error handling CAPTCHA: {e}")
            result['time_taken'] = time.time() - start_time
            return result
    
    def _detect_captcha_type(self) -> Dict[str, Any]:
        """
        Detect what type of CAPTCHA is present on the page
        """
        if not self.driver:
            return {'detected': False, 'type': None, 'elements': []}
        
        captcha_types = {
            'recaptcha_v2': {
                'selectors': ['.g-recaptcha', 'iframe[src*="recaptcha"]', '.recaptcha-checkbox'],
                'iframe_src': 'recaptcha'
            },
            'hcaptcha': {
                'selectors': ['.h-captcha', 'iframe[src*="hcaptcha"]'],
                'iframe_src': 'hcaptcha'
            },
            'turnstile': {
                'selectors': ['.cf-turnstile', '[data-cf-turnstile-sitekey]'],
                'iframe_src': 'turnstile'
            },
            'generic': {
                'selectors': ['[data-sitekey]', '.captcha', '#captcha'],
                'iframe_src': 'captcha'
            }
        }
        
        for captcha_type, config in captcha_types.items():
            elements = []
            for selector in config['selectors']:
                found = self.find_elements(selector)
                if found:
                    elements.extend(found)
            
            if elements:
                self.logger.debug(f"Detected {captcha_type} CAPTCHA")
                return {
                    'detected': True,
                    'type': captcha_type,
                    'elements': elements,
                    'config': config
                }
        
        return {'detected': False, 'type': None, 'elements': []}
    
    def _attempt_captcha_solve(self, captcha_info: Dict, timeout: int) -> bool:
        """
        Attempt to automatically solve CAPTCHA
        """
        captcha_type = captcha_info['type']
        
        try:
            if captcha_type == 'recaptcha_v2':
                return self._solve_recaptcha_v2(captcha_info, timeout)
            elif captcha_type == 'hcaptcha':
                return self._solve_hcaptcha(captcha_info, timeout)
            elif captcha_type == 'turnstile':
                return self._solve_turnstile(captcha_info, timeout)
            else:
                self.logger.warning(f"No automatic solver for {captcha_type}")
                return self._wait_for_captcha_completion(captcha_info, timeout)
                
        except Exception as e:
            self.logger.error(f"Error solving {captcha_type}: {e}")
            return False
    
    def _solve_recaptcha_v2(self, captcha_info: Dict, timeout: int) -> bool:
        """
        Attempt to solve reCAPTCHA v2 (mainly clicking the checkbox)
        """
        self.logger.debug("Attempting to solve reCAPTCHA v2...")
        
        try:
            # Look for the checkbox iframe
            checkbox_iframe = self.find_element('iframe[src*="recaptcha"][src*="anchor"]')
            if checkbox_iframe:
                self.logger.debug("Found reCAPTCHA checkbox iframe")
                
                # Switch to iframe and click checkbox
                self.driver.switch_to.frame(checkbox_iframe)
                
                checkbox = self.find_element('.recaptcha-checkbox-border')
                if checkbox and checkbox.is_enabled():
                    self.logger.debug("Clicking reCAPTCHA checkbox")
                    checkbox.click()
                    time.sleep(2)
                
                # Switch back to main content
                self.driver.switch_to.default_content()
                
                # Wait for completion or challenge
                return self._wait_for_captcha_completion(captcha_info, timeout)
            
        except Exception as e:
            self.logger.error(f"Error solving reCAPTCHA v2: {e}")
            try:
                self.driver.switch_to.default_content()
            except:
                pass
        
        return False
    
    def _solve_hcaptcha(self, captcha_info: Dict, timeout: int) -> bool:
        """
        Attempt to solve hCaptcha (mainly clicking the checkbox)
        """
        self.logger.debug("Attempting to solve hCaptcha...")
        
        try:
            # Look for hCaptcha checkbox
            checkbox = self.find_element('.hcaptcha-checkbox')
            if checkbox and checkbox.is_enabled():
                self.logger.debug("Clicking hCaptcha checkbox")
                checkbox.click()
                time.sleep(2)
                
                return self._wait_for_captcha_completion(captcha_info, timeout)
            
        except Exception as e:
            self.logger.error(f"Error solving hCaptcha: {e}")
        
        return False
    
    def _solve_turnstile(self, captcha_info: Dict, timeout: int) -> bool:
        """
        Attempt to solve Cloudflare Turnstile (usually automatic)
        """
        self.logger.debug("Waiting for Turnstile to complete...")
        
        # Turnstile usually solves automatically, just wait
        return self._wait_for_captcha_completion(captcha_info, timeout)
    
    def _wait_for_captcha_completion(self, captcha_info: Dict, timeout: int) -> bool:
        """
        Wait for CAPTCHA to be completed (either automatically or manually)
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if CAPTCHA elements are still visible/active
            current_captcha = self._detect_captcha_type()
            
            if not current_captcha['detected']:
                self.logger.debug("CAPTCHA no longer detected - assuming solved")
                return True
            
            # For reCAPTCHA, check for success indicators
            if captcha_info['type'] == 'recaptcha_v2':
                success_elements = self.find_elements('.recaptcha-checkbox-checked')
                if success_elements:
                    self.logger.debug("reCAPTCHA checkbox checked")
                    return True
            
            # Check if page has changed significantly (might indicate success)
            try:
                current_url = self.driver.current_url
                if hasattr(self, 'captcha_start_url') and current_url != self.captcha_start_url:
                    self.logger.debug("Page URL changed - CAPTCHA likely solved")
                    return True
            except:
                pass
            
            time.sleep(1)
        
        self.logger.warning(f"Timeout waiting for CAPTCHA completion after {timeout} seconds")
        return False
            
    def download_file(self, url: str, filename: str = None, use_browser: bool = True) -> Optional[str]:
        """
        Download a file using either browser session or requests
        
        Args:
            url: URL of file to download
            filename: Optional filename (auto-detected if None)
            use_browser: Use browser session (recommended for protected files)
            
        Returns:
            Path to downloaded file or None if failed
        """
        try:
            # Resolve relative URLs
            if self.current_url and not url.startswith(('http://', 'https://')):
                url = urljoin(self.current_url, url)
                
            self.logger.info(f"Downloading file: {url}")
            
            if use_browser and self.driver:
                # Update session first
                self._update_requests_session()
                
                # Set appropriate headers for file download
                headers = {
                    'Accept': '*/*',
                    'Referer': self.current_url or self.driver.current_url
                }
                
                # Detect file type and set appropriate accept header
                if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    headers['Accept'] = 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
                elif any(ext in url.lower() for ext in ['.css']):
                    headers['Accept'] = 'text/css,*/*;q=0.1'
                elif any(ext in url.lower() for ext in ['.js']):
                    headers['Accept'] = '*/*'
                
                response = self.session.get(url, stream=True, headers=headers)
            else:
                # Use basic requests without browser session
                response = requests.get(url, stream=True)
                
            response.raise_for_status()
            
            # Determine filename
            if not filename:
                # Try to get filename from Content-Disposition header
                cd_header = response.headers.get('content-disposition', '')
                if 'filename=' in cd_header:
                    filename = cd_header.split('filename=')[1].strip('"\'')
                else:
                    # Extract from URL
                    filename = os.path.basename(urlparse(url).path)
                    if not filename or '.' not in filename:
                        # Generate filename based on content type
                        content_type = response.headers.get('content-type', '')
                        if 'image' in content_type:
                            ext = content_type.split('/')[-1]
                            filename = f"image_{int(time.time())}.{ext}"
                        else:
                            filename = f"file_{int(time.time())}"
            
            # Ensure filename is safe
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            filepath = self.download_dir / filename
            
            # Download file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            file_size = filepath.stat().st_size
            self.logger.info(f"✓ File downloaded successfully!")
            self.logger.info(f"  Path: {filepath}")
            self.logger.info(f"  Size: {file_size / 1024:.1f} KB")
            self.logger.info(f"  Content-Type: {response.headers.get('content-type', 'Unknown')}")
            
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Error downloading file {url}: {e}")
            return None
            
    def download_all_images(self, selector: str = "img", attribute: str = "src") -> List[str]:
        """
        Download all images from the current page
        
        Args:
            selector: CSS selector for image elements
            attribute: Attribute containing image URL
            
        Returns:
            List of downloaded file paths
        """
        if not self.driver:
            raise Exception("No active browser session")
            
        images = self.find_elements(selector)
        downloaded = []
        
        for img in images:
            try:
                img_url = img.get_attribute(attribute)
                if img_url:
                    filepath = self.download_file(img_url)
                    if filepath:
                        downloaded.append(filepath)
            except Exception as e:
                self.logger.warning(f"Failed to download image: {e}")
                continue
                
        self.logger.info(f"Downloaded {len(downloaded)} images")
        return downloaded
        
    def screenshot(self, filename: str = None) -> str:
        """
        Take a screenshot of the current page
        
        Args:
            filename: Optional filename
            
        Returns:
            Path to screenshot file
        """
        if not self.driver:
            raise Exception("No active browser session")
            
        if not filename:
            filename = f"screenshot_{int(time.time())}.png"
            
        filepath = self.download_dir / filename
        self.driver.save_screenshot(str(filepath))
        
        self.logger.info(f"Screenshot saved: {filepath}")
        return str(filepath)
        
    def scroll_to_bottom(self, pause_time: float = 1.0) -> None:
        """
        Scroll to bottom of page with pauses to load content
        
        Args:
            pause_time: Time to pause between scrolls
        """
        if not self.driver:
            raise Exception("No active browser session")
            
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new content to load
            time.sleep(pause_time)
            
            # Calculate new scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        self.logger.info("Scrolled to bottom of page")
        
    def execute_script(self, script: str, *args) -> Any:
        """
        Execute JavaScript in the browser
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the script
            
        Returns:
            Result of script execution
        """
        if not self.driver:
            raise Exception("No active browser session")
            
        return self.driver.execute_script(script, *args)
        
    def get_cookies(self) -> List[Dict]:
        """Get all cookies from the browser"""
        if not self.driver:
            return []
        return self.driver.get_cookies()
        
    def add_cookie(self, cookie_dict: Dict) -> None:
        """Add a cookie to the browser"""
        if self.driver:
            self.driver.add_cookie(cookie_dict)
            self._update_requests_session()


# Example usage and test function
def test_universal_scraper():
    """Test the Universal Scraper with various operations"""
    print("=== Testing Universal Scraper ===")
    
    with UniversalScraper(headless=True, download_dir=".") as scraper:
        # Test 1: Navigate to page
        print("\nTest 1: Navigating to SteamRip...")
        result = scraper.goto("https://steamrip.com/")
        print(f"✓ Navigation result: {result}")
        
        # Test 2: Get page title and HTML snippet
        print("\nTest 2: Extracting HTML...")
        soup = scraper.get_soup()
        print(f"✓ Page title: {soup.title.text if soup.title else 'No title'}")
        print(f"✓ HTML length: {len(str(soup))} characters")
        
        # Test 3: Download a specific image
        print("\nTest 3: Downloading specific image...")
        image_url = "https://steamrip.com/wp-content/uploads/2025/01/ratten-reich-preinstalled-steamrip.jpg"
        filepath = scraper.download_file(image_url)
        if filepath:
            print(f"✓ Downloaded: {filepath}")
        
        # Test 4: Find and click elements (example)
        print("\nTest 4: Finding elements...")
        images = scraper.find_elements("img")
        print(f"✓ Found {len(images)} images on page")
        
        # Test 5: Take screenshot
        print("\nTest 5: Taking screenshot...")
        screenshot_path = scraper.screenshot("steamrip_screenshot.png")
        print(f"✓ Screenshot saved: {screenshot_path}")

if __name__ == "__main__":
    test_universal_scraper()