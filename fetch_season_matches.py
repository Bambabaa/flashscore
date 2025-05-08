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
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='season_scraper.log'
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

def get_league_matches(driver, league_url, start_date, end_date):
    """
    Fetch match IDs for a specific league within a date range
    """
    match_ids = []
    current_date = start_date
    
    while current_date <= end_date:
        try:
            date_str = current_date.strftime("%Y%m%d")
            url = f"{league_url}/results/?d={date_str}"
            logger.info(f"Fetching matches for {league_url} on date: {date_str}")
            
            driver.get(url)
            time.sleep(2)

            # Accept GDPR if present
            try:
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
                ).click()
            except (TimeoutException, NoSuchElementException):
                pass

            # Find all match elements
            matches = driver.find_elements(By.CLASS_NAME, "event__match")
            
            # Extract match IDs
            for match in matches:
                try:
                    match_id = match.get_attribute("id").split("_")[2]
                    match_ids.append({
                        "id": match_id,
                        "date": current_date.strftime("%Y-%m-%d"),
                        "league": league_url.split("/")[-1]
                    })
                    logger.info(f"Found match ID: {match_id}")
                except Exception as e:
                    logger.error(f"Error extracting match ID: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error fetching matches for date {current_date}: {e}")
        
        current_date += timedelta(days=1)
    
    return match_ids

def save_matches(matches, output_dir="data/leagues"):
    """Save matches to JSON files organized by league"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Group matches by league
        leagues = {}
        for match in matches:
            league = match["league"]
            if league not in leagues:
                leagues[league] = []
            leagues[league].append(match)
        
        # Save each league's matches to a separate file
        for league, league_matches in leagues.items():
            output_file = os.path.join(output_dir, f"{league}.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(league_matches, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(league_matches)} matches for {league} to {output_file}")
            
    except Exception as e:
        logger.error(f"Error saving matches: {e}")

def main():
    # List of leagues to scrape
    leagues = [
        "https://www.flashscore.com/football/england/premier-league",
        "https://www.flashscore.com/football/spain/laliga",
        "https://www.flashscore.com/football/italy/serie-a",
        "https://www.flashscore.com/football/germany/bundesliga",
        "https://www.flashscore.com/football/france/ligue-1",
        # Add more leagues as needed
    ]
    
    try:
        # Get date range from user
        start_date = input("Enter start date (YYYY-MM-DD): ")
        end_date = input("Enter end date (YYYY-MM-DD): ")
        
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        driver = setup_driver()
        all_matches = []
        
        try:
            # Fetch matches for each league
            for league_url in leagues:
                logger.info(f"Processing league: {league_url}")
                matches = get_league_matches(driver, league_url, start_date, end_date)
                all_matches.extend(matches)
                
                # Add a delay between leagues to avoid rate limiting
                time.sleep(2)
            
            # Save all matches
            save_matches(all_matches)
            logger.info(f"Successfully processed {len(all_matches)} matches across {len(leagues)} leagues")
            
        finally:
            driver.quit()
            
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Script failed: {e}")

if __name__ == "__main__":
    main()