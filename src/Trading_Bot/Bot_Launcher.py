import schedule
import time
import subprocess
import os
import sys
# Get absolute path of this script
base_dir = os.path.dirname(os.path.abspath(__file__))

# Correct relative paths
FETCH_SCRIPT = os.path.join(base_dir, "Daily_Fund_Fetcher.py")
BOT_SCRIPT = os.path.join(base_dir, "Bot.py")
MERGE_SCRIPT = os.path.join(base_dir, "DataBase.py")

def run_all():
    print("\n🚀 Starting full bot sequence...")
    try:
        subprocess.run(["python", FETCH_SCRIPT], check=True)
        subprocess.run(["python", BOT_SCRIPT], check=True)
        subprocess.run(["python", MERGE_SCRIPT], check=True)
        print("✅ Sequence completed!")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during execution: {e}")

# Run every hour at 00 minutes
schedule.every().hour.at(":01").do(run_all)

print("🔁 Scheduler initialized. Waiting for execution times...")

# This loop keeps the script running continuously,
# checking every 10 seconds if it's time to run a scheduled job
while True:
    schedule.run_pending()  # Run any jobs that are due
    time.sleep(10)          # Wait a bit before checking again
