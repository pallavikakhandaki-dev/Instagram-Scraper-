"""
scrape_from_links.py
--------------------
Scrapes Instagram post data (caption, likes, comments, timestamp)
directly from a .txt file containing post URLs stored in the html_files folder.

Usage:
    python scrape_from_links.py

The script will list all .txt files in html_files/ and ask you to pick one.
It then scrapes every post URL in that file and saves results to:
    - instagram_data/<label>_<timestamp>.json
    - excel_data/<label>_<timestamp>.xlsx
"""

import os
import sys
# Fix for TLS certificate path error
os.environ['CURL_CA_BUNDLE'] = ""
os.environ['REQUESTS_CA_BUNDLE'] = ""
os.environ['SSL_CERT_FILE'] = ""

import time
import time
import random
import json
import pickle
import re
import pandas as pd
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────
cookies_file = os.path.join("..", "..", "..", "secrets", "cookies.pkl")
HTML_FILES_DIR = os.path.abspath(os.path.join("..", "..", "html_files"))

# ─────────────────────────────────────────────
# Chrome Setup
# ─────────────────────────────────────────────
custom_headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.5",
}

chrome_options = Options()
chrome_options.add_argument(f"user-agent={custom_headers['User-Agent']}")
chrome_options.add_argument(f"accept-language={custom_headers['Accept-Language']}")
chrome_options.add_argument("--incognito")
chrome_options.add_argument("--start-maximized")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option("useAutomationExtension", False)


# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────
def random_sleep(a=2, b=5):
    time.sleep(random.uniform(a, b))


def load_cookies(driver, filename):
    print(f"[DEBUG] Attempting to load cookies from {filename}", flush=True)
    if os.path.exists(filename):
        with open(filename, "rb") as file:
            print(f"[DEBUG] Reading cookies file...", flush=True)
            cookies = pickle.load(file)
            print(f"[DEBUG] Found {len(cookies)} cookies. Adding them to driver...", flush=True)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    # print(f"[DEBUG] Skipping cookie: {e}", flush=True)
                    pass
        print(f"[SUCCESS] Cookies loaded from {filename}", flush=True)
    else:
        print(f"[WARNING] No cookies file found at {filename}. You may need to log in manually.", flush=True)


def init_driver_with_cookies():
    """Creates a Chrome driver and logs into Instagram using saved cookies."""
    # MANUAL FIX: Bypassing ChromeDriverManager download hang by using local cache
    driver_path = r"C:\Users\The Strelema\.wdm\drivers\chromedriver\win64\147.0.7727.57\chromedriver-win32\chromedriver.exe"
    print(f"[DEBUG] Using manual driver path: {driver_path}", flush=True)
    service = Service(executable_path=driver_path)
    
    print("[DEBUG] Starting WebDriver...", flush=True)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("[DEBUG] WebDriver started. Modifying navigator.webdriver...", flush=True)
    
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    
    print("[DEBUG] Navigating to Instagram home page to load cookies...", flush=True)
    driver.get("https://www.instagram.com")
    
    print("[DEBUG] Home page loaded. Waiting 5s...", flush=True)
    random_sleep(3, 5)
    
    load_cookies(driver, cookies_file)
    
    print("[DEBUG] Refreshing page to apply cookies...", flush=True)
    driver.refresh()
    
    print("[DEBUG] Waiting 6s for refresh...", flush=True)
    random_sleep(4, 6)
    
    print("[DEBUG] Driver initialization complete.", flush=True)
    return driver


def dismiss_modals(driver):
    """Closes any login / sign-up / cookie consent popups."""
    selectors = [
        "//button[contains(text(), 'Not Now')]",
        "//*[@aria-label='Close']",
        "//button[contains(text(), 'Allow all cookies')]",
        "//div[@role='dialog']//div[@role='button' and @aria-label='Close']",
    ]
    for xpath in selectors:
        try:
            btns = driver.find_elements(By.XPATH, xpath)
            for btn in btns:
                try:
                    btn.click()
                    random_sleep(0.5, 1)
                except Exception:
                    pass
        except Exception:
            pass


def normalize_post_url(link):
    """Converts any Instagram post/reel URL to a clean /p/ URL."""
    link = link.strip()
    if "/reel/" in link:
        clean_path = link[link.find("/reel/"):].replace("/reel/", "/p/").split("?")[0]
        return "https://www.instagram.com" + clean_path
    elif "/p/" in link:
        clean_path = link[link.find("/p/"):].split("?")[0]
        return "https://www.instagram.com" + clean_path
    return link


def scrape_post(driver, post_url):
    """
    Navigates to a single Instagram post and extracts:
    caption, likes, comments count, timestamp, and all comment text.
    """
    post_data = {
        "post_url": post_url,
        "caption": "",
        "likes_count": "",
        "comments_count": "",
        "timestamp": "",
        "comments": [],
    }

    try:
        driver.get(post_url)
        random_sleep(5, 8)
        dismiss_modals(driver)
    except Exception as e:
        print(f" [ERROR] Failed to load {post_url}: {e}", flush=True)
        return post_data

    # Timestamp
    try:
        post_data["timestamp"] = driver.find_element(By.XPATH, "//time").get_attribute("datetime")
    except Exception:
        pass

    # Caption
    try:
        caption = driver.find_element(
            By.XPATH,
            '(//div[@class="x5yr21d xw2csxc x1odjw0f x1n2onr6"]//following::span)[1]',
        ).text
        post_data["caption"] = caption
    except Exception:
        try:
            post_data["caption"] = driver.find_element(
                By.XPATH, "(//h1/following::span)[1]"
            ).text
        except Exception:
            pass

    # Likes
    try:
        likes_xpaths = [
            '(//section[@class="x6s0dn4 xrvj5dj x1o61qjw"]//child::span[@role="button"])[1]',
            '//a[contains(@href, "/liked_by/")]//span',
            '//span[contains(text(), "likes")]',
            '//div[contains(text(), "likes")]',
            '//section//span[contains(text(), "others")]',
        ]
        for xpath in likes_xpaths:
            try:
                element = driver.find_element(By.XPATH, xpath)
                text = element.text.strip()
                if text:
                    match = re.search(r"([\d,.]+)", text)
                    if match:
                        post_data["likes_count"] = match.group(1)
                        break
            except Exception:
                continue
    except Exception:
        pass

    # Comments count
    try:
        comments_xpath = (
            '(//section[@class="x6s0dn4 xrvj5dj x1o61qjw"]//child::span[@role="button"])[2]'
            ' | //span[contains(text(), "comments")]'
        )
        post_data["comments_count"] = driver.find_element(By.XPATH, comments_xpath).text
    except Exception:
        pass

    # Scroll & extract comments
    try:
        find_scroll_container_js = """
        let scrollable = null;
        document.querySelectorAll('div, ul').forEach(el => {
            let style = window.getComputedStyle(el);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll') && el.clientHeight > 200) {
                scrollable = el;
            }
        });
        return scrollable;
        """
        scroll_box = driver.execute_script(find_scroll_container_js)

        if scroll_box:
            print(f"  Scrolling comments...", flush=True)
            last_h = driver.execute_script("return arguments[0].scrollHeight", scroll_box)
            no_change = 0

            for _ in range(50):
                driver.execute_script(
                    "arguments[0].scrollTo(0, arguments[0].scrollHeight);", scroll_box
                )
                time.sleep(1.5)

                try:
                    load_more_xpath = (
                        "//li//div[@role='button']//span[contains(text(),'View all') or contains(text(),'View more')"
                        " or @aria-label='Load more comments']"
                    )
                    for btn in driver.find_elements(By.XPATH, load_more_xpath):
                        try:
                            driver.execute_script("arguments[0].click();", btn)
                            time.sleep(1)
                        except Exception:
                            pass
                except Exception:
                    pass

                new_h = driver.execute_script("return arguments[0].scrollHeight", scroll_box)
                if new_h == last_h:
                    no_change += 1
                    if no_change >= 3:
                        break
                else:
                    no_change = 0
                last_h = new_h

        # Extract comment text blocks
        comment_container_xpath = '//div[@class="x5yr21d xw2csxc x1odjw0f x1n2onr6"]'
        comments_elements = driver.find_elements(By.XPATH, comment_container_xpath)

        all_comments_text = []
        skip_words = ["reply", "view replies", "replies", "comments from facebook"]

        for c in comments_elements:
            txt = c.text.strip()
            if not txt or len(txt) <= 2 or txt in all_comments_text:
                continue
            lower = txt.lower()
            is_meta = any(w in lower for w in skip_words)
            if is_meta and len(txt) < 30:
                continue
            if txt in ["Reply", "7h", "6h", "5h", "4h", "3h", "2h", "1h"]:
                continue
            all_comments_text.append(txt)

        if all_comments_text:
            post_data["comments"] = [{"comment_text": "\n".join(all_comments_text)}]
            print(f"  Extracted {len(all_comments_text)} comment blocks.", flush=True)

    except Exception as e:
        print(f"[WARNING] Comment extraction failed: {e}", flush=True)

    return post_data


# ─────────────────────────────────────────────
# Main Flow
# ─────────────────────────────────────────────
def main():
    # Ensure output dirs exist
    os.makedirs(os.path.join("..", "..", "data", "instagram_data"), exist_ok=True)
    os.makedirs(os.path.join("..", "..", "data", "excel_data"), exist_ok=True)

    # Search both html_files root AND any sub-folders
    txt_files = []
    for root, dirs, files in os.walk(HTML_FILES_DIR):
        for f in files:
            if f.endswith(".txt"):
                rel = os.path.relpath(os.path.join(root, f), HTML_FILES_DIR)
                txt_files.append(rel)

    if not txt_files:
        print(f"[ERROR] No .txt files found in {HTML_FILES_DIR}", flush=True)
        return

    # Non-interactive support
    selected_rel = None
    label = None

    if len(sys.argv) > 1:
        # arg1: file index or name
        choice = sys.argv[1]
        if choice.isdigit() and 1 <= int(choice) <= len(txt_files):
            selected_rel = txt_files[int(choice) - 1]
        else:
            selected_rel = choice
        
        # arg2: label
        if len(sys.argv) > 2:
            label = sys.argv[2]
    
    if not selected_rel:
        print("\n" + "=" * 55)
        print("  Available .txt link files in html_files/:")
        print("=" * 55)
        for i, f in enumerate(txt_files, 1):
            print(f"  {i}. {f}")
        print("=" * 55)

        choice = input("\nEnter file number or full name: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(txt_files):
            selected_rel = txt_files[int(choice) - 1]
        else:
            selected_rel = choice

    txt_path = os.path.join(HTML_FILES_DIR, selected_rel)
    if not os.path.exists(txt_path):
        print(f"[ERROR] File not found: {txt_path}", flush=True)
        return
    if not os.path.isfile(txt_path):
        print(f"[ERROR] Selected path is not a file: {txt_path}", flush=True)
        return

    # Step 2: Read all post URLs
    with open(txt_path, "r", encoding="utf-8") as f:
        raw_lines = f.readlines()

    post_urls = []
    for line in raw_lines:
        url = line.strip()
        if url and url.startswith("http"):
            normalized = normalize_post_url(url)
            if normalized not in post_urls:
                post_urls.append(normalized)

    if not post_urls:
        print("[ERROR] No valid Instagram URLs found in the file.", flush=True)
        return

    print(f"\n[INFO] Found {len(post_urls)} post URLs to scrape.", flush=True)

    # Step 3: Optional label for output files
    if label is None:
        label = input("\nEnter a label/name for this scrape (e.g. Ashok Kharat, or press Enter to use filename): ").strip()
    
    if not label:
        label = os.path.splitext(os.path.basename(selected_rel))[0]

    # Step 4: Initialize driver
    print("\nStarting browser...", flush=True)
    driver = init_driver_with_cookies()

    # Step 6: Prepared Output Paths
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_label = re.sub(r"[^\w]", "_", label)
    
    # Create subfolder for this label inside instagram_data
    label_folder = os.path.join("..", "..", "data", "instagram_data", safe_label)
    os.makedirs(label_folder, exist_ok=True)
    
    base_name = f"{safe_label}_{timestamp_str}"
    json_path = os.path.join(label_folder, f"{base_name}.json")
    excel_path = os.path.join("..", "..", "data", "excel_data", f"{base_name}.xlsx")

    # Step 5: Scrape each post
    all_posts = []
    processed = set()

    for idx, post_url in enumerate(post_urls, 1):
        print(f"\n[{idx}/{len(post_urls)}] Scraping: {post_url}", flush=True)

        if post_url in processed:
            print("  Duplicate - skipping.", flush=True)
            continue
        processed.add(post_url)

        post_data = scrape_post(driver, post_url)
        all_posts.append(post_data)

        # INCREMENTAL SAVE: Update JSON after each post
        try:
            temp_result = {
                "label": label,
                "source_file": selected_rel,
                "scraped_at": timestamp_str,
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_posts_found": len(post_urls),
                "posts_scraped_so_far": len(all_posts),
                "posts": all_posts,
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(temp_result, f, indent=4, ensure_ascii=False)
            print(f"  [Progress Saved] {json_path}", flush=True)
        except Exception as e:
            print(f"  [WARNING] Incremental save failed: {e}", flush=True)

        random_sleep(2, 4)

    driver.quit()
    print("\nBrowser closed.", flush=True)

    # Final Summary Save (Excel)
    try:
        rows = []
        for post in all_posts:
            rows.append({
                "Label": label,
                "Post URL": post.get("post_url"),
                "Caption": post.get("caption"),
                "Likes": post.get("likes_count"),
                "Comments Count": post.get("comments_count"),
                "Timestamp": post.get("timestamp"),
                "Comments Text": (
                    post["comments"][0]["comment_text"]
                    if post.get("comments")
                    else ""
                ),
            })

        if rows:
            df = pd.DataFrame(rows)
            excel_path = os.path.join("..", "..", "data", "excel_data", f"{base_name}.xlsx")
            df.to_excel(excel_path, index=False)
            print(f"Excel saved: {excel_path}", flush=True)
    except Exception as e:
        print(f"Excel export failed: {e}", flush=True)

    print(f"\n[DONE] Scraped {len(all_posts)} posts from '{label}'.", flush=True)


if __name__ == "__main__":
    main()