import os
import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from playwright.sync_api import sync_playwright, Page
import git
from dotenv import load_dotenv

load_dotenv()

# --- Generic Configuration from Environment Variables ---
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")
USERNAME = os.getenv("TWITTER_USERNAME")
BOT_CATEGORY = os.getenv("BOT_CATEGORY")

# --- Paths & Directories ---
LOGIN_DATA_DIR = Path(f"./{BOT_CATEGORY}/login_data")
# Unified debug directory for logs, screenshots, and html
DEBUG_DIR = Path(f"./debug/{BOT_CATEGORY}")
TEMP_OTP_DIR = Path(f"./{BOT_CATEGORY}/temp_otp_repo")
TIMEZONE = pytz.timezone("Asia/Kolkata")

# --- OTP Configuration ---
OTP_REPO_URL = "https://github.com/twitterbotf1/login_otps"
OTP_FILE_IN_REPO = Path(f"{BOT_CATEGORY}/otp.txt")
OTP_CHECK_TEXT = "check your email"
EXTRA_VERIFICATION_TEXT = "unusual login activity"


# --- Unified Helper Function for Logging ---
def log_page(page: Page, name: str):
    """Saves a screenshot, HTML, and inner text for debugging."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    time.sleep(2) # Allow page to settle
    page.screenshot(path=DEBUG_DIR / f"{name}.png")
    (DEBUG_DIR / f"{name}.html").write_text(page.content(), encoding="utf-8")
    print(f"✅ Logged page state: {name}")


# --- Helper Function: is_logged_in ---
def is_logged_in(page: Page):
    page.wait_for_timeout(5000)
    page_text = page.inner_text("body").lower()
    logged_in = "for you" in page_text or "following" in page_text or "home" in page_text
    print(f"🕵️‍♂️ Verification check: Is logged in? {logged_in}")
    return logged_in


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

    if EXTRA_VERIFICATION_TEXT in page.inner_text("body").lower():
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
        print("❌ Login failed.", file=sys.stderr)
        log_page(page, "98_login_failure")
        return False

    print("✅ Full login successful.")
    log_page(page, "05_login_success")
    return True


# --- Sub-Process: Tweeting ---
def perform_tweeting(page: Page, items_to_process: list):
    print("\n🚀 Starting tweeting process...")
    now_ist = datetime.now(TIMEZONE)
    post_now_threshold = now_ist + timedelta(minutes=5)

    for i, item in enumerate(items_to_process):
        title = item.get("title", "No Title")
        url = item.get("url")
        time_str = item.get("time")

        if not url or not time_str:
            print(f"⚠️ Skipping item due to missing URL/time: '{title}'")
            continue

        print(f"\n--- Processing item {i+1}: '{title}' ---")
        tweet_text = f'"{title}"\n\n{url}'
        item_time = pytz.utc.localize(datetime.fromisoformat(time_str.replace("Z", ""))).astimezone(TIMEZONE)

        if item_time <= post_now_threshold:
            # --- EXECUTE "POST NOW" LOGIC ---
            print("-> Logic: Post Now (from main feed)")
            page.goto("https://x.com/home", wait_until="load") # Ensure we are on the home feed
            page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=15000)
            log_page(page, f"A_{i+1}_postnow_homepage_loaded")
            
            print("--> Typing tweet...")
            page.fill('div[data-testid="tweetTextarea_0"]', tweet_text)
            page.wait_for_timeout(3000) 
            log_page(page, f"B_{i+1}_postnow_tweet_typed")

            print("--> Clicking the Post button...")
            post_button = page.locator('button[data-testid="tweetButtonInline"]')
            post_button.click(timeout=10000)
            page.wait_for_timeout(5000)
            log_page(page, f"C_{i+1}_postnow_tweet_posted")
            print("✅ Tweet posted successfully!")

        else:
            # --- EXECUTE "SCHEDULE" LOGIC ---
            print("-> Logic: Schedule (from modal)")
            page.goto("https://twitter.com/home", wait_until="load") # Start from a clean slate on home
            page.wait_for_timeout(5000)
            log_page(page, f"A_{i+1}_schedule_home_loaded")

            print("--> Opening tweet composer...")
            page.click('[data-testid="SideNav_NewTweet_Button"]')
            page.wait_for_timeout(2000)
            log_page(page, f"B_{i+1}_schedule_composer_opened")

            print("--> Typing tweet...")
            page.fill('div[data-testid="tweetTextarea_0"]', tweet_text)
            log_page(page, f"C_{i+1}_schedule_text_filled")

            print("--> Opening schedule modal...")
            page.click("button[data-testid='scheduleOption']")
            page.wait_for_timeout(2000)
            log_page(page, f"D_{i+1}_schedule_modal_opened")

            # Set date/time from Supabase data
            schedule_date = item_time.strftime("%Y-%m-%d")
            hour = item_time.strftime("%I").lstrip("0")
            minute = item_time.strftime("%M")
            ampm = item_time.strftime("%p")
            print(f"--> Setting schedule: {schedule_date} {hour}:{minute} {ampm}")
            page.fill('input[type="date"]', schedule_date)
            page.select_option("select#SELECTOR_4", hour)
            page.select_option("select#SELECTOR_5", minute)
            page.select_option("select#SELECTOR_6", ampm)
            log_page(page, f"E_{i+1}_schedule_date_time_set")

            print("--> Confirming schedule modal...")
            page.click("button[data-testid='scheduledConfirmationPrimaryAction']")
            page.wait_for_timeout(3000)
            log_page(page, f"F_{i+1}_schedule_modal_confirmed")
            
            print("--> Finalizing tweet scheduling...")
            final_btn = page.locator('button[data-testid="tweetButton"]')
            final_btn.wait_for(state="visible", timeout=15000)
            final_btn.click(force=True, timeout=10000)
            page.wait_for_timeout(4000)
            log_page(page, f"G_{i+1}_schedule_tweet_scheduled_final")
            print("✅ Tweet successfully scheduled!")


# --- Main Orchestration ---
def main():
    if not all([EMAIL, PASSWORD, USERNAME, BOT_CATEGORY]):
        sys.exit("❌ FATAL: Credentials or BOT_CATEGORY environment variables not set.")
    if len(sys.argv) < 2:
        sys.exit("❌ FATAL: No data passed to the script.")

    try:
        items_to_process = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        sys.exit("❌ FATAL: Invalid JSON data passed to the script.")

    with sync_playwright() as p:
        browser = None
        try:
            print(f"--- Starting session for bot: '{BOT_CATEGORY}' ---")
            LOGIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LOGIN_DATA_DIR),
                headless=True,
                viewport={"width": 1280, "height": 800},
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            page = browser.new_page()

            page.goto("https://twitter.com/home", timeout=60000)
            log_page(page, "00_init_check_login")
            
            login_needed = "login" in page.url or not is_logged_in(page)

            if login_needed:
                print("⚠️ Session is invalid or expired. A full login is required.")
                if not perform_login(page):
                     raise Exception("Login failed, cannot proceed to tweeting.")
            else:
                print("✅ Reused existing session successfully.")

            if items_to_process:
                perform_tweeting(page, items_to_process)
            else:
                print("ℹ️ No items in the data payload to tweet.")

            print(f"--- Session for bot '{BOT_CATEGORY}' finished successfully. ---")
            log_page(page, "99_final_success")

        except Exception as e:
            print(f"❌ A critical error occurred during the session for '{BOT_CATEGORY}': {e}", file=sys.stderr)
            if 'page' in locals():
                log_page(page, "99_CRITICAL_FAILURE")
            sys.exit(1)
        finally:
            if browser:
                browser.close()
            if TEMP_OTP_DIR.exists():
                shutil.rmtree(TEMP_OTP_DIR)

if __name__ == "__main__":
    main()
