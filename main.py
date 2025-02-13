
BOT_TOKEN = ""
CHAT_ID = ""


import platform
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium_stealth import stealth
import time
import json
import requests
import logging
from datetime import datetime

log_filename = f"log_{datetime.now().strftime('%Y-%m-%d')}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Detect the operating system
os_name = platform.system()

# Set up Chrome options
chrome_options = uc.ChromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--headless')  # Comment this line out for debugging
chrome_options.binary_location = "/usr/bin/google-chrome"

# Initialize undetected-chromedriver
driver = uc.Chrome(options=chrome_options)

# Apply selenium-stealth
stealth(driver,
    languages=["en-US", "en"],
    vendor="Google Inc.",
    platform="Win32",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris OpenGL Engine",
    fix_hairline=True,
)
telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

try:
    # Step 1: Open the first link
    url1 = 'https://www.dextools.io/app/en/solana/gainers'
    driver.get(url1)
    time.sleep(3)  # Wait for the page to load

    # Step 2: Open a new tab
    driver.switch_to.new_window('tab')
    
    # Step 3: Open the second link in the new tab
    url2 = 'https://www.dextools.io/shared/analytics/pairs/gainers?chain=solana'
    driver.get(url2)
    time.sleep(5)  # Wait for the page to load

    # Step 4: Extract JSON data using JavaScript
    script = '''
        return fetch("https://www.dextools.io/shared/analytics/pairs/gainers?chain=solana")
            .then(response => response.json())
            .then(data => JSON.stringify(data))
            .catch(error => console.error('Error:', error));
    '''
    json_data = driver.execute_script(script)
    data = json.loads(json_data)
    message = ""
    if data.get("code") == "OK":
        # Iterate over each item in data
        for item in data.get("data", [])[:20]:
            symbol = item.get("token", {}).get("symbol")
            name = item.get("token", {}).get("name")
            token = item.get("_id", {}).get("token")
            tokenShort = f"{token[:5]}...{token[-4:]}"
            tokenLink = f'<a href="http://solscan.io/token/{token}" target="_blank">{tokenShort}</a>'
            priceDiff = item.get("priceDiff")
            priceDiffFormatted = f"{priceDiff:,.2f}%"
            message += f"Symbol: {symbol}\nName: {name}\nToken: {tokenLink}\nChange: {priceDiffFormatted}\n\n"
    else:
        message = "Cannot parse code from dextool"

    params = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.get(telegram_url, params=params)
    if not response.status_code == 200:
        logging.error(f"Failed to send message. Status code: {response.status_code}")
        logging.error("Response: %s", response.json())
except Exception as e:
    logging.error(f"An error occurred: {str(e)}")
    params = {
        'chat_id': CHAT_ID,
        'text': "Error occurs. Wait for next cycle",
        'parse_mode': 'HTML'
    }
    response = requests.get(telegram_url, params=params)


finally:  
    # Close the browser
    time.sleep(2)
    driver.quit()
