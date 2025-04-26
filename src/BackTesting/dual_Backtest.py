import config
from Backtest_Algo import FundingArbitrageBacktest
import os

# Rutas a los CSVs
binance_file = "../data/binance_btcusdt_funding.csv"
bybit_file = "../data/bybit_btcusdt_funding.csv"

# --- Paso 1: Correr backtests individualmente ---
def run_backtest_for(file_path):
    config.funding_file = file_path
    backtester = FundingArbitrageBacktest(csv_file=file_path)
    backtester.load_data()
    backtester.run_backtest()
    summary = backtester.summary()
    return summary

summary_binance = run_backtest_for(binance_file)
summary_bybit = run_backtest_for(bybit_file)

apy_binance = summary_binance["APY Estimated (BTC-based %)"] / 100
apy_bybit = summary_bybit["APY Estimated (BTC-based %)"] / 100

# --- Paso 2: Buscar el mejor split de BTC para maximizar el APY total ---
total_btc = config.btc_position
best_apy = 0
best_split = (0, config.btc_position)

for i in range(0, 101):
    pct_binance = i / 100
    btc_binance = total_btc * pct_binance
    btc_bybit = total_btc - btc_binance

    final_btc_binance = btc_binance * (1 + apy_binance)
    final_btc_bybit = btc_bybit * (1 + apy_bybit)
    final_total_btc = final_btc_binance + final_btc_bybit

    apy_total = ((final_total_btc / total_btc) - 1) * 100

    if apy_total > best_apy:
        best_apy = apy_total
        best_split = (btc_binance, btc_bybit)

# --- Resultados ---
print("\n--- Individual Results ---")
print(f"Binance APY: {apy_binance*100:.2f}%")
print(f"Bybit APY: {apy_bybit*100:.2f}%")

print("\n--- Optimized Split ---")
print(f"Best APY: {best_apy:.2f}%")
print(f"BTC to Binance: {best_split[0]:.2f}, BTC to Bybit: {best_split[1]:.2f}")
