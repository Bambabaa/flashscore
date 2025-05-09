from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

def test_flashscore_elements():
    print("Starting Flashscore element test...")
    
    try:
        # Setup Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        # Use local ChromeDriver
        chromedriver_path = os.path.join(os.getcwd(), 'drivers', 'chromedriver.exe')
        service = ChromeService(executable_path=chromedriver_path)
        
        print("Starting Chrome browser...")
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)
        
        try:
            # Open Flashscore
            print("Opening Flashscore...")
            driver.get("https://www.flashscore.com/football/")
            time.sleep(5)
            
            # Test different element selectors
            selectors_to_test = [
                ('div.event__match', "Match elements"),
                ('div.tournament__country', "Tournament country sections"),
                ('div.sportName', "Sport name sections"),
                ('div.event__participant', "Team names"),
                ('div.event__time', "Match times"),
                ('div.event__score', "Match scores")
            ]
            
            print("\nTesting element selectors:")
            for selector, description in selectors_to_test:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    print(f"\n{description}:")
                    print(f"Found {len(elements)} elements")
                    if elements:
                        print(f"Sample text: {elements[0].text}")
                except Exception as e:
                    print(f"Error finding {description}: {e}")
            
            print("\nKeeping browser open for 30 seconds for visual inspection...")
            time.sleep(30)
            
        except Exception as e:
            print(f"Error during testing: {e}")
        finally:
            driver.quit()
            print("Browser closed")
            
    except Exception as e:
        print(f"Setup error: {e}")

if __name__ == "__main__":
    test_flashscore_elements()