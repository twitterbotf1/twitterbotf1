import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from a .env file for local testing
load_dotenv()

# --- Configuration ---
# Reads the same secrets as the main controller
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def clear_table(supabase: Client):
    """Deletes all rows from the 'processed_urls' table."""
    try:
        print("Executing DELETE operation on 'processed_urls'...")
        
        # The .neq() filter is used to target all rows for deletion.
        # We select a column that always exists ('id') and provide a value that
        # will never be matched (-1), effectively selecting all rows to delete.
        supabase.table("processed_urls").delete().neq("id", -1).execute()
        
        print("-> Successfully sent delete request to Supabase.")

    except Exception as e:
        print(f"❌ An error occurred during table clearing: {e}", file=sys.stderr)
        sys.exit(1) # Exit with an error to signal failure to the workflow

def main():
    """Main function to connect and clear the table."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY environment variables are not set.", file=sys.stderr)
        sys.exit(1)
        
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    clear_table(supabase)
    print("✅ 'processed_urls' table clearing process finished.")

if __name__ == "__main__":
    main()
