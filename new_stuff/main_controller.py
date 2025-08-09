import os
import sys
import subprocess
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

load_dotenv()

BOT_CATEGORIES = ["formula", "tech", "hollywood", "movies", "unews", "news"]
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def fetch_data(supabase: Client):
    # [This function remains unchanged]
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
        sys.exit("❌ Error: Supabase environment variables not set.")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    all_data, source_table = fetch_data(supabase)

    # [The debug file saving logic remains unchanged]
    debug_dir = Path("debug_logs")
    debug_dir.mkdir(exist_ok=True)
    with open(debug_dir / "fetched_supabase_data.txt", 'w', encoding='utf-8') as f:
        json.dump(all_data, f, indent=4)

    if not all_data:
        print("No data to process. Exiting gracefully.")
        sys.exit(0)

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
        
        # --- SIMPLIFIED: Define path to the single, all-in-one script ---
        process_script_path = os.path.join("common", "process_bot.py")

        try:
            proc_env = os.environ.copy()
            proc_env["TWITTER_EMAIL"] = os.getenv(f"{category.upper()}_EMAIL")
            proc_env["TWITTER_USERNAME"] = os.getenv(f"{category.upper()}_USERNAME")
            proc_env["TWITTER_PASSWORD"] = os.getenv(f"{category.upper()}_PASSWORD")
            proc_env["BOT_CATEGORY"] = category

            if not all([proc_env["TWITTER_EMAIL"], proc_env["TWITTER_USERNAME"], proc_env["TWITTER_PASSWORD"]]):
                print(f"⚠️ Warning: Missing secrets for {category.upper()}. Skipping.")
                continue

            data_to_pass = json.dumps(categorized_data[category])
            
            # --- SIMPLIFIED: Run only the single process script ---
            print(f"Executing bot process for '{category}'...")
            subprocess.run(
                [sys.executable, process_script_path, data_to_pass], 
                check=True, env=proc_env, capture_output=True, text=True
            )
            print(f"✅ Bot process completed for '{category}'.")

        except subprocess.CalledProcessError as e:
            print(f"❌ An error occurred while processing category '{category}'. The script failed.", file=sys.stderr)
            print(f"Stdout of failed script:\n{e.stdout}", file=sys.stderr)
            print(f"Stderr of failed script:\n{e.stderr}", file=sys.stderr)
            print("Skipping to the next category.")
            continue

    print("\n--- Workflow finished ---")

if __name__ == "__main__":
    main()
