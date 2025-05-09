#!/usr/bin/env python

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging
import os

# Set up logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('xpath_finder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class XPathFinder:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        """Setup Chrome WebDriver without headless mode for visual inspection"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Use existing ChromeDriver
            chromedriver_path = os.path.join(os.getcwd(), 'drivers', 'chromedriver.exe')
            logger.info(f"Using ChromeDriver from: {chromedriver_path}")
            
            if not os.path.exists(chromedriver_path):
                raise Exception(f"ChromeDriver not found at {chromedriver_path}")
                
            service = ChromeService(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
        
    def handle_consent(self):
        """Handle GDPR consent popup"""
        try:
            consent_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            self.driver.execute_script("arguments[0].click();", consent_button)
            time.sleep(2)
            logger.info("Handled GDPR consent popup")
        except (TimeoutException, NoSuchElementException):
            logger.info("No consent popup found or already accepted")
            pass

    def inspect_page(self, url="https://www.flashscore.com/football/"):
        """Open page and wait for manual inspection"""
        try:
            logger.info(f"Opening {url}")
            self.driver.get(url)
            time.sleep(3)
            
            # Handle consent
            self.handle_consent()
            
            # Try to identify key elements
            try:
                # Look for tournament sections
                tournaments = self.driver.find_elements(By.CLASS_NAME, "sportName")
                logger.info(f"Found {len(tournaments)} tournament sections")
                
                # Look for matches
                matches = self.driver.find_elements(By.CLASS_NAME, "event__match")
                logger.info(f"Found {len(matches)} matches")
                
                # Print sample XPaths if elements are found
                if tournaments:
                    logger.info(f"Sample tournament XPath: {self.driver.execute_script('return getXPath(arguments[0])', tournaments[0])}")
                if matches:
                    logger.info(f"Sample match XPath: {self.driver.execute_script('return getXPath(arguments[0])', matches[0])}")
                    
            except Exception as e:
                logger.error(f"Error identifying elements: {e}")
            
            logger.info("\n" + "="*50)
            logger.info("Page is ready for inspection.")
            logger.info("Browser will stay open for inspection.")
            logger.info("Press Ctrl+C in the terminal to close the browser")
            logger.info("="*50 + "\n")
            
            # Add JavaScript function to help get XPath
            self.driver.execute_script("""
                function getXPath(element) {
                    if (element.id !== '')
                        return 'id("' + element.id + '")';
                    if (element === document.body)
                        return element.tagName;

                    var ix = 0;
                    var siblings = element.parentNode.childNodes;
                    for (var i = 0; i < siblings.length; i++) {
                        var sibling = siblings[i];
                        if (sibling === element)
                            return getXPath(element.parentNode) + '/' + element.tagName + '[' + (ix + 1) + ']';
                        if (sibling.nodeType === 1 && sibling.tagName === element.tagName)
                            ix++;
                    }
                }
            """)
            
            # Keep browser open for inspection
            while True:
                time.sleep(1)
            
        except KeyboardInterrupt:
            logger.info("Inspection terminated by user")
        except Exception as e:
            logger.error(f"Error during inspection: {e}")
        finally:
            self.driver.quit()

def main():
    finder = XPathFinder()
    finder.inspect_page()

if __name__ == "__main__":
    main()