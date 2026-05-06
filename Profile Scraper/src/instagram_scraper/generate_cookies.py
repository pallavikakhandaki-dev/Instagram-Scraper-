import pickle
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

# Fix for OSError: Could not find a suitable TLS CA certificate bundle
# This unsets problematic environment variables that might point to non-existent certificate bundles
import os
for var in ['CURL_CA_BUNDLE', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE']:
    if var in os.environ:
        del os.environ[var]

def generate_new_cookies():
    # Setup Chrome
    options = Options()
    # Do not use headless or incognito so you can manually log in
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    print("Starting browser...")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        print("Opening Instagram...")
        driver.get("https://www.instagram.com/accounts/login/")
        
        print("\n" + "="*50)
        print("⚠️ ACTION REQUIRED: Please log in to your Instagram account in the opened browser window.")
        print("You have 60 seconds to enter your credentials, solve any captchas, and click log in...")
        print("="*50 + "\n")
        
        # Wait for the user to log in manually
        # You can increase this time if you need longer to log in
        for remaining in range(60, 0, -1):
            print(f"Time remaining to log in: {remaining} seconds...", end="\r")
            time.sleep(1)
            
        print("\n\nTime is up! Attempting to save your cookies...")
        
        # Save the cookies to cookies.pkl
        cookies = driver.get_cookies()
        secrets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "secrets")
        os.makedirs(secrets_dir, exist_ok=True)
        cookies_path = os.path.join(secrets_dir, "cookies.pkl")
        with open(cookies_path, "wb") as file:
            pickle.dump(cookies, file)
            
        print("✅ Successfully saved your credentials to cookies.pkl!")
        print("You can now run your scraper code.")
        
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    generate_new_cookies()
