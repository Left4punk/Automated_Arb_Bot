import requests
import pandas as pd
import time
import os
import sys
import shutil
import tempfile
from datetime import datetime, timedelta, timezone

# Configuration for Binance endpoints and symbol
symbol = "BTCUSDT"
limit = 1000
funding_url = "https://fapi.binance.com/fapi/v1/fundingRate"
kline_url = "https://fapi.binance.com/fapi/v1/markPriceKlines"

# Resolve absolute path to data directory relative to the script
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
csv_path = os.path.join(base_dir, "data", "binance_btcusdt_funding_live.csv")
temp_csv_path = os.path.join(tempfile.gettempdir(), "temp_binance_funding.csv")

# Load existing data to prevent duplications in results
if os.path.exists(csv_path):
    # Read existing CSV and find the most recent timestamp
    try:
        df_existing = pd.read_csv(csv_path, parse_dates=['timestamp'], decimal=',')
        last_timestamp = df_existing['timestamp'].max()
        
        # Convert last_timestamp to UTC to ensure consistent timezone handling
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
        
        # IMPORTANT CHANGE: Use the latest timestamp we have as the start time
        # without adding 8 hours, to ensure we catch any already published rates
        funding_timestamp_unix = int(last_timestamp.timestamp() * 1000)
        start_time = funding_timestamp_unix + 1  # Add 1 ms to avoid duplicate
        
        print(f"Last funding timestamp: {last_timestamp} UTC")
        
        # Check if there should be a new funding rate by now (still calculate next expected for info)
        next_funding_time = last_timestamp + timedelta(hours=8)
        print(f"Next expected funding 8 hours later: {next_funding_time} UTC")
    except Exception as e:
        print(f"Error reading existing CSV: {e}")
        # If there's an error reading the file, start from 24 hours ago
        current_time_utc = datetime.now(timezone.utc)
        start_time = int((current_time_utc - timedelta(hours=24)).timestamp() * 1000)
        print("Error with existing data, starting from 24 hours ago")
else:
    # Initialize new DataFrame if no file exists and set start time to 24 hours ago
    df_existing = pd.DataFrame()
    current_time_utc = datetime.now(timezone.utc)
    start_time = int((current_time_utc - timedelta(hours=24)).timestamp() * 1000)
    print("No existing data found, starting from 24 hours ago")

# Set current time as the end time for the loop
current_time_utc = datetime.now(timezone.utc)
end_time = int(current_time_utc.timestamp() * 1000)
print(f"Current time: {current_time_utc} UTC")
print(f"Start time for API query: {datetime.fromtimestamp(start_time/1000, tz=timezone.utc)} UTC")
print(f"End time for API query: {datetime.fromtimestamp(end_time/1000, tz=timezone.utc)} UTC")

# Make sure we're not looking more than 3 days ahead to avoid errors
if start_time > end_time + (3 * 24 * 60 * 60 * 1000):
    print("⚠️ Warning: Start time is more than 3 days in the future, adjusting to 24 hours ago")
    start_time = int((current_time_utc - timedelta(hours=24)).timestamp() * 1000)
    print(f"Adjusted start time: {datetime.fromtimestamp(start_time/1000, tz=timezone.utc)} UTC")

# List to store all newly fetched data
all_data = []
print("📡 Fetching latest Binance funding and BTC price...")

# Fetch funding and price data in chunks until reaching the current time
max_end_time = end_time + (3 * 24 * 60 * 60 * 1000)  # Allow fetching 3 days ahead for pre-published rates
while start_time < max_end_time:
    params = {
        "symbol": symbol,
        "limit": limit,
        "startTime": start_time
    }
    print(f"API query params: {params}")
    resp = requests.get(funding_url, params=params)
    data = resp.json()
    print(f"API response: Got {len(data)} records")

    if not data:
        print("No data returned from API")
        break  # Exit if no data returned

    for entry in data:
        funding_time = int(entry['fundingTime'])
        funding_rate = float(entry['fundingRate'])

        # Align funding time to the nearest full hour to match 1-hour candle
        rounded_time = funding_time - (funding_time % (60 * 60 * 1000))
        price_params = {
            "symbol": symbol,
            "interval": "1h",
            "startTime": rounded_time,
            "limit": 1
        }
        price_resp = requests.get(kline_url, params=price_params)
        price_data = price_resp.json()

        # Extract mark price from the 1-hour kline
        if isinstance(price_data, list) and price_data:
            mark_price = float(price_data[0][1])  # Open price of the candle
        else:
            mark_price = None
            print(f"Could not get price data for time {datetime.fromtimestamp(funding_time/1000, tz=timezone.utc)} UTC")

        # Store record with timestamp, funding rate, and mark price
        timestamp_utc = datetime.fromtimestamp(funding_time / 1000, tz=timezone.utc)
        all_data.append({
            "timestamp": timestamp_utc,
            "fundingRate": funding_rate,
            "price": mark_price
        })
        print(f"Added record for {timestamp_utc} UTC: rate={funding_rate}, price={mark_price}")

        time.sleep(0.05)  # Avoid hitting API rate limits

    # Move start time forward to the next funding time
    start_time = int(data[-1]['fundingTime']) + 1
    time.sleep(0.05)

# Check for specific expected funding rates if normal fetch didn't get new data
if len(all_data) == 0:
    print("No data from standard query, checking specific funding timestamps...")
    
    # Funding occurs every 8 hours at 00:00, 08:00, and 16:00 UTC
    # Let's check for the next expected funding time after our last record
    if 'last_timestamp' in locals():
        # We already have the calculated next_funding_time
        expected_funding_times = [next_funding_time]
        
        # Also check the one after that, just in case
        expected_funding_times.append(next_funding_time + timedelta(hours=8))
    else:
        # If we don't have a last timestamp, check the last 24 hours
        current_time_utc = datetime.now(timezone.utc)
        
        # Calculate the most recent funding times (in the past 24 hours)
        funding_hours = [0, 8, 16]  # UTC hours when funding occurs
        expected_funding_times = []
        
        # Check for the last 24 hours of potential funding times
        for hours_ago in range(0, 25, 8):
            check_time = current_time_utc - timedelta(hours=hours_ago)
            # Adjust to the last expected funding time
            for hour in funding_hours:
                funding_time = check_time.replace(hour=hour, minute=0, second=0, microsecond=0)
                if funding_time <= current_time_utc:
                    expected_funding_times.append(funding_time)
    
    # Sort funding times in descending order to check newest first
    expected_funding_times.sort(reverse=True)
    
    # Check each expected funding time individually
    for funding_time in expected_funding_times:
        funding_time_ms = int(funding_time.timestamp() * 1000)
        params = {
            "symbol": symbol,
            "startTime": funding_time_ms,
            "endTime": funding_time_ms + 1000,  # Add 1 second to be safe
            "limit": 1
        }
        print(f"Checking specific funding time {funding_time} UTC with params: {params}")
        resp = requests.get(funding_url, params=params)
        data = resp.json()
        print(f"Response for {funding_time} UTC: Got {len(data)} records")
        
        if data:
            for entry in data:
                funding_time = int(entry['fundingTime'])
                funding_rate = float(entry['fundingRate'])
                
                # Check if we already have this funding time
                if df_existing is not None and not df_existing.empty:
                    timestamp_check = datetime.fromtimestamp(funding_time / 1000)
                    if any(df_existing['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S') == timestamp_check.strftime('%Y-%m-%d %H:%M:%S')):
                        print(f"Skipping already existing funding time: {timestamp_check}")
                        continue
                
                # Get the price data for this funding time
                rounded_time = funding_time - (funding_time % (60 * 60 * 1000))
                price_params = {
                    "symbol": symbol,
                    "interval": "1h",
                    "startTime": rounded_time,
                    "limit": 1
                }
                price_resp = requests.get(kline_url, params=price_params)
                price_data = price_resp.json()
                
                if isinstance(price_data, list) and price_data:
                    mark_price = float(price_data[0][1])  # Open price of the candle
                else:
                    mark_price = None
                    print(f"Could not get price data for time {datetime.fromtimestamp(funding_time/1000, tz=timezone.utc)} UTC")
                
                # Store record
                timestamp_utc = datetime.fromtimestamp(funding_time / 1000, tz=timezone.utc)
                all_data.append({
                    "timestamp": timestamp_utc,
                    "fundingRate": funding_rate,
                    "price": mark_price
                })
                print(f"Added specific record for {timestamp_utc} UTC: rate={funding_rate}, price={mark_price}")
        
        time.sleep(0.1)  # Avoid API rate limits

# Convert all new records to DataFrame
df_new = pd.DataFrame(all_data)
print(f"Total new records fetched: {len(df_new)}")

# Combine with existing data and drop duplicates
if not df_existing.empty and not df_new.empty:
    # Ensure timestamps are compatible by converting to naive datetime if needed
    if df_new["timestamp"].iloc[0].tzinfo is not None:
        df_new["timestamp"] = df_new["timestamp"].dt.tz_localize(None)
    
    df_merged = pd.concat([df_existing, df_new]).drop_duplicates("timestamp").sort_values("timestamp")
    print(f"Merged {len(df_existing)} existing and {len(df_new)} new records, final count: {len(df_merged)}")
elif not df_new.empty:
    # For new data only, convert timezone-aware timestamps to naive
    df_new["timestamp"] = df_new["timestamp"].dt.tz_localize(None)
    df_merged = df_new
    print(f"No existing records, only new {len(df_new)} records")
else:
    # No new data
    df_merged = df_existing
    print("No new records to add")

# First try to write to a temporary file
try:
    # Save updated DataFrame to temporary CSV
    os.makedirs(os.path.dirname(temp_csv_path), exist_ok=True)
    df_merged.to_csv(temp_csv_path, index=False, decimal=',')
    print(f"✅ Wrote to temporary file: {temp_csv_path}")
    
    # Now try to replace the original file with the temp file
    try:
        # First try renaming (atomic operation)
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        shutil.move(temp_csv_path, csv_path)
        print(f"✅ Successfully updated: {csv_path} with {len(df_new)} new records")
    except Exception as e:
        # If renaming fails, try to copy instead
        print(f"Warning: Could not move temp file: {e}")
        try:
            shutil.copyfile(temp_csv_path, csv_path)
            print(f"✅ Successfully copied to: {csv_path} with {len(df_new)} new records")
        except Exception as e2:
            print(f"❌ Error: Could not copy temp file: {e2}")
            print(f"The updated data is still available in the temporary file: {temp_csv_path}")
except Exception as e:
    print(f"❌ Error while saving CSV: {e}")
    print("Please check if any other process is using the file.")
