import pandas as pd
import config
import os
import sys
from Backtest_Algo import FundingArbitrageBacktest

if __name__ == '__main__':
    # Initialize the backtest with config
    backtester = FundingArbitrageBacktest(csv_file=config.funding_file)

    # Run the full backtest pipeline
    backtester.load_data()
    backtester.run_backtest()
    print(backtester.summary())

    # Optional: Uncomment for visual plot
    # backtester.plot_cumulative_profit()

    # Export results to /data folder
    output_path = os.path.join("data", f"{config.asset_name}_backtest_info_entry_only_avg_24_idle.csv")
    os.makedirs("data", exist_ok=True)  # Ensure the directory exists
    backtester.export_modified_csv(output_path)
