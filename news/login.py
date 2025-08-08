import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, Playwright
from dotenv import load_dotenv

# Load .env file for local testing
load_dotenv()

# --- Configuration ---
EMAIL = os.getenv("TWITTER_ne_EMAIL")
USERNAME = os.getenv("TWITTER_ne_USERNAME")
PASSWORD = os.getenv("TWITTER_ne_PASSWORD")

# --- Paths ---
SCRIPT_DIR = Path(__file__).parent
LOGIN_DATA_DIR = SCRIPT_DIR / "login_data"

# Ensure login data directory exists
LOGIN_DATA_DIR.mkdir(exist_ok=True)

# This text helps detect if Twitter is asking for username verification
CHECK_TEXT = "Enter your phone number or username"


def is_logged_in(page: Page) -> bool:
    """Checks if the page shows a logged-in state by looking for the main timeline."""
    page.wait_for_timeout(4000)
    timeline_visible = page.locator('[data-testid="primaryColumn"]').is_visible()
    return timeline_visible


def perform_full_login(p: Playwright) -> bool:
    """Performs a full, from-scratch login flow. Returns True on success, False on failure."""
    print("🚀 Performing a full, step-by-step login...")
    browser = None
    try:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(LOGIN_DATA_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800}
        )
        page = browser.new_page()

        # Step 1: Go to login page
        page.goto("https://twitter.com/login")
        page.wait_for_timeout(5000)

        # Step 2: Enter Email
        page.locator('input[name="text"]').fill(EMAIL)
        page.wait_for_timeout(1000)
        page.locator("text=Next").click()
        page.wait_for_timeout(3000)

        # Step 3: Handle extra verification check
        if CHECK_TEXT in page.inner_text("body"):
            print("🔹 Extra verification detected. Entering username.")
            page.locator('input[name="text"]').fill(USERNAME)
            page.wait_for_timeout(1000)
            page.locator("text=Next").click()
            page.wait_for_timeout(3000)

        # Step 4: Enter Password
        page.locator('input[name="password"]').fill(PASSWORD)
        page.wait_for_timeout(1000)
        page.locator('[data-testid="LoginForm_Login_Button"]').click()
        page.wait_for_timeout(7000)

        # Step 5: Final Check
        if is_logged_in(page):
            print("✅ Full login successful. Session data has been saved.")
            return True
        else:
            print("❌ Full login failed after entering credentials.", file=sys.stderr)
            return False

    except Exception as e:
        print(f"❌ An error occurred during the login process: {e}", file=sys.stderr)
        return False
    finally:
        if browser:
            browser.close()


def main():
    """Main function to ensure a valid login session exists."""
    if not all([EMAIL, USERNAME, PASSWORD]):
        print("❌ Error: TWITTER_EMAIL, USERNAME, and PASSWORD must be set in secrets.", file=sys.stderr)
        sys.exit(1)

    with sync_playwright() as p:
        browser = None
        try:
            # First, try to reuse the existing session.
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(LOGIN_DATA_DIR),
                headless=True
            )
            page = browser.new_page()
            print("Checking for existing valid session...")
            page.goto("https://twitter.com/home", wait_until="load")

            if is_logged_in(page):
                print("✅ Reused existing session successfully.")
                sys.exit(0)
       
