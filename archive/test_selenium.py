from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('selenium_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_selenium():
    logger.info("Starting Selenium test...")
    driver = None
    
    try:
        # Basic Chrome setup
        chromedriver_path = os.path.join(os.getcwd(), 'drivers', 'chromedriver.exe')
        logger.info(f"ChromeDriver path: {chromedriver_path}")
        logger.info(f"ChromeDriver exists: {os.path.exists(chromedriver_path)}")
        
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        service = ChromeService(executable_path=chromedriver_path)
        logger.info("Creating Chrome WebDriver...")
        driver = webdriver.Chrome(service=service, options=options)
        
        logger.info("Chrome started successfully!")
        logger.info("Opening Google...")
        driver.get("https://www.google.com")
        
        logger.info(f"Page title: {driver.title}")
        return True
        
    except WebDriverException as e:
        logger.error(f"WebDriver error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False
    finally:
        if driver:
            driver.quit()
            logger.info("Chrome browser closed")

if __name__ == "__main__":
    success = test_selenium()
    if success:
        logger.info("Selenium test completed successfully!")
    else:
        logger.error("Selenium test failed!")
        sys.exit(1)