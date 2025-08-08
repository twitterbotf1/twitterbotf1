import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load .env file for local testing
load_dotenv()

# --- Paths & Configuration ---
SCRIPT_DIR = Path(__file__).parent
LOGIN_DATA_DIR = SCRIPT_DIR / "login_data"
TIMEZONE = pytz.timezone("Asia/Kolkata")


def main():
    """
    Processes and posts/schedules tweets for the 'formula' category.
    Receives data as a JSON string from the command line.
    """
    if len(sys.argv) < 2:
        print("❌ Error: No data passed to the tweet script.", file=sys.stderr)
        sys.exit(1)

    try:
        items_to_process = json.loads(sys.argv[1])
    except json.JSONDecodeError:
        print("❌ Error: Invalid JSON data passed to the tweet script.", file=sys.stderr)
        sys.exit(1)

    print(f"Received {len(items_to_process)} items to process for 'formula' bot.")

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(LOGIN_DATA_DIR),
            headless=True,
            viewport={"width": 1280, "height": 800}
        )
        page = browser.new_page()

        try:
            page.goto("https://twitter.com/home", wait_until="load")
            page.wait_for_timeout(5000)

            # --- Time Calculation ---
            now_ist = datetime.now(TIMEZONE)
            post_now_threshold = now_ist + timedelta(minutes=5)
            print(f"Current IST time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"'Post Now' threshold (until): {post_now_threshold.strftime('%Y-%m-%d %H:%M:%S')}")

            # --- Process each item ---
            for item in items_to_process:
                title = item.get("title", "No Title")
                url = item.get("url")
                time_str = item.get("time")

                if not url or not time_str:
                    print(f"⚠️ Skipping item due to missing URL or time: \"{title}\"")
                    continue

                print(f"\nProcessing: \"{title}\"")

                tweet_text = f'"{title}"\n\n{url}'

                page.locator('[data-testid="SideNav_NewTweet_Button"]').click()
                page.wait_for_timeout(2000)

                page.locator('[data-testid="tweetTextarea_0"]').fill(tweet_text)
                print("-> Waiting 7 seconds for link preview card to generate...")
                page.wait_for_timeout(7000)

                # --- Decision: Post Now or Schedule ---
                item_time = pytz.utc.localize(datetime.fromisoformat(time_str.replace("Z", ""))).astimezone(TIMEZONE)

                if item_time <= post_now_threshold:
                    # --- ACTION: Post Now ---
                    print(f"-> Time ({item_time.strftime('%H:%M')}) is within threshold. Posting now.")
                    page.locator('[data-testid="tweetButton"]').click()
                    print("✅ Tweet posted successfully.")
                else:
                    # --- ACTION: Schedule for Later ---
                    print(f"-> Time ({item_time.strftime('%H:%M')}) is in the future. Scheduling.")
                    page.locator('[data-testid="scheduleOption"]').click()
                    page.wait_for_timeout(2000)
                    
                    schedule_date = item_time.strftime("%Y-%m-%d")
                    schedule_hour = item_time.strftime("%-I")
                    schedule_minute = item_time.strftime("%M")
                    schedule_ampm = item_time.strftime("%p")
                    
                    page.locator('input[type="date"]').fill(schedule_date)
                    page.select_option("select[aria-label='Hour']", schedule_hour)
                    page.select_option("select[aria-label='Minute']", schedule_minute)
                    page.select_option("select[aria-label='AM/PM']", schedule_ampm)
                    
                    page.locator('[data-testid="scheduledConfirmationPrimaryAction"]').click()
                    page.wait_for_timeout(1000)
                    
                    page.locator('[data-testid="tweetButton"]').click()
                    print("✅ Tweet scheduled successfully.")
                
                page.wait_for_timeout(5000)
        
        except Exception as e:
            print(f"❌ A critical error occurred during the tweeting process: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            browser.close()

    print("\n'formula' bot tweet processing complete.")
    sys.exit(0)

if __name__ == "__main__":
    main()
