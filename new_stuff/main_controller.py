import os
import sys
import subprocess
import json
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
BOT_CATEGORIES = ["formula", "tech", "hollywood", "movies", "unews", "news"]
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def fetch_data(supabase: Client):
    source_table = None
    data = []
    print("Attempting to fetch data from 'processed_urls'...")
    response_processed = supabase.table("processed_urls").select("*").execute()
    if response_processed.data:
        print("✅ Data found in 'processed_urls'.")
        data = response_processed.data
        source_table = "processed_urls"
    else:
        print("ℹ️ 'processed_urls' is empty. Falling back to 'to_process'.")
        response_to_process = supabase.table("to_process").select("*").execute()
        if response_to_process.data:
            print("✅ Data found in 'to_process'.")
            data = response_to_process.data
            source_table = "to_process"
        else:
            print("ℹ️ Both 'processed_urls' and 'to_process' are empty.")
    return data, source_table

def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables are not set.", file=sys.stderr)
        sys.exit(1)
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_data, source_table = fetch_data(supabase)

    if not all_data:
        print("No data to process. Exiting gracefully.")
        sys.exit(0)

    print("\nCategorizing data...")
    categorized_data = {bot: [] for bot in BOT_CATEGORIES}
    for row in all_data:
        bot_tag = row.get("bot")
        if bot_tag in categorized_data:
            categorized_data[bot_tag].append(row)

    print("\n--- Starting Bot Processing Loop ---")
    for category in BOT_CATEGORIES:
        if not categorized_data[category]:
            print(f"\nSkipping category '{category}': No data found.")
            continue

        print(f"\n--- Processing category: {category} ---")
        
        # --- MODIFIED: Use the single common login script ---
        login_script_path = os.path.join("common", "login.py")
        tweet_script_path = os.path.join(category, "tweet.py")

        try:
            proc_env = os.environ.copy()
            proc_env["TWITTER_EMAIL"] = os.getenv(f"{category.upper()}_EMAIL")
            proc_env["TWITTER_USERNAME"] = os.getenv(f"{category.upper()}_USERNAME")
            proc_env["TWITTER_PASSWORD"] = os.getenv(f"{category.upper()}_PASSWORD")
            # --- ADDED: Pass the bot's category name to the login script ---
            proc_env["BOT_CATEGORY"] = category

            if not all([proc_env["TWITTER_EMAIL"], proc_env["TWITTER_USERNAME"], proc_env["TWITTER_PASSWORD"]]):
                print(f"⚠️ Warning: Missing one or more secrets for {category.upper()}. Skipping category.")
                continue

            print(f"Executing login for '{category}'...")
            subprocess.run([sys.executable, login_script_path], check=True, env=proc_env, capture_output=True, text=True)
            print(f"✅ Login successful for '{category}'.")

            print(f"Executing tweeting for '{category}'...")
            data_to_pass = json.dumps(categorized_data[category])
            subprocess.run([sys.executable, tweet_script_path, data_to_pass], check=True, env=proc_env, capture_output=True, text=True)
            print(f"✅ Tweeting process completed for '{category}'.")

        except subprocess.CalledProcessError as e:
            print(f"❌ An error occurred while processing category '{category}'. The script failed.", file=sys.stderr)
            print(f"Stderr of failed script:\n{e.stderr}", file=sys.stderr)
            print("Skipping to the next category.")
            continue
        except FileNotFoundError:
            print(f"❌ Error: Script not found for category '{category}'. Make sure paths are correct.", file=sys.stderr)
            continue

    # --- DISABLED: The table clearing logic is now commented out ---
    # if source_table == "processed_urls":
    #     print("\n--- Clearing 'processed_urls' table ---")
    #     try:
    #         clear_script_path = os.path.join("common", "clear_processed_table.py")
    #         subprocess.run([sys.executable, clear_script_path], check=True, env=os.environ.copy())
    #         print("✅ 'processed_urls' table has been cleared.")
    #     except Exception as e:
    #         print(f"❌ Failed to clear 'processed_urls' table: {e}", file=sys.stderr)

    print("\n--- Workflow finished ---")

if __name__ == "__main__":
    main()
