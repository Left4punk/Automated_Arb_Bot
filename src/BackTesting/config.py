# config.py

asset_name = "SOL"

funding_file = f"data/binance_solusdt_funding.csv"

btc_position = 2000                        # Your initial asset balance
position_fee = 0.0002                     # Maker fee (0.02%)
use_compounding = True                    # Reinvest profits in BTC or not

# === Strategy configuration ===
entry_fee_type = "entry_only"            # Options:
                                         # - "entry_only": open if funding > entry fee
                                         # - "half_round": open if funding > 0.5 * (entry + exit fee)
                                         # - "round_trip": open if funding > full round-trip fees

short_only = False                        # If True → only enter shorts (funding positive)
use_avg_window = True                     # If True → use 24h avg funding (last 3) to decide exit
exit_on_low_funding = False               # If True → exit if funding income < exit fee

# === Passive Lending ===
enable_idle_lending = True               # If True, earn passive APY while idle (not in trade)
idle_lending_apy = 0.0997                # Example: 9.97% APY annualized yield (on idle capital)
