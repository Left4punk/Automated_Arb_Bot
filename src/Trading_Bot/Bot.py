import pandas as pd
import os
import config_bot
from datetime import datetime, timedelta

# === CONFIGURATION ===
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, "..", ".."))
live_data_path = os.path.join(root_dir, "data", "binance_btcusdt_funding_live.csv")
results_path = os.path.join(root_dir, "data", "live_bot_results.csv")
initial_btc = config_bot.btc_position
maker_fee_rate = config_bot.position_fee

# === LOAD LIVE DATA ===
df = pd.read_csv(live_data_path, parse_dates=["timestamp"], decimal=',')
df = df[df["fundingRate"] != 0].sort_values("timestamp").reset_index(drop=True)

# === LOAD PREVIOUS RESULTS IF AVAILABLE ===
if os.path.exists(results_path) and os.path.getsize(results_path) > 0:
    df_results = pd.read_csv(results_path, parse_dates=["timestamp"], decimal=',')
    if not df_results.empty and "timestamp" in df_results.columns:
        df_results = df_results.sort_values("timestamp")
    btc_balance = df_results["btc_balance"].iloc[-1] if not df_results.empty else initial_btc
    last_trade_id = df_results["trade_id"].dropna().max()
    last_trade_id = int(last_trade_id) + 1 if pd.notna(last_trade_id) else 0

    # Detect open positions (last trade where profit is still 0)
    grouped = df_results[df_results["trade_id"].notna()].groupby("trade_id")
    open_trades = grouped.filter(lambda x: x["position"].notna().any() and (x["profit"].iloc[-1] == 0))
    position_open = not open_trades.empty

    if position_open:
        open_trades_grouped = open_trades.groupby("trade_id").last()
        current_direction = open_trades_grouped["position"].iloc[-1]
        trade_id_active = open_trades_grouped.index[-1]
        cumulative_profit = df_results[df_results["trade_id"] == trade_id_active]["profit"].sum()
        rounds = df_results[df_results["trade_id"] == trade_id_active].shape[0]
    else:
        current_direction = None
        cumulative_profit = 0
        rounds = 0
else:
    # Initialize empty results DataFrame if no past results
    df_results = pd.DataFrame(columns=["timestamp", "fundingRate", "price", "position", "fees_paid", "profit", "btc_balance", "trade_id"])
    btc_balance = initial_btc
    last_trade_id = 0
    position_open = False
    current_direction = None
    cumulative_profit = 0
    rounds = 0

# === GET MOST RECENT FUNDING RECORD ===
row = df.iloc[-1]
funding = row["fundingRate"]
price = row["price"]
ts = row["timestamp"]
position_size_usdt = btc_balance * price
one_side_fee = position_size_usdt * maker_fee_rate
round_fee = one_side_fee * 2
direction = "long" if funding < 0 else "short"
step_income = abs(funding) * position_size_usdt

# Calculate moving average of last 3 funding rates
window = df.tail(3)["fundingRate"].tolist()
avg_funding = sum(window) / len(window)

# === ENTRY LOGIC ===
should_open = False
if not position_open:
    should_open = step_income >= round_fee and avg_funding * funding > 0
    if should_open:
        net_profit = step_income - round_fee
        if net_profit > 0:
            btc_balance += net_profit / price

        record = {
            "timestamp": ts,
            "fundingRate": funding,
            "price": price,
            "position": direction,
            "fees_paid": one_side_fee,
            "profit": net_profit,
            "btc_balance": btc_balance,
            "trade_id": last_trade_id
        }
        df_results = pd.concat([df_results, pd.DataFrame([record])])
        print(f"✅ Trade OPENED at {ts}: {direction} | Profit: {round(net_profit,2)} USDT")
    else:
        # Log skipped opportunity
        record = {
            "timestamp": ts,
            "fundingRate": funding,
            "price": price,
            "position": None,
            "fees_paid": 0,
            "profit": 0,
            "btc_balance": btc_balance,
            "trade_id": None
        }
        df_results = pd.concat([df_results, pd.DataFrame([record])])
        print("❌ No trade today: entry condition not met. Row recorded.")

# === EXIT / HOLD LOGIC ===
else:
    exit_due_to_avg_flip = (current_direction == "short" and avg_funding < 0) or (current_direction == "long" and avg_funding > 0)
    if exit_due_to_avg_flip:
        net_profit = cumulative_profit + step_income - one_side_fee
        if net_profit > 0:
            btc_balance += net_profit / price

        record = {
            "timestamp": ts,
            "fundingRate": funding,
            "price": price,
            "position": current_direction,
            "fees_paid": one_side_fee,  # Exit fee only
            "profit": net_profit,
            "btc_balance": btc_balance,
            "trade_id": trade_id_active
        }
        df_results = pd.concat([df_results, pd.DataFrame([record])])
        print(f"📤 Trade CLOSED at {ts}: {current_direction} | Total Profit: {round(net_profit,2)} USDT")
    else:
        # Continue holding position
        cumulative_profit += step_income
        record = {
            "timestamp": ts,
            "fundingRate": funding,
            "price": price,
            "position": current_direction,
            "fees_paid": 0,
            "profit": cumulative_profit - round_fee,
            "btc_balance": btc_balance,
            "trade_id": trade_id_active
        }
        df_results = pd.concat([df_results, pd.DataFrame([record])])
        print(f"📈 Holding {current_direction} | Accumulated Profit: {round(cumulative_profit - round_fee, 2)}")

# === SAVE RESULTS TO CSV ===
if not df_results.empty and "timestamp" in df_results.columns:
    df_results = df_results.sort_values("timestamp")

os.makedirs(os.path.join(root_dir, "data"), exist_ok=True)
df_results.to_csv(results_path, index=False, decimal=',')
