# --- BEFORE ---
# 5. Conditionally clear the 'processed_urls' table
if source_table == "processed_urls":
    print("\n--- Clearing 'processed_urls' table ---")
    try:
        # Call the dedicated script to perform this action safely
        clear_script_path = os.path.join("common", "clear_processed_table.py")
        subprocess.run([sys.executable, clear_script_path], check=True, env=os.environ.copy())
        print("✅ 'processed_urls' table has been cleared.")
    except Exception as e:
        print(f"❌ Failed to clear 'processed_urls' table: {e}", file=sys.stderr)

# --- AFTER ---
# 5. Conditionally clear the 'processed_urls' table
# if source_table == "processed_urls":
#     print("\n--- Clearing 'processed_urls' table ---")
#     try:
#         # Call the dedicated script to perform this action safely
#         clear_script_path = os.path.join("common", "clear_processed_table.py")
#         subprocess.run([sys.executable, clear_script_path], check=True, env=os.environ.copy())
#         print("✅ 'processed_urls' table has been cleared.")
#     except Exception as e:
#         print(f"❌ Failed to clear 'processed_urls' table: {e}", file=sys.stderr)```

### 2. Adapt the New Login Script

We will make the new login script generic and place it in the `common` directory. The main controller will then be updated to call this single script for all bots.

**Action 1: Create the new generic login script.**

Create a new file named `login.py` inside the `old_stuff/common/` directory with the following content. This version is adapted from your working script to be reusable for all bot categories.

**New File:** `old_stuff/common/login.py`

```python
import os
import sys
import shutil
import time
from pathlib import Path
from playwright.sync_api import sync_playwright
import git

# --- Credentials from Generic Environment Variables ---
EMAIL = os.getenv("TWITTER_EMAIL")
PASSWORD = os.getenv("TWITTER_PASSWORD")
USERNAME = os.getenv("TWITTER_USERNAME")
BOT_CATEGORY = os.getenv("BOT_CATEGORY") # e.g., "formula", "tech"

# --- Directory and Repository Setup ---
LOGIN_DATA_DIR = Path(f"./{BOT_CATEGORY}/login_data")
SCREENSHOT_DIR = Path(f"./debug_screenshots/{BOT_CATEGORY}")
TEMP_OTP_DIR = Path(f"./{BOT_CATEGORY}/temp_otp_repo")
LOGIN_DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

# --- OTP Configuration ---
OTP_REPO_URL = "https://github.com/twitterbotf1/login_otps"
OTP_FILE_IN_REPO = Path(f"{BOT_CATEGORY}/otp.txt")
OTP_CHECK_TEXT = "check your email"
EXTRA_VERIFICATION_TEXT = "unusual login activity"

# --- Helper Functions ---
def take_shot(page, name):
    screenshot_path = SCREENSHOT_DIR / f"{name}.png"
    print(f"📸 Taking screenshot: {screenshot_path}")
    try:
        page.screenshot(path=screenshot_path)
    except Exception as e:
        print(f"⚠️ Could not take screenshot: {e}", file=sys.stderr)

def get_otp_from_repo():
    for attempt in range(3):
        print(f"OTP Attempt {attempt + 1} of 3.")
        print("...Waiting 2 minutes for manual OTP update...")
        time.sleep(120)
        try:
            if TEMP_OTP_DIR.exists():
                shutil.rmtree(TEMP_OTP_DIR)
            print(f"...Cloning repository from {OTP_REPO_URL}")
            git.Repo.clone_from(OTP_REPO_URL, str(TEMP_OTP_DIR))
            otp_file_path = TEMP_OTP_DIR / OTP_FILE_IN_REPO
            if otp_file_path.is_file():
                otp_code = otp_file_path.read_text().strip()
                if otp_code:
                    print("✅ OTP code found in repository.")
                    return otp_code
            else:
                 print(f"...Cloned repo, but file '{OTP_FILE_IN_REPO}' not found.")
        except Exception as e:
            print(f"⚠️ An error occurred during git clone/read on attempt {attempt + 1}: {e}", file=sys.stderr)
    print("❌ All 3 attempts to fetch OTP from the repository failed.", file=sys.stderr)
    return None

def is_logged_in(page):
    page.wait_for_timeout(5000)
    page_text = page.inner_text("body").lower()
    logged_in = "home" in page_text or "post" in page_text
    print(f"🕵️‍♂️ Verification check: Is 'Home' or 'Post' visible? {logged_in}")
    return logged_in

# --- Main Login Function ---
def main():
    if not all([EMAIL, USERNAME, PASSWORD, BOT_CATEGORY]):
        print("❌ Error: Credentials or BOT_CATEGORY were not provided via environment variables.", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = None
        try:
            print("🚀 Launching browser for a headless login...")
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LOGIN_DATA_DIR),
                headless=True,
                viewport={"width": 1280, "height": 720}
            )
            page = browser.new_page()
            page.goto("https://x.com/login")
            page.wait_for_timeout(5000)
            take_shot(page, "01_start_page")

            print("Typing email...")
            page.mouse.click(580, 350)
            page.keyboard.type(EMAIL)
            take_shot(page, "02_email_entered")

            print("Clicking 'Next' after email...")
            page.mouse.click(640, 430)
            page.wait_for_timeout(5000)
            take_shot(page, "03_after_email_next")

            if EXTRA_VERIFICATION_TEXT in page.inner_text("body").lower():
                print("🔹 Extra verification step detected. Entering username.")
                page.mouse.click(520, 320)
                page.keyboard.type(USERNAME)
                take_shot(page, "04_extra_username_entered")
                print("Clicking 'Next' after username...")
                page.mouse.click(640, 640)
                page.wait_for_timeout(5000)
                take_shot(page, "05_after_username_next")

            print("Typing password...")
            page.mouse.click(500, 300)
            page.keyboard.type(PASSWORD)
            take_shot(page, "06_password_entered")

            print("Clicking final 'Login' button...")
            page.mouse.click(640, 590)
            page.wait_for_timeout(7000)
            take_shot(page, "07_after_password_login_click")

            if OTP_CHECK_TEXT in page.inner_text("body").lower():
                print("-> OTP screen detected. Starting OTP retrieval process...")
                take_shot(page, "08a_otp_screen_detected")
                otp_code = get_otp_from_repo()
                if otp_code:
                    print(f"✅ OTP found. Entering it now.")
                    page.mouse.click(550, 350)
                    page.keyboard.type(otp_code)
                    take_shot(page, "08b_otp_entered")
                    print("Clicking 'Next' after OTP...")
                    page.mouse.click(640, 640)
                    page.wait_for_timeout(7000)
                    take_shot(page, "08c_after_otp_next_click")
                else:
                    print("❌ OTP retrieval process failed after multiple attempts.", file=sys.stderr)
                    take_shot(page, "98_otp_failure")
                    sys.exit(1)

            if is_logged_in(page):
                print("✅ Login successful. Main feed is visible.")
                take_shot(page, "10_final_success")
            else:
                print("❌ Login failed. Main feed was not visible.", file=sys.stderr)
                take_shot(page, "99_final_failure")
                sys.exit(1)

        except Exception as e:
            print(f"❌ A critical error occurred during login: {e}", file=sys.stderr)
            if 'page' in locals():
                take_shot(page, "99_exception_failure")
            sys.exit(1)
        finally:
            if browser:
                browser.close()
            if TEMP_OTP_DIR.exists():
                shutil.rmtree(TEMP_OTP_DIR)
                print("🧹 Cleaned up temporary OTP directory.")

if __name__ == "__main__":
    main()
