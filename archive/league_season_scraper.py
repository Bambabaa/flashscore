#!/usr/bin/env python

import logging
import json
import os
import random
import time
from datetime import datetime
from typing import List, Dict, Any

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='season_scraper.log'
)
logger = logging.getLogger(__name__)

# Constants
WAIT_TIME = 20
RETRY_ATTEMPTS = 3
DELAY_BETWEEN_REQUESTS = (1, 3)  # Random delay range in seconds

class LeagueSeasonScraper:
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        """Initialize Chrome WebDriver with optimal settings"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--ignore-certificate-errors')  # Handle SSL errors
        options.add_argument('--ignore-ssl-errors')         # Handle SSL errors
        options.add_argument('--disable-web-security')      # Handle SSL errors
        options.add_argument('--allow-running-insecure-content')  # Handle SSL errors
        options.add_argument('--disable-features=WebGL')    # Disable WebGL
        options.add_argument('--disable-software-rasterizer')  # Disable software rasterization
        options.page_load_strategy = 'eager'  # Don't wait for all resources to load
        
        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.implicitly_wait(5)
        
        # Set window size explicitly
        self.driver.set_window_size(1920, 1080)

    def handle_consent(self):
        """Handle GDPR consent popup if present"""
        try:
            consent_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            consent_button.click()
            time.sleep(1)
        except:
            pass

    def wait_for_element(self, by: By, value: str, timeout: int = WAIT_TIME):
        """Wait for an element to be present"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            return None

    def get_season_matches(self, league_url: str) -> List[Dict[str, Any]]:
        """Get all matches for a season from the results page"""
        matches = []
        url = f"{league_url}/results/"
        
        try:
            logger.info(f"Fetching season matches from: {url}")
            self.driver.get(url)
            self.handle_consent()
            
            # Wait for the results container to load
            results_container = self.wait_for_element(By.CLASS_NAME, "sportName")
            if not results_container:
                logger.error("Results container not found")
                return matches

            # Keep clicking "Show more matches" until all matches are loaded
            while True:
                try:
                    more_button = self.wait_for_element(By.CLASS_NAME, "event__more", timeout=5)
                    if not more_button or not more_button.is_displayed():
                        break
                    self.driver.execute_script("arguments[0].click();", more_button)
                    time.sleep(random.uniform(*DELAY_BETWEEN_REQUESTS))
                except:
                    break

            # Get all match rows
            match_rows = self.driver.find_elements(By.CLASS_NAME, "event__match")
            
            for match in match_rows:
                try:
                    match_data = {
                        "date": match.find_element(By.CLASS_NAME, "event__time").text,
                        "home_team": match.find_element(By.CLASS_NAME, "event__participant--home").text,
                        "away_team": match.find_element(By.CLASS_NAME, "event__participant--away").text,
                        "score": {
                            "home": match.find_element(By.CLASS_NAME, "event__score--home").text,
                            "away": match.find_element(By.CLASS_NAME, "event__score--away").text
                        },
                        "league": league_url.split("/")[-1]
                    }
                    
                    # Get match statistics if available
                    stats = self.get_match_statistics(match)
                    if stats:
                        match_data.update(stats)
                    
                    matches.append(match_data)
                    logger.info(f"Processed: {match_data['home_team']} vs {match_data['away_team']}")
                    
                except Exception as e:
                    logger.error(f"Error processing match: {e}")
                    continue
                
            return matches
            
        except Exception as e:
            logger.error(f"Error scraping league {league_url}: {e}")
            return matches

    def get_match_statistics(self, match_element) -> Dict[str, Any]:
        """Extract available statistics from a match element"""
        stats = {}
        
        try:
            # Get possession stats if available
            possession_elements = match_element.find_elements(By.CLASS_NAME, "event__possession")
            if possession_elements:
                stats["possession"] = {
                    "home": possession_elements[0].text if len(possession_elements) > 0 else None,
                    "away": possession_elements[1].text if len(possession_elements) > 1 else None
                }
            
            # Get cards
            home_cards = len(match_element.find_elements(By.CSS_SELECTOR, ".event__card.event__card--home"))
            away_cards = len(match_element.find_elements(By.CSS_SELECTOR, ".event__card.event__card--away"))
            if home_cards or away_cards:
                stats["cards"] = {"home": home_cards, "away": away_cards}
            
            # Get corners
            home_corners = len(match_element.find_elements(By.CSS_SELECTOR, ".event__corner.event__corner--home"))
            away_corners = len(match_element.find_elements(By.CSS_SELECTOR, ".event__corner.event__corner--away"))
            if home_corners or away_corners:
                stats["corners"] = {"home": home_corners, "away": away_corners}
                
        except Exception as e:
            logger.warning(f"Could not get match statistics: {e}")
            
        return stats

    def save_season_data(self, matches: List[Dict[str, Any]], league_name: str):
        """Save the season data to JSON file"""
        if not matches:
            logger.warning("No matches to save")
            return
            
        output_dir = os.path.join("data", "seasons", league_name)
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_dir, f"season_2024_2025_{timestamp}.json")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(matches)} matches to {output_file}")
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def scrape_league(self, league_url: str):
        """Main method to scrape a league's season data"""
        try:
            matches = self.get_season_matches(league_url)
            league_name = league_url.split("/")[-1]
            self.save_season_data(matches, league_name)
        finally:
            if self.driver:
                self.driver.quit()

def main():
    # List of major leagues to scrape
    leagues = [
        "https://www.flashscore.com/football/england/premier-league",
        # "https://www.flashscore.com/football/spain/laliga",
        # "https://www.flashscore.com/football/italy/serie-a",
        # "https://www.flashscore.com/football/germany/bundesliga",
        # "https://www.flashscore.com/football/france/ligue-1",
        # "https://www.flashscore.com/football/netherlands/eredivisie",
        # "https://www.flashscore.com/football/portugal/liga-portugal",
    ]
    
    for league_url in leagues:
        try:
            scraper = LeagueSeasonScraper()
            scraper.scrape_league(league_url)
            # Add delay between leagues
            time.sleep(random.uniform(3, 5))
        except Exception as e:
            logger.error(f"Error processing league {league_url}: {e}")

if __name__ == "__main__":
    main()