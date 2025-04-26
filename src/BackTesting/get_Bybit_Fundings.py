import requests
import pandas as pd
import time
import os
from datetime import datetime, timedelta

# Configuración
symbol = "BTCUSDT"
category = "linear"
interval = "60"
limit = 200  # Máximo según docs
step_days = 7  # Por seguridad, bajas en bloques de 7 días

# Tiempos iniciales
start_date = datetime(2019, 1, 1)
end_date = datetime.now()

# Endpoints de la API de Bybit
funding_url = "https://api.bybit.com/v5/market/funding/history"
kline_url = "https://api.bybit.com/v5/market/mark-price-kline"

# Lista para guardar los datos
all_data = []

print("Downloading funding + mark price data from Bybit...")

while start_date < end_date:
    batch_end = min(start_date + timedelta(days=step_days), end_date)
    start_ms = int(start_date.timestamp() * 1000)
    end_ms = int(batch_end.timestamp() * 1000)

    funding_params = {
        "category": category,
        "symbol": symbol,
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": limit
    }

    funding_resp = requests.get(funding_url, params=funding_params)
    funding_data = funding_resp.json()

    funding_list = funding_data.get("result", {}).get("list", [])

    if not funding_list:
        print(f"No data from {start_date} to {batch_end}")
        start_date = batch_end
        continue

    for entry in funding_list:
        funding_time = int(entry['fundingRateTimestamp'])
        funding_rate = float(entry['fundingRate'])

        rounded_time = funding_time - (funding_time % (60 * 60 * 1000))

        price_params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "start": rounded_time,
            "limit": 1
        }

        price_resp = requests.get(kline_url, params=price_params)
        price_data = price_resp.json()

        if price_data.get("result", {}).get("list"):
            mark_price = float(price_data["result"]["list"][0][1])
        else:
            mark_price = None

        all_data.append({
            "timestamp": datetime.fromtimestamp(funding_time / 1000),
            "fundingRate": funding_rate,
            "price": mark_price
        })

        time.sleep(0.03)

    start_date = batch_end
    time.sleep(0.03)

# Exportar a CSV
df = pd.DataFrame(all_data)
os.makedirs("data", exist_ok=True)
output_path = os.path.join("data", "bybit_btcusdt_funding.csv")
df.to_csv(output_path, index=False, decimal='.')
print(f"✅ Done: {output_path} with {len(df)} records saved.")
