#!/usr/bin/env python

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import time
import logging
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='match_fetcher.log'
)
logger = logging.getLogger(__name__)

def setup_driver():
    """Setup and return configured Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3')
    
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise

def get_match_ids(date_str):
    """
    Fetch match IDs from Flashscore for a specific date
    date_str: date in format YYYYMMDD
    """
    driver = setup_driver()
    match_ids = []
    
    try:
        # Go to Flashscore and set the date
        url = f"https://www.flashscore.com/football/?d={date_str}"
        logger.info(f"Fetching matches for date: {date_str}")
        driver.get(url)
        time.sleep(2)

        # Accept GDPR if present
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
        except (TimeoutException, NoSuchElementException):
            pass

        # Wait for matches to load
        time.sleep(2)

        # Find all match elements
        matches = driver.find_elements(By.CLASS_NAME, "event__match")
        
        # Extract match IDs
        for match in matches:
            try:
                match_id = match.get_attribute("id").split("_")[2]
                match_ids.append(match_id)
                logger.info(f"Found match ID: {match_id}")
            except Exception as e:
                logger.error(f"Error extracting match ID: {e}")
                continue

        logger.info(f"Found {len(match_ids)} matches for date {date_str}")
        
        # Save match IDs to file
        output_file = "match_ids_input.txt"
        with open(output_file, "w") as f:
            for match_id in match_ids:
                f.write(f"{match_id}\n")
        
        logger.info(f"Saved match IDs to {output_file}")
        
        return match_ids

    except Exception as e:
        logger.error(f"Error fetching match IDs: {e}")
        return []
    
    finally:
        driver.quit()

def main():
    # Get yesterday's date in YYYYMMDD format
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    
    try:
        match_ids = get_match_ids(yesterday)
        print(f"Found {len(match_ids)} matches for {yesterday}")
    except Exception as e:
        logger.error(f"Script failed: {e}")

if __name__ == "__main__":
    main()