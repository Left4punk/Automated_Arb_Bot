import pandas as pd
import os
import sys
# === Setup dynamic paths based on script location ===
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))

# === Paths to input data files ===
backtest_path = os.path.join(root_dir, "src", "BackTesting", "data", "backtest_info_entry_only_avg_24.csv")
live_path = os.path.join(root_dir, "data", "binance_btcusdt_funding_live.csv")
output_path = os.path.join(root_dir, "data", "DataBase.csv")

# === Load the backtest dataset ===
if os.path.exists(backtest_path):
    df_backtest = pd.read_csv(backtest_path, parse_dates=["timestamp"], decimal=',')
    df_backtest["source"] = "backtest"  # Label the source
else:
    raise FileNotFoundError("Backtest CSV not found")

# === Load the live results dataset ===
if os.path.exists(live_path):
    df_live = pd.read_csv(live_path, parse_dates=["timestamp"], decimal=',').drop_duplicates()
    df_live["source"] = "live"  # Label the source
else:
    # If no live data exists yet, initialize an empty DataFrame with same structure
    df_live = pd.DataFrame(columns=df_backtest.columns)

print (df_live)
sys.exit()
# === Combine both datasets into a single DataFrame ===
combined_df = pd.concat([df_backtest, df_live], ignore_index=True)

# === Drop duplicate records based on timestamp and source, and sort chronologically ===
combined_df = combined_df.drop_duplicates(subset=["timestamp", "source"]).sort_values("timestamp")

# === Save the merged dataset to output CSV ===
os.makedirs(os.path.dirname(output_path), exist_ok=True)
combined_df.to_csv(output_path, index=False, decimal=',')
print(f"✅ Merged dataset saved to {output_path} with {len(combined_df)} total rows.")
