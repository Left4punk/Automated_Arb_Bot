import requests
import pandas as pd
import time
import os
from datetime import datetime

# === Configuration ===
symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
limit = 1000
start_time = int(datetime(2019, 1, 1).timestamp() * 1000)
end_time = int(datetime.now().timestamp() * 1000)

# API endpoints
funding_url = "https://fapi.binance.com/fapi/v1/fundingRate"
kline_url = "https://fapi.binance.com/fapi/v1/markPriceKlines"

# Create data folder
os.makedirs("data", exist_ok=True)

# Loop through each symbol
for symbol in symbols:
    print(f"\n📡 Downloading funding data for {symbol}...")
    all_data = []
    current_start = start_time

    while current_start < end_time:
        params = {
            "symbol": symbol,
            "limit": limit,
            "startTime": current_start
        }
        try:
            resp = requests.get(funding_url, params=params)
            data = resp.json()

            if not data:
                break

            for entry in data:
                funding_time = int(entry['fundingTime'])
                funding_rate = float(entry['fundingRate'])

                # Round to nearest full hour
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
                    mark_price = float(price_data[0][1])
                else:
                    mark_price = None

                all_data.append({
                    "timestamp": datetime.fromtimestamp(funding_time / 1000),
                    "fundingRate": funding_rate,
                    "price": mark_price
                })

                time.sleep(0.01)

            current_start = int(data[-1]['fundingTime']) + 1
            time.sleep(0.01)

        except Exception as e:
            print(f"⚠️ Error fetching {symbol}: {e}")
            break

    # Save to CSV
    df = pd.DataFrame(all_data)
    filename = f"data/binance_{symbol.lower()}_funding.csv"
    df.to_csv(filename, index=False, decimal=',')
    print(f"✅ Saved {len(df)} rows to '{filename}'")
