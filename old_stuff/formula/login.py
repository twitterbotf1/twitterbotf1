import os
import sys
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

# Ensure directories exist
LOGIN_DATA_DIR.mkdir(exist_ok=True)
DEBUG_DIR.mkdir(parents=True, exist_ok=True)

CHECK_TEXT = "Enter your phone number or username"

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
        take_shot(page, "07_after_final_login_click")

        if is_logged_in(page):
            print("✅ Full login successful.")
            return True
        else:
            print("❌ Full login failed.", file=sys.stderr)
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
