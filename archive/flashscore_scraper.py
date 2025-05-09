from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('flashscore_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FlashscoreScraper:
    def __init__(self):
        self.setup_driver()
        
    def setup_driver(self):
        """Initialize Chrome WebDriver with optimal settings"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--start-maximized')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            chromedriver_path = os.path.join(os.getcwd(), 'drivers', 'chromedriver.exe')
            logger.info(f"Using ChromeDriver from: {chromedriver_path}")
            
            service = ChromeService(executable_path=chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 20)
            logger.info("Chrome WebDriver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
            
    def handle_consent(self):
        """Handle GDPR consent if present"""
        try:
            consent_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            )
            consent_button.click()
            time.sleep(2)
            logger.info("Handled GDPR consent")
        except TimeoutException:
            logger.info("No consent popup found or already accepted")
            
    def get_match_ids(self, date_str):
        """Get match IDs for a specific date"""
        try:
            url = f"https://www.flashscore.com/football/?d={date_str}"
            logger.info(f"Accessing matches for date: {date_str}")
            
            self.driver.get(url)
            time.sleep(5)  # Increased wait time
            
            self.handle_consent()
            
            # Wait for matches to load and get container
            try:
                container = self.wait.until(
                    EC.presence_of_element_located((By.CLASS_NAME, "sportName"))
                )
                logger.info("Found matches container")
            except TimeoutException:
                logger.error("Could not find matches container")
                return []
                
            # Get tournament sections
            tournament_sections = self.driver.find_elements(By.CLASS_NAME, "tournament")
            match_ids = []
            
            for section in tournament_sections:
                try:
                    # Get tournament name
                    tournament_name = section.find_element(By.CLASS_NAME, "tournament__name").text
                    
                    # Get matches in this tournament
                    matches = section.find_elements(By.CLASS_NAME, "sportName__row")
                    
                    for match in matches:
                        try:
                            # Get match ID from the element ID
                            match_id = match.get_attribute("id").split("_")[-1]
                            
                            # Get team names
                            teams = match.find_elements(By.CLASS_NAME, "participant__overflow")
                            team_names = [team.text for team in teams if team.text]
                            
                            # Get match time/status
                            time_element = match.find_elements(By.CLASS_NAME, "event__time")
                            match_time = time_element[0].text if time_element else None
                            
                            # Get score if available
                            score_elements = match.find_elements(By.CLASS_NAME, "event__score--home") + \
                                          match.find_elements(By.CLASS_NAME, "event__score--away")
                            score = " - ".join([s.text for s in score_elements]) if score_elements else None
                            
                            match_data = {
                                "id": match_id,
                                "tournament": tournament_name,
                                "teams": team_names,
                                "score": score,
                                "time": match_time
                            }
                            match_ids.append(match_data)
                            logger.info(f"Found match: {match_data}")
                        except Exception as e:
                            logger.error(f"Error processing match: {e}")
                            continue
                            
                except Exception as e:
                    logger.error(f"Error processing tournament section: {e}")
                    continue
                    
            return match_ids
            
        except Exception as e:
            logger.error(f"Error getting match IDs: {e}")
            return []
            
    def get_match_details(self, match_id):
        """Get detailed information for a specific match"""
        try:
            url = f"https://www.flashscore.com/match/{match_id}/#/match-summary"
            logger.info(f"Getting details for match: {match_id}")
            
            self.driver.get(url)
            time.sleep(3)
            
            # Wait for match info to load
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "duelParticipant"))
            )
            
            match_data = {}
            
            # Get basic match info
            try:
                match_data["teams"] = {
                    "home": self.driver.find_element(By.CLASS_NAME, "duelParticipant__home").text,
                    "away": self.driver.find_element(By.CLASS_NAME, "duelParticipant__away").text
                }
                
                match_data["score"] = self.driver.find_element(By.CLASS_NAME, "detailScore__wrapper").text
                match_data["status"] = self.driver.find_element(By.CLASS_NAME, "detailScore__status").text
                
            except NoSuchElementException as e:
                logger.error(f"Error getting basic match info: {e}")
            
            # Get match statistics
            try:
                stats_button = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@href='#/match-summary/match-statistics']"))
                )
                stats_button.click()
                time.sleep(2)
                
                stats_elements = self.driver.find_elements(By.CLASS_NAME, "wcl-statistics")
                match_data["statistics"] = []
                
                for stat in stats_elements:
                    try:
                        stat_name = stat.find_element(By.CLASS_NAME, "wcl-statistics-category").text
                        stat_values = stat.find_elements(By.CLASS_NAME, "wcl-statistics-value")
                        match_data["statistics"].append({
                            "name": stat_name,
                            "home": stat_values[0].text if len(stat_values) > 0 else None,
                            "away": stat_values[1].text if len(stat_values) > 1 else None
                        })
                    except Exception as e:
                        logger.error(f"Error processing statistic: {e}")
                        continue
                        
            except Exception as e:
                logger.error(f"Error getting match statistics: {e}")
            
            return match_data
            
        except Exception as e:
            logger.error(f"Error getting match details: {e}")
            return None
            
    def save_matches(self, matches, filename):
        """Save match data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(matches)} matches to {filename}")
        except Exception as e:
            logger.error(f"Error saving matches: {e}")
            
    def close(self):
        """Close the browser"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            logger.info("Browser closed")

def main():
    scraper = FlashscoreScraper()
    try:
        # Get today's matches
        date_str = time.strftime("%Y%m%d")
        matches = scraper.get_match_ids(date_str)
        
        if matches:
            logger.info(f"Found {len(matches)} matches")
            
            # Get details for each match
            match_details = []
            for match in matches[:5]:  # Start with first 5 matches for testing
                details = scraper.get_match_details(match['id'])
                if details:
                    match_details.append(details)
                time.sleep(2)  # Delay between requests
                
            # Save results
            if match_details:
                scraper.save_matches(match_details, f'matches_{date_str}.json')
                
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    main()