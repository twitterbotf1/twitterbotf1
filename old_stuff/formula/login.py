import os
import sys
import time
import subprocess
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Playwright
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
EMAIL = os.getenv("TWITTER_EMAIL")
USERNAME = os.getenv("TWITTER_USERNAME")
PASSWORD = os.getenv("TWITTER_PASSWORD")

# --- Correct URL for your public OTP repository ---
OTP_REPO_URL = "https://github.com/twitterbotf1/login_otps.git"

# --- Paths ---
BOT_NAME = Path(__file__).parent.name
DEBUG_DIR = Path(__file__).parents[1] / "debug_screenshots" / BOT_NAME
LOGIN_DATA_DIR = Path(__file__).parent / "login_data"
TEMP_OTP_DIR = Path(__file__).parent / "temp_otp_repo"

# Ensure directories exist
LOGIN_DATA_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# --- Constants ---
CHECK_TEXT = "Enter your phone number or username"
OTP_CHECK_TEXT = "check your email"

def take_shot(page: Page, name: str):
    """Saves a screenshot for debugging."""
    page.screenshot(path=DEBUG_DIR / f"{name}.png")
    print(f"-> Screenshot saved: {name}.png")

def is_logged_in(page: Page) -> bool:
    """Checks if the page shows a logged-in state."""
    page.wait_for_timeout(4000)
    return page.locator('[data-testid="primaryColumn"]').is_visible()

def get_otp_from_repo() -> str:
    """Clones the OTP repo and reads the code from the correct otp.txt file."""
    if TEMP_OTP_DIR.exists():
        shutil.rmtree(TEMP_OTP_DIR) # Clean up old clone

    try:
        # Clone the public repo
        subprocess.run(
            ["git", "clone", "--depth", "1", OTP_REPO_URL, str(TEMP_OTP_DIR)],
            check=True, capture_output=True, text=True
        )
        
        # --- CORRECTED: Looking for 'otp.txt' as requested ---
        otp_file = TEMP_OTP_DIR / BOT_NAME / "otp.txt"
        if otp_file.exists():
            return otp_file.read_text().strip()
            
    except subprocess.CalledProcessEror as e:
        print(f"❌ Failed to clone OTP repo: {e.stderr}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"❌ An error occurred checking for OTP: {e}", file=sys.stderr)
        return ""
    
    return ""

def perform_full_login(p: Playwright) -> bool:
    """Performs a full login, polling for OTP if needed."""
    print("🚀 Performing a full, step-by-step login...")
    browser = None
    try:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(LOGIN_DATA_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800}
        )
        page = browser.new_page()

        page.goto("https://twitter.com/login")
        page.wait_for_timeout(5000)
        take_shot(page, "01_start_page")

        page.locator('input[name="text"]').fill(EMAIL)
        page.wait_for_timeout(1000)
        take_shot(page, "02_email_entered")

        page.locator("text=Next").click()
        page.wait_for_timeout(3000)
        take_shot(page, "03_after_email_next")

        if CHECK_TEXT in page.inner_text("body"):
            print("🔹 Extra verification detected. Entering username.")
            page.locator('input[name="text"]').fill(USERNAME)
            page.wait_for_timeout(1000)
            take_shot(page, "04_extra_username_entered")
            page.locator("text=Next").click()
            page.wait_for_timeout(3000)
            take_shot(page, "05_after_username_next")

        page.locator('input[name="password"]').fill(PASSWORD)
        page.wait_for_timeout(1000)
        take_shot(page, "06_password_entered")

        page.locator('[data-testid="LoginForm_Login_Button"]').click()
        page.wait_for_timeout(7000)
        take_shot(page, "07_after_password_login_click")

        # --- OTP Polling Logic ---
        if OTP_CHECK_TEXT in page.inner_text("body").lower():
            print(f"-> OTP screen detected for bot '{BOT_NAME}'.")
            take_shot(page, "08a_otp_screen_detected")
            
            otp_code = ""
            for i in range(5): 
                print(f"-> Checking remote repo for OTP... (Attempt {i+1}/5)")
                otp_code = get_otp_from_repo()
                
                if otp_code:
                    print(f"✅ OTP found in remote repo: {otp_code}")
                    break
                else:
                    if i < 4:
                        print("-> OTP not found. Waiting 60 seconds...")
                        time.sleep(60)
            
            if otp_code:
                print("-> Entering OTP...")
                page.mouse.click(480, 380)
                page.keyboard.type(otp_code)
                take_shot(page, "08b_otp_entered")

                print("-> Clicking Next button after OTP...")
                page.mouse.click(650, 670)
                page.wait_for_timeout(7000)
                take_shot(page, "08c_after_otp_next_click")
            else:
                print(f"❌ Timed out waiting for OTP for '{BOT_NAME}'.", file=sys.stderr)
                take_shot(page, "98_otp_timeout_failure")
                return False

        if is_logged_in(page):
            print("✅ Full login successful.")
            return True
        else:
            print("❌ Full login failed.", file=sys.stderr)
            take_shot(page, "99_login_failed")
            return False

    except Exception as e:
        if 'page' in locals():
             take_shot(page, "99_exception")
        print(f"❌ An error occurred during the login process: {e}", file=sys.stderr)
        return False
    finally:
        if browser:
            if TEMP_OTP_DIR.exists():
                shutil.rmtree(TEMP_OTP_DIR)
            browser.close()

def main():
    if not all([EMAIL, USERNAME, PASSWORD]):
        print("❌ Error: Twitter credentials not set.", file=sys.stderr)
        sys.exit(1)
        
    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LOGIN_DATA_DIR),
                headless=True
            )
            page = browser.new_page()
            print("Checking for existing valid session...")
            page.goto("https://twitter.com/home", wait_until="load")
            take_shot(page, "00_check_existing_session")

            if is_logged_in(page):
                print("✅ Reused existing session successfully.")
                sys.exit(0)
            else:
                print("⚠️ Session not valid or expired. Starting full login.")
                browser.close()
                success = perform_full_login(p)
                if success:
                    sys.exit(0)
                else:
                    sys.exit(1)
        except Exception as e:
            print(f"❌ A critical error occurred in login check: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            if browser:
                browser.close()

if __name__ == "__main__":
    main()
