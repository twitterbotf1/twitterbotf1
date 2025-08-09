from playwright.sync_api import Page
import time

def post_now(page: Page, tweet_text: str, log_func, item_id: str):
    """
    Posts a tweet immediately from the main feed.
    Based on your verified post_now script.
    """
    print("-> Logic: Post Now (from main feed)")
    page.goto("https://x.com/home", wait_until="load")
    page.wait_for_selector('div[data-testid="tweetTextarea_0"]', timeout=15000)
    log_func(page, f"A_{item_id}_postnow_homepage_loaded")
    
    print("--> Typing tweet...")
    page.fill('div[data-testid="tweetTextarea_0"]', tweet_text)
    time.sleep(3)
    log_func(page, f"B_{item_id}_postnow_tweet_typed")

    print("--> Clicking the Post button...")
    post_button = page.locator('button[data-testid="tweetButtonInline"]')
    post_button.click(timeout=10000)
    time.sleep(5)
    log_func(page, f"C_{item_id}_postnow_tweet_posted")
    print("✅ Tweet posted successfully!")

def schedule_post(page: Page, tweet_text: str, item_time, log_func, item_id: str):
    """
    Schedules a tweet using the composer modal.
    Based on your verified schedule script.
    """
    print("-> Logic: Schedule (from modal)")
    page.goto("https://twitter.com/home", wait_until="load")
    time.sleep(5)
    log_func(page, f"A_{item_id}_schedule_home_loaded")

    print("--> Opening tweet composer...")
    page.click('[data-testid="SideNav_NewTweet_Button"]')
    time.sleep(2)
    log_func(page, f"B_{item_id}_schedule_composer_opened")

    print("--> Typing tweet...")
    page.fill('div[data-testid="tweetTextarea_0"]', tweet_text)
    log_func(page, f"C_{item_id}_schedule_text_filled")

    print("--> Opening schedule modal...")
    page.click("button[data-testid='scheduleOption']")
    time.sleep(2)
    log_func(page, f"D_{item_id}_schedule_modal_opened")

    # Set date/time from Supabase data
    schedule_date = item_time.strftime("%Y-%m-%d")
    hour = item_time.strftime("%I").lstrip("0") or "12" # Handle midnight
    minute = item_time.strftime("%M")
    ampm = item_time.strftime("%p")
    print(f"--> Setting schedule: {schedule_date} {hour}:{minute} {ampm}")
    page.fill('input[type="date"]', schedule_date)
    page.select_option("select#SELECTOR_4", hour)
    page.select_option("select#SELECTOR_5", minute)
    page.select_option("select#SELECTOR_6", ampm)
    log_func(page, f"E_{item_id}_schedule_date_time_set")

    print("--> Confirming schedule modal...")
    page.click("button[data-testid='scheduledConfirmationPrimaryAction']")
    time.sleep(3)
    log_func(page, f"F_{item_id}_schedule_modal_confirmed")
    
    print("--> Finalizing tweet scheduling...")
    final_btn = page.locator('button[data-testid="tweetButton"]')
    final_btn.wait_for(state="visible", timeout=15000)
    final_btn.click(force=True, timeout=10000)
    time.sleep(4)
    log_func(page, f"G_{item_id}_schedule_tweet_scheduled_final")
    print("✅ Tweet successfully scheduled!")
