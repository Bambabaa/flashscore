from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import json
import os

def analyze_flashscore():
    print("Starting Flashscore analysis...")
    
    try:
        # Setup Chrome with stealth options
        options = webdriver.ChromeOptions()
        options.add_argument('--start-maximized')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Use local ChromeDriver
        chromedriver_path = os.path.join(os.getcwd(), 'drivers', 'chromedriver.exe')
        service = ChromeService(executable_path=chromedriver_path)
        
        print("Starting Chrome browser...")
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 20)
        
        # Add stealth script
        driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        try:
            print("Opening Flashscore...")
            driver.get("https://www.flashscore.com/football/")
            time.sleep(5)
            
            print("\nAnalyzing page structure...")
            element_data = driver.execute_script("""
                var data = {
                    'matches': [],
                    'tournaments': [],
                    'teams': [],
                    'scores': [],
                    'dates': []
                };
                
                // Find tournaments
                document.querySelectorAll('.tournament__header').forEach(el => {
                    data.tournaments.push({
                        className: el.className,
                        text: el.textContent.trim()
                    });
                });
                
                // Find matches
                document.querySelectorAll('.event__match').forEach(el => {
                    data.matches.push({
                        className: el.className,
                        id: el.getAttribute('id'),
                        text: el.textContent.trim()
                    });
                });
                
                // Find teams
                document.querySelectorAll('.event__participant').forEach(el => {
                    data.teams.push({
                        className: el.className,
                        text: el.textContent.trim()
                    });
                });
                
                // Find dates
                document.querySelectorAll('.event__time').forEach(el => {
                    data.dates.push({
                        className: el.className,
                        text: el.textContent.trim()
                    });
                });
                
                return data;
            """)
            
            # Save element data
            with open('page_elements.json', 'w', encoding='utf-8') as f:
                json.dump(element_data, f, indent=2, ensure_ascii=False)
            
            print("\nFound elements:")
            for key, items in element_data.items():
                print(f"- {len(items)} {key}")
                if items:
                    print(f"  Sample {key}: {items[0]['text']}")
            
            print("\nResults saved to page_elements.json")
            print("Browser will stay open for 30 seconds for inspection...")
            time.sleep(30)
            
        except Exception as e:
            print(f"Error during analysis: {e}")
        finally:
            driver.quit()
            print("Browser closed")
            
    except Exception as e:
        print(f"Setup error: {e}")

if __name__ == "__main__":
    analyze_flashscore()