#!/usr/bin/env python

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='flashscore_analysis.log'
)
logger = logging.getLogger(__name__)

class FlashscoreAnalyzer:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        """Setup Chrome WebDriver with optimal settings"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')  # Updated headless mode
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36')
        
        self.driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options
        )
        self.driver.implicitly_wait(20)
        self.wait = WebDriverWait(self.driver, 20)
        
    def wait_for_element(self, by, value, timeout=10):
        """Wait for an element to be present and visible"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            logger.error(f"Timeout waiting for element: {value}")
            return None

    def handle_consent(self):
        """Handle GDPR consent popup"""
        try:
            consent_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            self.driver.execute_script("arguments[0].click();", consent_button)
            time.sleep(2)
        except (TimeoutException, NoSuchElementException):
            logger.info("No consent popup found or already accepted")
            
    def analyze_main_page(self):
        """Analyze the main football page structure"""
        try:
            url = "https://www.flashscore.com/football/"
            logger.info(f"Accessing {url}")
            self.driver.get(url)
            time.sleep(5)  # Allow page to load fully
            
            # Handle consent if needed
            self.handle_consent()
            
            # Wait for the content to load
            main_content = self.wait_for_element(By.CLASS_NAME, "sportName")
            if not main_content:
                logger.error("Main content not found")
                return
                
            print("Analyzing page structure...")
            
            # Try different selectors for tournaments
            selectors = [
                "//div[contains(@class, 'tournament')]",
                "//div[contains(@class, 'leagues--static')]",
                "//div[contains(@class, 'sportName')]"
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} elements with selector: {selector}")
                        print(f"Found {len(elements)} elements")
                        
                        # Print the first few elements to analyze structure
                        for element in elements[:5]:
                            try:
                                print("\nElement HTML:")
                                print(element.get_attribute('outerHTML'))
                                print("\nElement Text:")
                                print(element.text)
                                print("-" * 50)
                            except StaleElementReferenceException:
                                continue
                            
                except Exception as e:
                    logger.error(f"Error with selector {selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error analyzing main page: {e}")
        finally:
            self.driver.quit()

def main():
    analyzer = FlashscoreAnalyzer()
    analyzer.analyze_main_page()

if __name__ == "__main__":
    main()