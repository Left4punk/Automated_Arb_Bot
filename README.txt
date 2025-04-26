# Arbitrage Bot (Funding-Based Strategy)

This project simulates and runs a live arbitrage trading strategy using funding rates from Binance's perpetual futures market. It includes both backtesting tools and a real-time bot with a Streamlit-based dashboard.

---

## Features

### ✅ Strategy & Backtesting
- Simulate long/short funding arbitrage based on real Binance funding data
- Evaluate performance with dynamic entry/exit logic and BTC compounding
- Calculate profit in USDT and BTC-based APY over time
- Supports configurable entry conditions: entry-only / half-round / round-trip
- Option to use 3-funding moving average window for exits

### 🔁 Live Bot Execution
- Live funding rate ingestion (8-hour intervals)
- Logic to determine trade entries and exits in real-time
- Records each funding window in `live_bot_results.csv`
- Automatically merges backtest and live data into a unified database
- Hourly scheduling using Python scheduler

### 📊 Streamlit Dashboard
- Visualize live and historical trade data
- View BTC balance growth, funding rates, profits, and more
- Filter by `source` (backtest / live) and `direction` (long / short)
- APY metrics and BTC growth metrics calculated in real time

---

## Folder Structure

Arb_Bot/
├── data/
│   ├── binance_btcusdt_funding_live.csv      # Live data
│   ├── live_bot_results.csv                  # Live bot records
│   ├── DataBase.csv                          # Merged backtest + live
│   └── backtest_info_entry_only_avg_24.csv  # Backtest sample
├── requirements.txt
├── README.txt
├── src/
│   ├── BackTesting/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── Backtest_Algo.py
│   │   ├── dual_Backtest.py
│   │   ├── get_Binance_Fundings.py
│   │   ├── get_Bybit_Fundings.py
│   │   └── data/                             # All backtest results
│   ├── Trading_Bot/
│   │   ├── Bot.py
│   │   ├── Bot_Launcher.py
│   │   ├── Daily_Fund_Fetcher.py
│   │   ├── config_bot.py
│   │   └── DataBase.py
│   └── Dashboard/
│       └── Dashoard.py                      # Streamlit dashboard

---

## How to Use

### 1. Setup Environment
```bash
pip install -r requirements.txt
```

### 2. Run Backtest (optional)
```bash
# Ensure historical funding data is present
python BackTesting/main.py  # (if applicable)
```

### 3. Run the Bot Manually (Single Execution)
```bash
python Bot.py
```

### 4. Launch Hourly Bot Scheduler (Continuous Run)
```bash
python Bot_Launcher.py
```

### 5. View the Dashboard
```bash
streamlit run Dashoard.py
```

You can also use `localtunnel` to make the dashboard accessible externally:
```bash
npx localtunnel --port 8501
```

---

## Configuration

Edit the following parameters in `config_bot.py`:
```python
btc_position = 5                     # Initial BTC position
position_fee = 0.0002               # Maker fee
use_compounding = True              # Reinvest profits in BTC
entry_fee_type = "entry_only"       # Entry rule: "entry_only", "half_round", "round_trip"
short_only = False                  # Only allow shorts
use_avg_window = True               # Use 3-funding avg for exit
exit_on_low_funding = False         # Force exit on low income
```

---

## Requirements

- Python 3.9+
- Node.js (only if using `localtunnel`)

Required Python packages (in `requirements.txt`):
- `pandas`
- `schedule`
- `requests`
- `matplotlib`
- `streamlit`

---

## Notes
- Binance funding rates are updated every 8 hours
- Strategy is intended to mimic real trading conditions as closely as possible
- Make sure your local timezone does not offset UTC timestamps if debugging

---