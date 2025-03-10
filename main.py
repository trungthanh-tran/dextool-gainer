import platform
import os
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium_stealth import stealth
import time
import json
import requests
import logging
import random
import configparser
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logger = logging.getLogger('DexScreenerBot')
logger.setLevel(logging.INFO)

# Create formatters
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Set up daily rotating file handler
file_handler = TimedRotatingFileHandler(
    filename='logs/dexscreener.log',
    when='midnight',
    interval=1,
    backupCount=30,  # Keep logs for 30 days
    encoding='utf-8'
)
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.INFO)

# Set up console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_formatter)
console_handler.setLevel(logging.INFO)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.info("Script started")

def load_config():
    """
    Load configuration from config.properties file
    Returns tuple of (bot_token, chat_id)
    """
    config = configparser.ConfigParser()
    
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, 'config.properties')
    
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file {config_file} not found")
    
    logger.info(f"Loading configuration from: {config_file}")
    config.read(config_file)
    
    # Check if required section and values exist
    if not config.has_section('telegram'):
        raise ValueError("Missing [telegram] section in config file")
    
    bot_token = config.get('telegram', 'bot_token', fallback='')
    chat_id = config.get('telegram', 'chat_id', fallback='')
    
    # Validate credentials
    if not bot_token or not chat_id:
        raise ValueError("Bot token and chat ID must be set in config.properties")
        
    return bot_token, chat_id

# Load configuration
try:
    BOT_TOKEN, CHAT_ID = load_config()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configuration: {str(e)}")
    raise

# Detect the operating system
os_name = platform.system()
logger.info(f"Operating System: {os_name}")

# Set up Chrome options
chrome_options = uc.ChromeOptions()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--window-size=1920,1080')
chrome_options.add_argument('--headless')  # Comment this line out for debugging

# Set Chrome binary location based on OS
if os_name == "Windows":
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_binary = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_binary = path
            break
    if chrome_binary is None:
        raise Exception("Chrome browser not found in default locations")
    chrome_options.binary_location = chrome_binary
    logger.info(f"Using Chrome binary at: {chrome_binary}")
else:
    chrome_options.binary_location = "/usr/bin/google-chrome"
    logger.info("Using default Linux Chrome binary location")

# Initialize undetected-chromedriver
logger.info("Initializing Chrome driver with stealth settings")
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
logger.info("Chrome driver initialized successfully")
telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def wait_for_page_load(driver, url, max_retries=2):
    """
    Try to load a page and verify it's loaded, with retries
    Returns True if successful, False otherwise
    """
    retry_count = 0
    while retry_count <= max_retries:
        try:
            logger.info(f"Loading URL: {url}" + (f" (Attempt {retry_count + 1})" if retry_count > 0 else ""))
            driver.get(url)
            
            sleep_time = random.uniform(1, 3)
            logger.info(f"Waiting for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

            # Wait for the document ready state to be complete
            WebDriverWait(driver, 10).until(
                lambda driver: driver.execute_script('return document.readyState') == 'complete'
            )
            
            # Try to find a common element that should be present when page is loaded
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            logger.info(f"Page {url} loaded successfully")
            return True
            
        except TimeoutException as e:
            retry_count += 1
            if retry_count > max_retries:
                logger.error(f"Failed to load page {url} after {max_retries} attempts")
                return False
            logger.warning(f"Page load timeout, will retry. Error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error loading page {url}: {str(e)}")
            return False
    
    return False

try:
    # Step 1: Define URLs
    url1 = 'https://www.dextools.io/app/en/solana/gainers'
    url2 = 'https://www.dextools.io/shared/analytics/pairs/gainers?chain=solana'
    
    # Open the first link
    logger.info(f"Accessing first URL: {url1}")
    if not wait_for_page_load(driver, url1):
        raise Exception(f"Failed to load page {url1}")

    # Step 2: Open a new tab
    logger.info("Opening new tab")
    driver.switch_to.new_window('tab')
    
    # Step 3: Open the second link in the new tab
    logger.info(f"Accessing second URL: {url2}")
    if not wait_for_page_load(driver, url2):
        raise Exception(f"Failed to load page {url2}")

    # Step 4: Extract JSON data using JavaScript
    logger.info("Attempting to fetch JSON data")
    max_retries = 3
    retry_count = 0
    success = False
    
    while retry_count < max_retries and not success:
        try:
            if retry_count > 0:
                sleep_time = random.uniform(1, 3)
                logger.info(f"Retry attempt {retry_count + 1}/{max_retries}. Waiting {sleep_time:.2f} seconds before retry...")
                time.sleep(sleep_time)
            
            script = '''
                return fetch("https://www.dextools.io/shared/analytics/pairs/gainers?chain=solana")
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok: ' + response.status);
                        }
                        return response.json();
                    })
                    .then(data => JSON.stringify(data))
                    .catch(error => {
                        console.error('Error:', error);
                        return JSON.stringify({error: error.message});
                    });
            '''
            json_data = driver.execute_script(script)
            data = json.loads(json_data)
            
            if 'error' in data:
                raise Exception(f"Fetch error: {data['error']}")
                
            logger.info("JSON data successfully parsed")
            success = True
            
        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                logger.error(f"Failed to fetch data after {max_retries} attempts. Last error: {str(e)}")
                raise
            logger.warning(f"Attempt {retry_count} failed: {str(e)}")

    message = ""
    if data.get("code") == "OK":
        logger.info("Processing top 20 tokens")
        # Iterate over each item in data
        for item in data.get("data", [])[:20]:
            try:
                symbol = item.get("token", {}).get("symbol")
                name = item.get("token", {}).get("name")
                token = item.get("_id", {}).get("token")
                banner = item.get("token", {}).get("logo")
                url = f"<a href='https://www.dextools.io/resources/tokens/logos/{banner}'>{symbol}</a>"
                tokenShort = f"{token[:5]}...{token[-4:]}"
                tokenLink = f'<a href="http://solscan.io/token/{token}" target="_blank">{tokenShort}</a>'
                priceDiff = item.get("priceDiff")
                priceDiffFormatted = f"{priceDiff:,.2f}%"
                
                # Create message for this specific token
                token_message = f"Symbol: {url}\nName: {name}\nToken: {tokenLink}\nChange: {priceDiffFormatted}"
                
                # Send message for this token
                logger.info(f"Sending message for token {symbol}")
                params = {
                    'chat_id': CHAT_ID,
                    'text': token_message,
                    'parse_mode': 'HTML'
                }
                response = requests.get(telegram_url, params=params)
                
                if response.status_code == 200:
                    logger.info(f"Message for {symbol} sent successfully")
                else:
                    logger.error(f"Failed to send message for {symbol}. Status code: {response.status_code}")
                    logger.error("Response: %s", response.json())
                
                # Add random delay between messages to avoid rate limiting
                sleep_time = random.uniform(1, 2)
                logger.info(f"Waiting {sleep_time:.2f} seconds before next message")
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Error processing token {symbol if 'symbol' in locals() else 'unknown'}: {str(e)}")
                continue
                
        logger.info("Successfully processed all token data")
    else:
        logger.error("Failed to get valid response code from dextool")
        params = {
            'chat_id': CHAT_ID,
            'text': "Cannot parse code from dextool",
            'parse_mode': 'HTML'
        }
        response = requests.get(telegram_url, params=params)
    logger.info("Sending message to Telegram")
    if response.status_code == 200:
        logger.info("Message successfully sent to Telegram")
    else:
        logger.error(f"Failed to send message. Status code: {response.status_code}")
        logger.error("Response: %s", response.json())
except Exception as e:
    logger.error(f"An error occurred: {str(e)}", exc_info=True)
    params = {
        'chat_id': CHAT_ID,
        'text': "Error occurs. Wait for next cycle",
        'parse_mode': 'HTML'
    }
    response = requests.get(telegram_url, params=params)
    logger.info("Error notification sent to Telegram")

finally:  
    # Close the browser
    logger.info("Cleaning up and closing browser")
    time.sleep(2)
    driver.quit()
    logger.info("Script execution completed")
