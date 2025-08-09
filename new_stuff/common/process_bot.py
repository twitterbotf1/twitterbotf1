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
SCREENSHOT_DIR = Path(f"./debug_screenshots/{BOT_CATEGORY}")
HTML_DEBUG_DIR = Path(f"./debug_html/{BOT_CATEGORY}")
TEMP_OTP_DIR = Path(f"./{BOT_CATEGORY}/temp_otp_repo")
TIMEZONE = pytz.timezone("Asia/Kolkata")

# --- OTP Configuration ---
OTP_REPO_URL = "https://github.com/twitterbotf1/login_otps"
OTP_FILE_IN_REPO = Path(f"{BOT_CATEGORY}/otp.txt")
OTP_CHECK_TEXT = "check your email"
EXTRA_VERIFICATION_TEXT = "unusual login activity"


# --- Helper Function: take_shot ---
def take_shot(page: Page, name: str):
    """Saves a screenshot for debugging the entire process."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = SCREENSHOT_DIR / f"{name}.png"
    print(f"📸 Taking screenshot: {screenshot_path}")
    try:
        page.screenshot(path=screenshot_path)
    except Exception as e:
        print(f"⚠️ Could not take screenshot: {e}", file=sys.stderr)


# --- Helper Function: save_html ---
def save_html(page: Page, name: str):
    """Saves the current HTML of the page for debugging element attributes."""
    HTML_DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    html_path = HTML_DEBUG_DIR / f"{name}.html"
    print(f"📄 Saving HTML snapshot: {html_path}")
    try:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception as e:
        print(f"⚠️ Could not save HTML: {e}", file=sys.stderr)


# --- Helper Function: is_logged_in ---
def is_logged_in(page: Page):
    page.wait_for_timeout(5000)
    page_text = page.inner_text("body").lower()
    logged_in = "for you" in page_text or "following" in page_text or "home" in page_text
    print(f"🕵️‍♂️ Verification check: Is logged in? {logged_in}")
    return logged_in


# --- Sub-Process: Login ---
def perform_login(page: Page):
    """Contains the logic to perform a full, step-by-step login."""
    print("🚀 Starting full login process...")
    page.goto("https://x.com/login", timeout=60000)
    page.wait_for_timeout(5000)
    take_shot(page, "01_login_start")

    print("-> Typing email...")
    page.mouse.click(580, 350)
    page.keyboard.type(EMAIL)
    take_shot(page, "02_login_email_entered")
    page.mouse.click(640, 430)
    page.wait_for_timeout(5000)
    take_shot(page, "03_login_after_email_next")

    if EXTRA_VERIFICATION_TEXT in page.inner_text("body").lower():
        print("-> Extra verification needed. Entering username...")
        page.mouse.click(520, 320)
        page.keyboard.type(USERNAME)
        take_shot(page, "04_login_username_entered")
        page.mouse.click(640, 640)
        page.wait_for_timeout(5000)
        take_shot(page, "05_login_after_username_next")

    print("-> Typing password...")
    page.mouse.click(500, 300)
    page.keyboard.type(PASSWORD)
    take_shot(page, "06_login_password_entered")
    page.mouse.click(640, 590)
    page.wait_for_timeout(7000)
    take_shot(page, "07_login_after_password_click")

    if OTP_CHECK_TEXT in page.inner_text("body").lower():
        print("-> OTP screen detected. Halting for this version.")
        take_shot(page, "08_login_otp_failure")
        return False

    if not is_logged_in(page):
        print("❌ Login failed. Main feed was not visible.", file=sys.stderr)
        take_shot(page, "98_login_final_failure")
        return False
    
    print("✅ Full login successful.")
    take_shot(page, "09_login_final_success")
    return True


# --- Sub-Process: Tweeting ---
def perform_tweeting(page: Page, items_to_process: list):
    """Contains the logic for posting or scheduling tweets."""
    print("\n🚀 Starting tweeting process...")
    now_ist = datetime.now(TIMEZONE)
    post_now_threshold = now_ist + timedelta(minutes=5)

    for i, item in enumerate(items_to_process):
        title = item.get("title", "No Title")
        url = item.get("url")
        time_str = item.get("time")
        item_id = url.split('/')[-1] if url else f"item_{i}"

        if not url or not time_str:
            print(f"⚠️ Skipping item due to missing URL/time: '{title}'")
            continue

        print(f"\n--- Processing item {i+1}: '{title}' ---")
        tweet_text = f'"{title}"\n\n{url}'

        print("-> Clicking 'New Tweet' button...")
        page.locator('[data-testid="SideNav_NewTweet_Button"]').click()
        page.wait_for_timeout(3000)
        take_shot(page, f"10_tweet_{item_id}_new_tweet_clicked")

        # --- THIS IS THE NEW FIX ---
        # Click the textarea to make sure the cursor is active.
        print("-> Clicking tweet textarea to focus...")
        page.locator('[data-testid="tweetTextarea_0"]').click()
        page.wait_for_timeout(500) # Brief pause to ensure focus is set.

        # Use the page's keyboard to type directly, simulating a real user.
        print("-> Typing text using direct keyboard simulation...")
        page.keyboard.type(tweet_text, delay=30)
        # --- END OF NEW FIX ---

        take_shot(page, f"11_tweet_{item_id}_textarea_filled")
        
        print("-> Waiting for link preview card...")
        page.wait_for_timeout(7000)
        take_shot(page, f"12_tweet_{item_id}_link_preview")

        item_time = pytz.utc.localize(datetime.fromisoformat(time_str.replace("Z", ""))).astimezone(TIMEZONE)

        if item_time <= post_now_threshold:
            print("-> Attempting to POST NOW.")
            page.locator('[data-testid="tweetButton"]').click()
            take_shot(page, f"13_tweet_{item_id}_posted_now")
            print("✅ Tweet posted successfully.")
        else:
            print("-> Attempting to SCHEDULE.")
            page.locator('[data-testid="scheduleOption"]').click()
            page.wait_for_timeout(2000)
            take_shot(page, f"13_tweet_{item_id}_schedule_dialog_open")
            
            schedule_date = item_time.strftime("%Y-%m-%d")
            schedule_hour = item_time.strftime("%-I")
            schedule_minute = item_time.strftime("%M")
            schedule_ampm = item_time.strftime("%p")
            
            print("--> Filling schedule time...")
            page.locator('input[type="date"]').fill(schedule_date)
            page.select_option("select[aria-label='Hour']", schedule_hour)
            page.select_option("select[aria-label='Minute']", schedule_minute)
            page.select_option("select[aria-label='AM/PM']", schedule_ampm)
            take_shot(page, f"14_tweet_{item_id}_schedule_time_filled")

            print("--> Confirming schedule time...")
            page.locator('[data-testid="scheduledConfirmationPrimaryAction"]').click()
            page.wait_for_timeout(1000)
            take_shot(page, f"15_tweet_{item_id}_schedule_confirmed")
            
            print("--> Clicking final 'Schedule' button...")
            page.locator('[data-testid="tweetButton"]').click()
            take_shot(page, f"16_tweet_{item_id}_scheduled_final")
            print("✅ Tweet scheduled successfully.")
        
        print("-> Waiting 5 seconds before next item...")
        page.wait_for_timeout(5000)


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
            take_shot(page, "00_init_check_login")
            
            login_needed = "login" in page.url or not is_logged_in(page)

            if login_needed:
                print("⚠️ Session is invalid or expired. A full login is required.")
                if not perform_login(page):
                     raise Exception("Login failed, cannot proceed to tweeting.")
                save_html(page, "homepage_after_new_login")
            else:
                print("✅ Reused existing session successfully.")
                save_html(page, "homepage_after_reused_session")

            if items_to_process:
                perform_tweeting(page, items_to_process)
            else:
                print("ℹ️ No items in the data payload to tweet.")

            print(f"--- Session for bot '{BOT_CATEGORY}' finished successfully. ---")
            take_shot(page, "99_final_success")

        except Exception as e:
            print(f"❌ A critical error occurred during the session for '{BOT_CATEGORY}': {e}", file=sys.stderr)
            if 'page' in locals():
                take_shot(page, "99_CRITICAL_FAILURE")
                save_html(page, "page_on_failure")
            sys.exit(1)
        finally:
            if browser:
                browser.close()
            if TEMP_OTP_DIR.exists():
                shutil.rmtree(TEMP_OTP_DIR)

if __name__ == "__main__":
    main()
