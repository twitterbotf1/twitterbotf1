import os
import sys
import subprocess
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path # <-- NEW: Import Path
from datetime import datetime # <-- NEW: Import datetime

# Load environment variables from a .env file if it exists
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
    """Main controller function to orchestrate the entire workflow."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables are not set.", file=sys.stderr)
        sys.exit(1)
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_data, source_table = fetch_data(supabase)

    # --- NEW DEBUGGING STEP ---
    # This block saves the fetched data to a file before doing anything else.
    print("\n📝 Saving fetched data to a debug file...")
    debug_dir = Path("debug_logs")
    debug_dir.mkdir(exist_ok=True)
    debug_file_path = debug_dir / "fetched_supabase_data.txt"

    with open(debug_file_path, 'w', encoding='utf-8') as f:
        f.write(f"--- Supabase Data Fetch Log ---\n")
        f.write(f"Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"Source Table: {source_table or 'None'}\n")
        f.write("-------------------------------------\n\n")

        if all_data:
            f.write("Data Fetched:\n")
            # Use json.dump for pretty-printing the data
            json.dump(all_data, f, indent=4)
            print(f"✅ Successfully wrote {len(all_data)} rows to {debug_file_path}")
        else:
            f.write("Result: No data was fetched from either 'processed_urls' or 'to_process'.\n")
            print(f"✅ Wrote 'no data' message to {debug_file_path}")
    # --- END OF NEW DEBUGGING STEP ---

    if not all_data:
        print("\nNo data to process. Exiting gracefully.")
        sys.exit(0)

    # 3. Categorize the fetched data
    print("\nCategorizing data...")
    categorized_data = {bot: [] for bot in BOT_CATEGORIES}
    for row in all_data:
        bot_tag = row.get("bot")
        if bot_tag in categorized_data:
            categorized_data[bot_tag].append(row)

    # 4. Loop through each category and process it
    print("\n--- Starting Bot Processing Loop ---")
    for category in BOT_CATEGORIES:
        if not categorized_data[category]:
            print(f"\nSkipping category '{category}': No data found.")
            continue

        print(f"\n--- Processing category: {category} ---")
        
        login_script_path = os.path.join("common", "login.py")
        tweet_script_path = os.path.join("common", "tweet.py")

        try:
            proc_env = os.environ.copy()
            proc_env["TWITTER_EMAIL"] = os.getenv(f"{category.upper()}_EMAIL")
            proc_env["TWITTER_USERNAME"] = os.getenv(f"{category.upper()}_USERNAME")
            proc_env["TWITTER_PASSWORD"] = os.getenv(f"{category.upper()}_PASSWORD")
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
            print(f"❌ Error: A script was not found.", file=sys.stderr)
            continue

    # 5. Table clearing logic is still disabled
    # ...

    print("\n--- Workflow finished ---")

if __name__ == "__main__":
    main()
