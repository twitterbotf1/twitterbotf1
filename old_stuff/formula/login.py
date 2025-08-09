# old_stuff/formula/login.py:

import os
import sys
import time # Added for waiting
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Playwright
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
EMAIL = os.getenv("TWITTER_EMAIL")
USERNAME = os.getenv("TWITTER_USERNAME")
PASSWORD = os.getenv("TWITTER_PASSWORD")

# --- Paths ---
# Save screenshots in a top-level folder for easy access in the repo
DEBUG_DIR = Path(__file__).parents[1] / "debug_screenshots" / "formula"
LOGIN_DATA_DIR = Path(__file__).parent / "login_data"
# Path to the OTP verification file at the project root
VERI_FILE_PATH = Path(__file__).parents[2] / "veri.txt"

# Ensure directories exist
LOGIN_DATA_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

# --- Constants ---
CHECK_TEXT = "Enter your phone number or username"
OTP_CHECK_TEXT = "check your email" # Text to look for on the OTP page

def take_shot(page: Page, name: str):
    """Saves a screenshot for debugging."""
    page.screenshot(path=DEBUG_DIR / f"{name}.png")
    print(f"-> Screenshot saved: {name}.png")

def is_logged_in(page: Page) -> bool:
    """Checks if the page shows a logged-in state."""
    page.wait_for_timeout(4000)
    return page.locator('[data-testid="primaryColumn"]').is_visible()

def perform_full_login(p: Playwright) -> bool:
    """Performs a full login, screenshotting every step."""
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

        # --- NEW OTP HANDLING LOGIC ---
        if OTP_CHECK_TEXT in page.inner_text("body").lower():
            print(f"-> OTP screen detected. Looking for text: '{OTP_CHECK_TEXT}'")
            take_shot(page, "08a_otp_screen_detected")
            
            otp_code = ""
            for i in range(5): # Loop 5 times (total 5 minutes)
                print(f"-> Checking 'veri.txt' for OTP... (Attempt {i+1}/5)")
                if VERI_FILE_PATH.exists() and VERI_FILE_PATH.read_text().strip():
                    otp_code = VERI_FILE_PATH.read_text().strip()
                    print(f"✅ OTP found in 'veri.txt': {otp_code}")
                    break
                else:
                    if i < 4: # Don't wait after the last attempt
                        print("-> 'veri.txt' is empty. Waiting for 60 seconds.")
                        time.sleep(60)
            
            if otp_code:
                print("-> Entering OTP...")
                page.mouse.click(480, 380) # Click on the OTP text box
                page.keyboard.type(otp_code)
                page.wait_for_timeout(1000)
                take_shot(page, "08b_otp_entered")

                print("-> Clicking Next button after OTP...")
                page.mouse.click(650, 670) # Click on the Next button
                page.wait_for_timeout(7000)
                take_shot(page, "08c_after_otp_next_click")
            else:
                print("❌ Timed out waiting for OTP in 'veri.txt' after 5 minutes.", file=sys.stderr)
                take_shot(page, "98_otp_timeout_failure")
                return False # Exit login process if OTP times out
        # --- END OF OTP HANDLING LOGIC ---

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
            browser.close()

def main():
    if not all([EMAIL, USERNAME, PASSWORD]):
        print("❌ Error: Twitter credentials not set.", file=sys.stderr)
        sys.exit(1)
    with sync_playwright() as p:
        browser = None
        try:
            # Ensure the veri.txt file is empty before starting
            if VERI_FILE_PATH.exists():
                VERI_FILE_PATH.write_text("")
                print("-> Cleared 'veri.txt' for the new session.")

            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LOGIN_DATA_DIR),
                headless=True
            )
            page = browser.new_page()
            print("Checking for existing valid session...")
            page.goto("https://twitter.com/home", wait_until="load")
            take_shot(page, "00_check_existing_session") # Screenshot of initial check

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
