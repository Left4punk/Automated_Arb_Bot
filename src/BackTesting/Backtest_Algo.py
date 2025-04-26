import pandas as pd
import os
import config

class FundingArbitrageBacktest:
    def __init__(self, csv_file, asset_name=config.asset_name, btc_position=config.btc_position, maker_fee_rate=config.position_fee, compound=config.use_compounding):
        self.csv_file = csv_file
        self.asset_name = asset_name  # BTC, ETH, SOL
        self.btc_position = btc_position
        self.initial_btc = btc_position
        self.maker_fee_rate = maker_fee_rate
        self.compound = compound
        self.df = None
        self.results = []
        self.df_results = None

    def load_data(self):
        self.df = pd.read_csv(self.csv_file, decimal=',', parse_dates=["timestamp"])
        self.df = self.df[self.df["fundingRate"] != 0].sort_values("timestamp")
        self.df["position"] = None
        self.df["fees_paid"] = 0.0
        self.df["profit"] = 0.0
        self.df["trade_id"] = None
        self.df["btc_balance"] = self.btc_position

    def run_backtest(self):
        position_open = False
        current_direction = None
        cumulative_funding = 0
        funding_income = 0
        rounds = 0
        trade_id = 0
        btc_balance = self.btc_position
        funding_window = []

        for i, row in self.df.iterrows():
            funding = row["fundingRate"]
            price = row["price"]
            ts = row["timestamp"]
            position_size_usdt = btc_balance * price
            one_side_fee = position_size_usdt * self.maker_fee_rate
            round_fee = one_side_fee * 2
            direction = "long" if funding < 0 else "short"
            step_income = abs(funding) * position_size_usdt

            self.df.loc[i, "btc_balance"] = btc_balance

            entry_fee_threshold = {
                "entry_only": one_side_fee,
                "half_round": round_fee * 0.5,
                "round_trip": round_fee
            }.get(config.entry_fee_type, round_fee)

            if step_income >= entry_fee_threshold and not position_open:
                if config.short_only and direction != "short":
                    continue

                position_open = True
                current_direction = direction
                cumulative_funding = funding
                funding_income = step_income
                rounds = 1
                funding_window = [funding]

                self.df.loc[i, "position"] = direction
                self.df.loc[i, "trade_id"] = trade_id
                self.df.loc[i, "fees_paid"] = one_side_fee
                self.df.loc[i, "profit"] = funding_income - round_fee

            elif position_open:
                funding_window.append(funding)
                if len(funding_window) > 3:
                    funding_window.pop(0)

                exit_due_to_direction = False
                exit_due_to_low_funding = False

                if config.use_avg_window:
                    avg_funding = sum(funding_window) / len(funding_window)
                    if (current_direction == "short" and avg_funding < 0) or (current_direction == "long" and avg_funding > 0):
                        exit_due_to_direction = True
                else:
                    if direction != current_direction:
                        exit_due_to_direction = True

                if config.exit_on_low_funding and step_income <= one_side_fee:
                    exit_due_to_low_funding = True

                if exit_due_to_direction or exit_due_to_low_funding:
                    funding_income += step_income
                    cumulative_funding += funding
                    net_profit = funding_income - round_fee
                    self.results.append({
                        "start": ts,
                        "direction": current_direction,
                        "funding_total": cumulative_funding,
                        "funding_income": funding_income,
                        "fees": round_fee,
                        "net_profit": net_profit,
                        "rounds": rounds
                    })
                    self.df.loc[i, "fees_paid"] = one_side_fee
                    self.df.loc[i, "profit"] = net_profit
                    self.df.loc[i, "trade_id"] = trade_id
                    if self.compound:
                        btc_balance += net_profit / price
                    trade_id += 1
                    position_open = False
                    current_direction = None
                else:
                    cumulative_funding += funding
                    funding_income += step_income
                    rounds += 1
                    self.df.loc[i, "position"] = current_direction
                    self.df.loc[i, "trade_id"] = trade_id
                    self.df.loc[i, "profit"] = funding_income - round_fee

        self.df_results = pd.DataFrame(self.results)
        if not self.df_results.empty:
            self.df_results["cumulative_profit"] = self.df_results["net_profit"].cumsum()

    def summary(self):
        if self.df_results is None or self.df_results.empty:
            return f"No profitable trades detected for {self.asset_name}."

        total_net = self.df_results["net_profit"].sum()
        days = (self.df["timestamp"].max() - self.df["timestamp"].min()).days
        start_btc = self.initial_btc
        final_btc = self.df["btc_balance"].iloc[-1]

        apy_btc = ((final_btc / start_btc) ** (365 / days) - 1) * 100

        print(f"[ {self.asset_name} ] Initial {self.asset_name}: {start_btc}, Final {self.asset_name}: {final_btc}")

        return {
            "Asset": self.asset_name,
            "Total net profit (USDT)": round(total_net, 2),
            "APY Estimated (BTC-based %)": round(apy_btc, 2),
            "Number of operations": len(self.df_results),
            "Most profitable streak (USDT)": round(self.df_results["net_profit"].max(), 2),
            "Least profitable streak (USDT)": round(self.df_results["net_profit"].min(), 2),
            "Longest streak": int(self.df_results["rounds"].max())
        }

    def export_modified_csv(self, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self.df.to_csv(output_path, index=False, decimal=',')
