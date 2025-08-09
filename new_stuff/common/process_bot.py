import os
import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from playwright.sync_api import sync_playwright, Page
from dotenv import load_dotenv

# Import our new, separated logic
from tweeting_logic import post_now, schedule_post

load_dotenv()

# --- Generic Configuration ---
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")
USERNAME = os.getenv("TWITTER_USERNAME")
BOT_CATEGORY = os.getenv("BOT_CATEGORY")

# --- Paths & Directories ---
LOGIN_DATA_DIR = Path(f"./{BOT_CATEGORY}/login_data")
DEBUG_DIR = Path(f"./debug/{BOT_CATEGORY}")
TIMEZONE = pytz.timezone("Asia/Kolkata")


# --- Unified Helper Function for Logging ---
def log_page(page: Page, name: str):
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    time.sleep(2)
    page.screenshot(path=DEBUG_DIR / f"{name}.png")
    (DEBUG_DIR / f"{name}.html").write_text(page.content(), encoding="utf-8")
    print(f"✅ Logged page state: {name}")


# --- Helper Function: is_logged_in ---
def is_logged_in(page: Page):
    page.wait_for_timeout(5000)
    page_text = page.inner_text("body").lower()
    return "for you" in page_text or "following" in page_text

# --- Sub-Process: Login ---
def perform_login(page: Page):
    print("🚀 Starting full login process...")
    page.goto("https://x.com/login", timeout=60000)
    log_page(page, "01_login_start")
    page.mouse.click(580, 350)
    page.keyboard.type(EMAIL)
    page.mouse.click(640, 430)
    page.wait_for_timeout(5000)
    log_page(page, "02_login_after_email")
    if "unusual login" in page.inner_text("body").lower():
        page.mouse.click(520, 320)
        page.keyboard.type(USERNAME)
        page.mouse.click(640, 640)
        page.wait_for_timeout(5000)
        log_page(page, "03_login_after_username")
    page.mouse.click(500, 300)
    page.keyboard.type(PASSWORD)
    page.mouse.click(640, 590)
    page.wait_for_timeout(7000)
    log_page(page, "04_login_after_password")
    if not is_logged_in(page):
        log_page(page, "98_login_failure")
        return False
    print("✅ Full login successful.")
    log_page(page, "05_login_success")
    return True


# --- Main Orchestration ---
def main():
    if not all([EMAIL, PASSWORD, USERNAME, BOT_CATEGORY]):
        sys.exit("❌ FATAL: Credentials or BOT_CATEGORY not set.")
    if len(sys.argv) < 2:
        sys.exit("❌ FATAL: No data passed.")
    try:
        items_to_process = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        sys.exit("❌ FATAL: Invalid JSON data.")

    with sync_playwright() as p:
        browser = None
        try:
            print(f"--- Starting session for bot: '{BOT_CATEGORY}' ---")
            LOGIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LOGIN_DATA_DIR),
                headless=True,
                viewport={"width": 1280, "height": 800},
            )
            page = browser.new_page()
            page.goto("https://twitter.com/home", timeout=60000)
            log_page(page, "00_init_check_login")
            
            if "login" in page.url or not is_logged_in(page):
                print("⚠️ Session invalid. Performing full login.")
                if not perform_login(page):
                     raise Exception("Login failed, cannot proceed.")
            else:
                print("✅ Reused existing session successfully.")

            if not items_to_process:
                print("ℹ️ No items to process.")
            else:
                print("\n🚀 Starting tweeting process...")
                now_ist = datetime.now(TIMEZONE)
                post_now_threshold = now_ist + timedelta(minutes=5)

                for i, item in enumerate(items_to_process):
                    title = item.get("title", "No Title")
                    url = item.get("url")
                    time_str = item.get("time")
                    
                    if not url or not time_str:
                        print(f"⚠️ Skipping item {i+1} due to missing URL/time.")
                        continue

                    tweet_text = f'"{title}"\n\n{url}'
                    item_time = pytz.utc.localize(datetime.fromisoformat(time_str.replace("Z", ""))).astimezone(TIMEZONE)
                    item_id = f"{i+1}_{url.split('/')[-1]}"

                    if item_time <= post_now_threshold:
                        post_now(page, tweet_text, log_page, item_id)
                    else:
                        schedule_post(page, tweet_text, item_time, log_page, item_id)

            print(f"--- Session for bot '{BOT_CATEGORY}' finished successfully. ---")
            log_page(page, "99_final_success")

        except Exception as e:
            print(f"❌ A critical error occurred: {e}", file=sys.stderr)
            if 'page' in locals():
                log_page(page, "99_CRITICAL_FAILURE")
            sys.exit(1)
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    main()
