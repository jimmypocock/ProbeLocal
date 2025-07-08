"""Selenium base class for Streamlit UI testing"""
import time
import subprocess
import requests
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import os


class SeleniumStreamlitTest:
    """Base class for Selenium-based Streamlit tests"""
    
    def __init__(self):
        self.driver = None
        self.wait = None
        self.app_url = "http://localhost:2402"
        self.api_url = "http://localhost:8080"
        self.api_process = None
        self.app_process = None
        
    def setup_driver(self, headless=True):
        """Setup Chrome driver with options"""
        options = Options()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        
        # Use webdriver_manager to handle driver installation
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def start_services(self):
        """Start API and Streamlit services if not running"""
        # Check if API is running
        try:
            response = requests.get(f"{self.api_url}/health", timeout=1)
            if response.status_code == 200:
                print("✓ API already running on port 8080")
        except:
            print("Starting API server...")
            self.api_process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            # Wait for API to start
            for _ in range(30):
                try:
                    if requests.get(f"{self.api_url}/health", timeout=1).status_code == 200:
                        break
                except:
                    time.sleep(1)
                    
        # Check if Streamlit is running
        try:
            response = requests.get(self.app_url, timeout=1)
            if response.status_code == 200:
                print("✓ Streamlit already running on port 2402")
        except:
            print("Starting Streamlit app...")
            self.app_process = subprocess.Popen(
                ["streamlit", "run", "app.py", "--server.port", "2402", "--server.headless", "true"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            time.sleep(5)
            
    def stop_services(self):
        """Stop services if we started them"""
        if self.api_process:
            self.api_process.terminate()
            self.api_process.wait()
        if self.app_process:
            self.app_process.terminate()
            self.app_process.wait()
            
    def teardown(self):
        """Clean up driver and services"""
        if self.driver:
            self.driver.quit()
        self.stop_services()
        
    def wait_for_streamlit(self):
        """Wait for Streamlit app to load"""
        self.driver.get(self.app_url)
        # Wait for main app container
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stApp"]')))
        # Wait for header
        self.wait.until(EC.presence_of_element_located((By.XPATH, "//h1[contains(text(), 'Greg')]")))
        time.sleep(2)  # Let Streamlit finish rendering
        
    def upload_file(self, file_path: str):
        """Upload a file using Selenium"""
        # Find the file input - even if hidden
        file_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        
        # Sometimes there are multiple file inputs, use the visible one or the first one
        file_input = None
        for inp in file_inputs:
            if inp.is_displayed() or inp.is_enabled():
                file_input = inp
                break
        
        if not file_input and file_inputs:
            file_input = file_inputs[0]
            
        if not file_input:
            raise Exception("No file input found")
        
        # Make it visible temporarily if needed
        self.driver.execute_script("arguments[0].style.display = 'block';", file_input)
        self.driver.execute_script("arguments[0].style.opacity = '1';", file_input)
        
        # Send the file path
        file_input.send_keys(os.path.abspath(file_path))
        
        print(f"✓ File selected: {file_path}")
        time.sleep(2)  # Give Streamlit time to register the file
        
    def click_button(self, button_text: str):
        """Click a button by its text"""
        # Take screenshot for debugging
        self.take_screenshot(f"before_click_{button_text.replace(' ', '_')}")
        
        try:
            button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{button_text}')]"))
            )
            button.click()
            time.sleep(1)  # Wait for Streamlit to process
        except Exception as e:
            # Try alternative selectors
            try:
                # Try with partial text
                button = self.driver.find_element(By.XPATH, f"//button[contains(., '{button_text}')]") 
                button.click()
                time.sleep(1)
            except:
                # Take screenshot and re-raise original error
                self.take_screenshot(f"failed_click_{button_text.replace(' ', '_')}")
                raise e
        
    def get_notification(self):
        """Get notification text if present"""
        try:
            alerts = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="stAlert"]')
            for alert in alerts:
                if alert.is_displayed():
                    return alert.text
        except:
            pass
        return None
        
    def select_document(self, doc_name: str) -> bool:
        """Select a document from the sidebar"""
        try:
            # Find document button - they might not be in the sidebar
            doc_button = None
            
            # Try different selectors
            selectors = [
                f"//button[text()='{doc_name}']",  # Exact match anywhere
                f"//button[contains(text(), '{doc_name}')]",  # Contains anywhere
                f"//div[@data-testid='stSidebar']//button[text()='{doc_name}']",  # In sidebar exact
                f"//div[@data-testid='stSidebar']//button[contains(text(), '{doc_name}')]",  # In sidebar contains
            ]
            
            for selector in selectors:
                try:
                    doc_button = self.driver.find_element(By.XPATH, selector)
                    if doc_button and doc_button.is_displayed():
                        break
                except:
                    continue
            
            if doc_button:
                doc_button.click()
                time.sleep(2)
                
                # Check if chat input appears
                chat_inputs = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="stChatInput"]')
                return len(chat_inputs) > 0
            return False
        except Exception as e:
            print(f"Error selecting document: {e}")
            return False
            
    def send_chat_message(self, message: str):
        """Send a message in the chat"""
        # Find chat input
        chat_input = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="stChatInput"] textarea'))
        )
        chat_input.send_keys(message)
        chat_input.submit()  # Press Enter
        
    def get_chat_messages(self):
        """Get all chat messages"""
        messages = []
        msg_elements = self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="stChatMessage"]')
        for msg in msg_elements:
            messages.append(msg.text)
        return messages
        
    def take_screenshot(self, name: str):
        """Take a screenshot for debugging"""
        screenshots_dir = Path("tests/ui/screenshots")
        screenshots_dir.mkdir(exist_ok=True)
        self.driver.save_screenshot(str(screenshots_dir / f"{name}.png"))
        
    def enable_web_search(self):
        """Enable web search mode"""
        # Find and click web search checkbox
        checkboxes = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
        for checkbox in checkboxes:
            try:
                parent = checkbox.find_element(By.XPATH, '../..')
                parent_text = parent.text
                if "🌐" in parent_text or "search web" in parent_text.lower():
                    if not checkbox.is_selected():
                        # Try clicking the label or the checkbox itself
                        try:
                            label = parent.find_element(By.TAG_NAME, 'label')
                            label.click()
                        except:
                            checkbox.click()
                        time.sleep(2)
                    return True
            except:
                continue
        return False
        
    def get_document_list(self):
        """Get list of documents"""
        documents = []
        # Look for all buttons on the page
        all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
        
        # Filter to find document buttons (they have .txt, .pdf, etc. extensions)
        for button in all_buttons:
            text = button.text.strip()
            # Check if it looks like a document (has file extension)
            if text and any(ext in text.lower() for ext in ['.txt', '.pdf', '.csv', '.md', '.docx', '.xlsx', '.png', '.jpg']):
                # Skip delete buttons and empty buttons
                if text and '🗑️' not in text and 'delete' not in text.lower():
                    documents.append(text)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_docs = []
        for doc in documents:
            if doc not in seen:
                seen.add(doc)
                unique_docs.append(doc)
        
        return unique_docs