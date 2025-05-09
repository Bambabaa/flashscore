#!/usr/bin/env python

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timedelta
import time
import logging
import os
import json
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='season_scraper.log'
)
logger = logging.getLogger(__name__)

# Constants
WAIT_TIME = 30  # Increased wait time
PAGE_LOAD_TIMEOUT = 40
RETRY_ATTEMPTS = 5
RETRY_DELAY = 10

def setup_driver():
    """Setup and return configured Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument(f'--window-size=1920,1080')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-infobars')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    try:
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
        })
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        driver.implicitly_wait(WAIT_TIME)
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize Chrome driver: {e}")
        raise

def handle_gdpr_consent(driver):
    """Handle GDPR consent popup if present"""
    try:
        consent_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
        )
        driver.execute_script("arguments[0].click();", consent_button)
        time.sleep(2)
    except (TimeoutException, NoSuchElementException):
        logger.info("No GDPR consent button found or already accepted")
        pass

def wait_for_load(driver):
    """Wait for page to load completely"""
    time.sleep(random.uniform(2, 4))  # Random delay to appear more human-like
    try:
        WebDriverWait(driver, WAIT_TIME).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
    except:
        pass

def get_match_details(driver, match_id):
    """Get detailed statistics for a specific match"""
    try:
        url = f"https://www.flashscore.com/match/{match_id}/#/match-summary/match-statistics"
        logger.info(f"Getting details for match: {match_id}")
        
        driver.get(url)
        wait_for_load(driver)
        
        # Wait for match info to load
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.CLASS_NAME, "duelParticipant"))
        )
        
        match_data = {
            "id": match_id,
            "teams": {},
            "score": {},
            "statistics": {}
        }
        
        # Get team names
        try:
            match_data["teams"] = {
                "home": driver.find_element(By.CLASS_NAME, "duelParticipant__home").text,
                "away": driver.find_element(By.CLASS_NAME, "duelParticipant__away").text
            }
        except Exception as e:
            logger.error(f"Error getting team names: {e}")
        
        # Get score
        try:
            score_element = driver.find_element(By.CLASS_NAME, "detailScore__wrapper")
            match_data["score"]["full"] = score_element.text
        except Exception as e:
            logger.error(f"Error getting score: {e}")
        
        # Get statistics
        try:
            stats_elements = driver.find_elements(By.CLASS_NAME, "stat__row")
            for stat in stats_elements:
                try:
                    stat_name = stat.find_element(By.CLASS_NAME, "stat__categoryName").text
                    stat_values = stat.find_elements(By.CLASS_NAME, "stat__value")
                    match_data["statistics"][stat_name] = {
                        "home": stat_values[0].text if len(stat_values) > 0 else None,
                        "away": stat_values[1].text if len(stat_values) > 1 else None
                    }
                except Exception as e:
                    logger.error(f"Error processing statistic: {e}")
                    continue
        except Exception as e:
            logger.error(f"Error getting match statistics: {e}")
        
        return match_data
        
    except Exception as e:
        logger.error(f"Error getting match details: {e}")
        return None

def save_match_details(match_details, output_dir="data/matches"):
    """Save detailed match information to JSON files"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        for match in match_details:
            if match and "id" in match:
                league_name = match.get("league", "unknown")
                league_dir = os.path.join(output_dir, league_name)
                os.makedirs(league_dir, exist_ok=True)
                
                output_file = os.path.join(league_dir, f"{match['id']}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(match, f, indent=2, ensure_ascii=False)
                logger.info(f"Saved match details to {output_file}")
                
    except Exception as e:
        logger.error(f"Error saving match details: {e}")

def get_league_matches(driver, league_url, start_date, end_date):
    """Fetch match data directly from league results page"""
    matches_data = []
    current_date = start_date
    league_name = league_url.split("/")[-1]
    
    while current_date <= end_date:
        attempts = 0
        while attempts < RETRY_ATTEMPTS:
            try:
                date_str = current_date.strftime("%Y%m%d")
                url = f"{league_url}/results/"
                logger.info(f"Fetching matches for {league_url} on date: {date_str}")
                
                driver.get(url)
                wait_for_load(driver)
                
                # Handle GDPR
                handle_gdpr_consent(driver)
                
                # Wait for matches container to load
                try:
                    WebDriverWait(driver, WAIT_TIME).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "sportName soccer"))
                    )
                except TimeoutException:
                    logger.info(f"No matches found for date {date_str}")
                    break

                # Get all match rows
                match_rows = driver.find_elements(By.CLASS_NAME, "event__match")
                
                for match_row in match_rows:
                    try:
                        # Extract match date
                        match_date = match_row.find_element(By.CLASS_NAME, "event__time").text
                        
                        # Extract teams
                        home_team = match_row.find_element(By.CLASS_NAME, "event__participant--home").text
                        away_team = match_row.find_element(By.CLASS_NAME, "event__participant--away").text
                        
                        # Extract score
                        home_score = match_row.find_element(By.CLASS_NAME, "event__score--home").text
                        away_score = match_row.find_element(By.CLASS_NAME, "event__score--away").text
                        
                        match_data = {
                            "date": match_date,
                            "league": league_name,
                            "home_team": home_team,
                            "away_team": away_team,
                            "score": {
                                "home": home_score,
                                "away": away_score
                            }
                        }
                        
                        # Get additional statistics from the page directly
                        try:
                            stats = {
                                "possession": match_row.find_elements(By.CLASS_NAME, "event__possession"),
                                "cards": match_row.find_elements(By.CLASS_NAME, "event__card"),
                                "corners": match_row.find_elements(By.CLASS_NAME, "event__corner")
                            }
                            
                            if stats["possession"]:
                                match_data["possession"] = {
                                    "home": stats["possession"][0].text if len(stats["possession"]) > 0 else None,
                                    "away": stats["possession"][1].text if len(stats["possession"]) > 1 else None
                                }
                            
                            if stats["cards"]:
                                match_data["cards"] = {
                                    "home": len([c for c in stats["cards"] if "event__card--home" in c.get_attribute("class")]),
                                    "away": len([c for c in stats["cards"] if "event__card--away" in c.get_attribute("class")])
                                }
                            
                            if stats["corners"]:
                                match_data["corners"] = {
                                    "home": len([c for c in stats["corners"] if "event__corner--home" in c.get_attribute("class")]),
                                    "away": len([c for c in stats["corners"] if "event__corner--away" in c.get_attribute("class")])
                                }
                        except Exception as e:
                            logger.warning(f"Could not extract additional statistics: {e}")
                        
                        matches_data.append(match_data)
                        logger.info(f"Processed match: {home_team} vs {away_team}")
                        
                    except Exception as e:
                        logger.error(f"Error extracting match row data: {e}")
                        continue

                # Add small delay between pages
                time.sleep(random.uniform(1, 2))
                break  # Success - exit retry loop

            except Exception as e:
                attempts += 1
                logger.error(f"Attempt {attempts} failed for date {current_date}: {e}")
                if attempts < RETRY_ATTEMPTS:
                    time.sleep(RETRY_DELAY)
                    try:
                        driver.refresh()
                        wait_for_load(driver)
                    except:
                        driver.quit()
                        driver = setup_driver()
                else:
                    logger.error(f"Failed to fetch matches for date {current_date} after {RETRY_ATTEMPTS} attempts")
        
        current_date += timedelta(days=1)
    
    return matches_data

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
    # List of major leagues to scrape with their identifiers
    leagues = [
        "https://www.flashscore.com/football/england/premier-league",
        # "https://www.flashscore.com/football/spain/laliga",
        # "https://www.flashscore.com/football/italy/serie-a",
        # "https://www.flashscore.com/football/germany/bundesliga",
        # "https://www.flashscore.com/football/france/ligue-1",
        # "https://www.flashscore.com/football/netherlands/eredivisie",
        # "https://www.flashscore.com/football/portugal/liga-portugal",
    ]
    
    try:
        # Set default date range for 2024/2025 season
        start_date = "2024-08-01"  # Typical season start
        end_date = "2025-05-31"    # Typical season end
        
        logger.info(f"Scraping season 2024/2025 from {start_date} to {end_date}")
        
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_matches = []
        
        for league_url in leagues:
            driver = None
            try:
                driver = setup_driver()  # Create new driver for each league
                logger.info(f"Processing league: {league_url}")
                matches = get_league_matches(driver, league_url, start_date, end_date)
                all_matches.extend(matches)
                
                # Save match details for this league
                save_match_details(matches)
                
                # Add a delay between leagues to avoid rate limiting
                time.sleep(random.uniform(3, 5))
            except Exception as e:
                logger.error(f"Error processing league {league_url}: {e}")
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        # Save overview of all matches
        if all_matches:
            save_matches(all_matches)
            logger.info(f"Successfully processed {len(all_matches)} matches across {len(leagues)} leagues")
        else:
            logger.warning("No matches were found for the specified date range")
            
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Script failed: {e}")

if __name__ == "__main__":
    main()