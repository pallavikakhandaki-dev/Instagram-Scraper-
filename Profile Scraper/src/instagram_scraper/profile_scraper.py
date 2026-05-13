import os

# Fix for OSError: Could not find a suitable TLS CA certificate bundle
# This unsets problematic environment variables that might point to non-existent certificate bundles
for var in ['CURL_CA_BUNDLE', 'REQUESTS_CA_BUNDLE', 'SSL_CERT_FILE']:
    if var in os.environ:
        del os.environ[var]

import time
import random
import json
import pickle
import re
import pandas as pd
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuration & Setup ---
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
cookies_file = os.path.join(project_root, "secrets", "cookies.pkl")
output_dir = os.path.join(project_root, "data", "instagram_data")
excel_dir = os.path.join(project_root, "data", "excel_data")

if not os.path.exists(output_dir): os.makedirs(output_dir)
if not os.path.exists(excel_dir): os.makedirs(excel_dir)

def random_sleep(a=2, b=5):
    time.sleep(random.uniform(a, b))

def load_cookies(driver, filename):
    if os.path.exists(filename):
        with open(filename, "rb") as file:
            cookies = pickle.load(file)
            for cookie in cookies:
                try: driver.add_cookie(cookie)
                except: pass
        print(f"Cookies loaded from {filename}")


def validate_instagram_session():
    """
    Returns True if cookies produce a logged-in Instagram session, else False.
    """
    if not os.path.exists(cookies_file):
        return False

    try:
        with open(cookies_file, "rb") as f:
            cookies = pickle.load(f)
        if not isinstance(cookies, list) or not cookies:
            return False
        # sessionid is the key cookie for authenticated session
        has_session_cookie = any(
            isinstance(c, dict) and c.get("name") == "sessionid" and str(c.get("value", "")).strip()
            for c in cookies
        )
        if not has_session_cookie:
            return False
    except Exception:
        return False

    chrome_opts = Options()
    chrome_opts.add_argument("--incognito")
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1280,800")
    chrome_opts.add_argument("--disable-blink-features=AutomationControlled")

    driver = None
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_opts)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.get("https://www.instagram.com/")
        random_sleep(2, 3)
        load_cookies(driver, cookies_file)
        driver.refresh()
        random_sleep(3, 5)

        # Visit a login-required page to verify session strongly.
        driver.get("https://www.instagram.com/accounts/edit/")
        random_sleep(2, 4)

        current = (driver.current_url or "").lower()
        if "accounts/login" in current:
            return False

        login_inputs = driver.find_elements(By.XPATH, "//input[@name='username' or @name='password']")
        if login_inputs:
            return False

        login_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/accounts/login')]")
        if login_links:
            return False

        page_text = (driver.execute_script("return document.body.innerText || ''") or "").lower()
        login_markers = ["log in", "login", "password", "sign up"]
        if any(m in page_text for m in login_markers) and "profile" not in page_text:
            return False
        return True
    except Exception:
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

def parse_timeframe(timeframe_str):
    now = datetime.now(timezone.utc)
    if not timeframe_str or timeframe_str.lower() == 'all': return None
    match = re.search(r"(\d+)\s*([a-z]+)", timeframe_str.lower())
    if not match: return None
    value, unit = int(match.group(1)), match.group(2)
    if unit.startswith('h'): return now - timedelta(hours=value)
    if unit.startswith('d'): return now - timedelta(days=value)
    if unit.startswith('w'): return now - timedelta(weeks=value)
    if unit.startswith('m'): return now - timedelta(days=value * 30)
    return None


def parse_date_range(start_date_str, end_date_str):
    if not start_date_str or not end_date_str:
        return None, None
    try:
        start_dt = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end_dt = datetime.strptime(end_date_str, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=timezone.utc
        )
        return start_dt, end_dt
    except Exception:
        return None, None

# --- Extraction Helpers ---

def extract_meta_only(driver, post_url):
    """FAST extraction of caption, likes, and timestamp."""
    data = {
        "post_url": post_url,
        "caption": "",
        "likes_count": "",
        "comments_count": "",
        "timestamp": "",
        "comments": []
    }
    try:
        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, "//time")))
        data["timestamp"] = driver.find_element(By.XPATH, "//time").get_attribute("datetime")

        
        # Caption
        try:
            caption_xpath = '(//div[@class="x5yr21d xw2csxc x1odjw0f x1n2onr6"]//following::span)[1]'
            data["caption"] = driver.find_element(By.XPATH, caption_xpath).text
        except:
            try: data["caption"] = driver.find_element(By.XPATH, '(//h1/following::span)[1]').text
            except: pass

        # Likes
        likes_xpaths = [
            '(//section[@class="x6s0dn4 xrvj5dj x1o61qjw"]//child::span[@role="button"])[1]',
            '//a[contains(@href, "/liked_by/")]//span',
            '//span[contains(text(), "likes")]'
        ]
        for xpath in likes_xpaths:
            try:
                text = driver.find_element(By.XPATH, xpath).text
                # regex to capture numbers with K/M suffixes: e.g. "3.3K", "1.2M", "1,234"
                match = re.search(r'([\d,.]+[KMkm]?)', text)
                if match:
                    data["likes_count"] = match.group(1)
                    break
            except: continue

        # Comments count
        try:
            comm_xpath = '(//section[@class="x6s0dn4 xrvj5dj x1o61qjw"]//child::span[@role="button"])[2] | //span[contains(text(), "comments")]'
            data["comments_count"] = driver.find_element(By.XPATH, comm_xpath).text
        except: pass
    except: pass
    return data

def scrape_comments_deep(driver, post_data):
    """SLOW extraction of comments. Updates post_data in place."""
    post_url = post_data["post_url"]
    print(f"  -> Deep scrolling comments for {post_url}...")
    try:
        find_scroll_js = "let s = null; document.querySelectorAll('div, ul').forEach(el => { if ((window.getComputedStyle(el).overflowY === 'auto' || window.getComputedStyle(el).overflowY === 'scroll') && el.clientHeight > 200) s = el; }); return s;"
        scroll_box = driver.execute_script(find_scroll_js)
        if scroll_box:
            last_h = driver.execute_script("return arguments[0].scrollHeight", scroll_box)
            no_change_count = 0
            for i in range(100):
                driver.execute_script("arguments[0].scrollTo(0, arguments[0].scrollHeight);", scroll_box)
                time.sleep(1.0) # Faster scroll
                try:
                    load_more_xpath = "//li//div[@role='button']//span[contains(text(), 'View all') or contains(text(), 'View more') or @aria-label='Load more comments']"
                    load_more = driver.find_elements(By.XPATH, load_more_xpath)
                    for btn in load_more: 
                        driver.execute_script("arguments[0].click();", btn)
                except: pass
                
                new_h = driver.execute_script("return arguments[0].scrollHeight", scroll_box)
                if new_h == last_h:
                    no_change_count += 1
                    if no_change_count >= 4: break
                else:
                    no_change_count = 0
                last_h = new_h
        
        # Extract
        comment_els = driver.find_elements(By.XPATH, '//div[@class="x5yr21d xw2csxc x1odjw0f x1n2onr6"]')
        all_txt = []
        for c in comment_els:
            t = c.text.strip()
            if t and len(t) > 2 and t not in all_txt:
                if any(m in t.lower() for m in ["reply", "view replies", "h", "m", "d", "w"]) and len(t) < 30: continue
                all_txt.append(t)
        if all_txt:
            post_data["comments"] = [{"comment_text": "\n".join(all_txt)}]
            print(f"  -> {len(all_txt)} comments captured.")
    except Exception as e:
        print(f"  -> Comment error: {e}")

def is_pinned(el):
    """Enhanced check for pinned posts."""
    try:
        pinned_selectors = [
            ".//*[local-name()='svg' and @aria-label='Pinned']",
            ".//*[local-name()='svg']/*[local-name()='title' and contains(text(), 'Pinned')]",
            ".//span[contains(@class, 'pinned')]",
            ".//*[contains(@aria-label, 'Pinned')]"
        ]
        for sel in pinned_selectors:
            if len(el.find_elements(By.XPATH, sel)) > 0:
                return True
    except:
        pass
    return False

def save_realtime_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Core Logic ---

def run_unified_scraper(leader_name=None, tf_input=None, output_path=None, start_date=None, end_date=None):
    try:
        leaders_path = os.path.join(project_root, "config", "leaders.json")
        with open(leaders_path, "r") as f: leaders = json.load(f)
    except Exception as e: 
        print(f"Error loading leaders.json: {e}")
        return

    if not leader_name:
        leader_name = input("\nEnter leader name: ").strip()
    if leader_name not in leaders: return

    if tf_input is None:
        tf_input = input("Selection: ").strip()
    cutoff_dt = parse_timeframe(tf_input)
    range_start_dt, range_end_dt = parse_date_range(start_date, end_date)

    chrome_opts = Options()
    chrome_opts.add_argument("--incognito")
    chrome_opts.add_argument("--start-maximized")
    chrome_opts.add_argument("--disable-blink-features=AutomationControlled")
    chrome_opts.add_argument("--headless=new") # Run in background
    chrome_opts.add_argument("--disable-gpu")
    chrome_opts.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_opts)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    driver.get("https://www.instagram.com/")
    random_sleep(3, 5); load_cookies(driver, cookies_file); driver.refresh(); random_sleep(3, 5)

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_path if output_path else os.path.join(output_dir, f"{leader_name.replace(' ', '_').lower()}_{timestamp_str}.json")
    leader_results = {"leader_name": leader_name, "scrape_timestamp": timestamp_str, "profiles": []}
    processed_urls = set()

    for profile_url in leaders[leader_name]:
        if "instagram.com" not in profile_url: continue
        print(f"\nProfile: {profile_url}")

        driver.get(profile_url)
        # Wait longer for profile to load
        WebDriverWait(driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
        random_sleep(4, 6)

        try:
            # 1. Use JS to get all text on the page - most reliable way to bypass DOM complexities
            page_text = driver.execute_script("return document.body.innerText").lower()
            
            # 2. Username detection
            username = ""
            user_selectors = ["//header//h2", "//h2", "//h1"]
            for sel in user_selectors:
                try: 
                    el = driver.find_element(By.XPATH, sel)
                    if el.is_displayed():
                        username = el.text.strip()
                        if username: break
                except: continue
            if not username:
                username = profile_url.strip("/").split("/")[-1].replace("_", " ")

            # 3. Stats extraction using regex on innerText
            followers = "0"; posts_count = "0"
            # Support variations: "1.2M followers", "350 followers", "10 posts", etc.
            f_match = re.search(r'([\d,.]+[KMkm]?)\s*follower', page_text)
            p_match = re.search(r'([\d,.]+[KMkm]?)\s*post', page_text)
            
            if f_match: followers = f_match.group(1).upper()
            if p_match: posts_count = p_match.group(1).upper()

            # 4. Bio
            bio = ""
            try: 
                bio_el = driver.find_element(By.XPATH, '//div[@class="_ap3a _aaco _aacw _aacz _aada _aade"] | //header//section//div[contains(@class, "ap3a")]')
                bio = bio_el.text.strip()
            except: pass
        except Exception as e:
            print(f"  -> Stats extraction error: {e}")
            username = profile_url.strip("/").split("/")[-1].replace("_", " "); followers = "0"; posts_count = "0"; bio = ""

        profile_entry = {"account": {"username": username, "bio": bio, "followers": followers, "posts_count": posts_count}, "posts": []}
        leader_results["profiles"].append(profile_entry); save_realtime_json(json_path, leader_results)

        last_h = driver.execute_script("return document.body.scrollHeight")
        stop_p = False
        while not stop_p:
            els = driver.find_elements(By.XPATH, "//a[contains(@href, '/p/') or contains(@href, '/reel/')]")
            for el in els:
                href = el.get_attribute("href")
                if not href: continue
                normalized = href.split('?')[0].replace('/reel/', '/p/')
                if normalized not in processed_urls:
                    processed_urls.add(normalized)
                    pinned = is_pinned(el)
                    print(f"Post: {normalized}")
                    
                    main_win = driver.current_window_handle
                    driver.execute_script("window.open(arguments[0], '_blank');", normalized)
                    random_sleep(1.5, 2.5); driver.switch_to.window(driver.window_handles[-1])
                    
                    try:
                        # FAST STEP: Metadata
                        post_data = extract_meta_only(driver, normalized)
                        if post_data["timestamp"]:
                            ts = datetime.fromisoformat(post_data["timestamp"].replace('Z', '+00:00'))

                            if range_start_dt and range_end_dt:
                                if ts < range_start_dt:
                                    if not pinned:
                                        print("  -> Older than custom range. Stopping.")
                                        driver.close(); driver.switch_to.window(main_win); stop_p = True; break
                                    else:
                                        print("  -> Pinned but older than custom range. Skipping.")
                                        driver.close(); driver.switch_to.window(main_win); continue
                                if ts > range_end_dt:
                                    print("  -> Newer than custom range end. Skipping.")
                                    driver.close(); driver.switch_to.window(main_win); continue
                            elif cutoff_dt:
                                if ts < cutoff_dt:
                                    if not pinned:
                                        print("  -> Too old. Stopping.")
                                        driver.close(); driver.switch_to.window(main_win); stop_p = True; break
                                    else:
                                        print("  -> Pinned but old. Skipping.")
                                        driver.close(); driver.switch_to.window(main_win); continue
                        
                        # Within timeframe: IMMEDIATE UPDATE
                        profile_entry["posts"].append(post_data)
                        save_realtime_json(json_path, leader_results) # Dash shows post NOW
                        
                        # SLOW STEP: Comments
                        scrape_comments_deep(driver, post_data)
                        save_realtime_json(json_path, leader_results) # Dash shows comments LATER
                        
                    except: pass
                    if len(driver.window_handles) > 1: driver.close()
                    driver.switch_to.window(main_win)

            if stop_p: break
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            random_sleep(3, 5); new_h = driver.execute_script("return document.body.scrollHeight")
            if new_h == last_h: break
            last_h = new_h

    driver.quit()
    print(f"Final: {json_path}")

if __name__ == "__main__":
    run_unified_scraper()
