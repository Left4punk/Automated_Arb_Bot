import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta, timezone
import os
import time

# Set config at the top (fixes Streamlit error)
st.set_page_config(layout="wide")

# Check for mobile device - safer implementation
def is_mobile():
    # Use session state to let user self-identify as mobile
    if 'is_mobile_view' not in st.session_state:
        st.session_state.is_mobile_view = False
    return st.session_state.is_mobile_view

# Toggle mobile view
def toggle_mobile_view():
    st.session_state.is_mobile_view = not st.session_state.is_mobile_view
    
# Add mobile toggle in sidebar
st.sidebar.title("Dashboard Settings")
if st.sidebar.button("Toggle Mobile View", on_click=toggle_mobile_view):
    pass
st.sidebar.write("Current view: " + ("Mobile" if is_mobile() else "Desktop"))

# Paths
DATA_PATH = "data/Database.csv"
st_autorefresh(interval=1000 * 60 * 60, key="refresh_dashboard")

# Load CSV safely
if not os.path.exists(DATA_PATH):
    st.error("❌ Database.csv not found in data/ directory.")
    st.stop()

# Load Data
try:
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"], decimal=",")
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# Detect mobile - show simplified version if on mobile
mobile_device = is_mobile()
if mobile_device:
    st.title("📈 Arbitrage Bot Dashboard (Mobile View)")
    st.warning("You're viewing the simplified mobile version. For the full experience, please use a desktop browser.")
    
    # Show basic KPIs and latest data
    if not df.empty:
        df_live = df[df["source"] == "live"]
        if not df_live.empty:
            initial_balance = df_live["btc_balance"].iloc[0]
            final_balance = df_live["btc_balance"].iloc[-1]
            total_days = (df_live["timestamp"].max() - df_live["timestamp"].min()).days or 1
            apy = ((final_balance / initial_balance) ** (365 / total_days) - 1) * 100
            
            st.metric("APY %", f"{apy:.2f}%")
            st.metric("BTC Balance", f"{final_balance:.4f}")
            
            # Show latest funding rate
            latest = df_live.sort_values("timestamp", ascending=False).iloc[0]
            st.metric("Latest Funding Rate", f"{latest['fundingRate']:.8f}")
            st.metric("Latest BTC Price", f"${latest['price']:.2f}")
            
            # Calculate time until next funding rate
            now_utc = datetime.now(tz=timezone.utc)
            funding_hours = [0, 8, 16]  # Hours when funding occurs (UTC)
            st.write(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            
            # Last 5 rows in table format
            st.subheader("Recent Funding Rates")
            recent_data = df_live.sort_values("timestamp", ascending=False).head(5)
            st.dataframe(recent_data[["timestamp", "fundingRate", "price"]])
    else:
        st.error("No data available")
    
    st.stop()  # Don't execute the rest of the code for mobile

# Regular view for desktop browsers
# Sidebar filters
source_filter = st.sidebar.selectbox("📊 Choose data source", options=["backtest", "live"])
direction_filter = st.sidebar.selectbox("📉 Filter by trade direction", options=["All", "short", "long"])

# Date range controls for live data
if source_filter == "live":
    # Get current month (first day of current month)
    current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    default_start_date = current_month_start
    default_end_date = current_month_start + timedelta(days=45)  # Current month + ~15 days into next month
    
    # Add date range selector to sidebar
    show_date_range = st.sidebar.checkbox("Custom Date Range", value=True)
    
    if show_date_range:
        start_date = st.sidebar.date_input("Start Date", value=default_start_date)
        end_date = st.sidebar.date_input("End Date", value=default_end_date)
        
        # Convert to datetime for filtering
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
    else:
        # Use default date range
        start_datetime = default_start_date
        end_datetime = default_end_date

# Main layout
st.title("📈 Arbitrage Bot Dashboard")
st.markdown("Live and backtest performance tracking with trade insights.")

# Sort and clean
df = df.sort_values("timestamp")

# Apply filters to show filtered data in charts/tables
df_filtered = df[df["source"] == source_filter]
if direction_filter != "All":
    df_filtered = df_filtered[df_filtered["position"] == direction_filter]

# Apply date filter for live data
if source_filter == "live" and show_date_range:
    df_filtered = df_filtered[(df_filtered["timestamp"] >= start_datetime) & 
                             (df_filtered["timestamp"] <= end_datetime)]

if df_filtered.empty:
    st.warning("No data available for selected filters.")
    st.stop()

# Calculate metrics based on the full dataset, not just the filtered view
if not df[df["source"] == source_filter].empty:
    df_metrics = df[df["source"] == source_filter]
    initial_balance = df_metrics["btc_balance"].iloc[0]
    final_balance = df_metrics["btc_balance"].iloc[-1]
    total_days = (df_metrics["timestamp"].max() - df_metrics["timestamp"].min()).days or 1
    apy = ((final_balance / initial_balance) ** (365 / total_days) - 1) * 100
else:
    initial_balance = 0
    final_balance = 0
    apy = 0

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Initial BTC", round(initial_balance, 4))
col2.metric("Final BTC", round(final_balance, 4))
col3.metric("# Trades", df_filtered["trade_id"].nunique())
col4.metric("APY %", f"{apy:.2f}%")

# Charts
st.markdown("---")
st.subheader("📉 Funding Rate and Price Over Time")
col5, col6 = st.columns(2)

with col5:
    fig1, ax1 = plt.subplots(figsize=(8, 3))
    df_filtered.plot(x="timestamp", y="fundingRate", ax=ax1, legend=False, color="#2196f3")
    ax1.set_title("Funding Rate History")
    ax1.set_ylabel("Rate")
    ax1.grid(True)
    
    # Set x-axis limits explicitly for April 2025 and 15 days forward
    if source_filter == "live" and show_date_range:
        ax1.set_xlim([start_datetime, end_datetime])
    
    # Format x-axis date labels to be more readable
    fig1.autofmt_xdate()
    st.pyplot(fig1)

with col6:
    fig2, ax2 = plt.subplots(figsize=(8, 3))
    df_filtered.plot(x="timestamp", y="price", ax=ax2, legend=False, color="#4caf50")
    ax2.set_title("BTC Price History")
    ax2.set_ylabel("USDT")
    ax2.grid(True)
    
    # Set x-axis limits explicitly for April 2025 and 15 days forward
    if source_filter == "live" and show_date_range:
        ax2.set_xlim([start_datetime, end_datetime])
    
    # Format x-axis date labels
    fig2.autofmt_xdate()
    st.pyplot(fig2)

st.markdown("---")
col7, col8 = st.columns(2)

with col7:
    fig3, ax3 = plt.subplots(figsize=(8, 3))
    df_filtered.plot(x="timestamp", y="btc_balance", ax=ax3, legend=False, color="#9c27b0")
    ax3.set_title("Position Value History")
    ax3.set_ylabel("BTC")
    ax3.grid(True)
    
    # Set x-axis limits explicitly for April 2025 and 15 days forward
    if source_filter == "live" and show_date_range:
        ax3.set_xlim([start_datetime, end_datetime])
    
    # Format x-axis date labels
    fig3.autofmt_xdate()
    st.pyplot(fig3)

with col8:
    fig4, ax4 = plt.subplots(figsize=(8, 3))
    df_filtered.plot(x="timestamp", y="profit", ax=ax4, legend=False, color="#ff9800")
    ax4.set_title("Profit History")
    ax4.set_ylabel("Profit (USDT)")
    ax4.grid(True)
    
    # Set x-axis limits explicitly for April 2025 and 15 days forward
    if source_filter == "live" and show_date_range:
        ax4.set_xlim([start_datetime, end_datetime])
    
    # Format x-axis date labels
    fig4.autofmt_xdate()
    st.pyplot(fig4)

# Table View
st.markdown("---")

# Calculate time until next funding rate (funding occurs every 8 hours at 00:00, 08:00, and 16:00 UTC)
# Get current time in UTC (not local time)
now_utc = datetime.now(tz=timezone.utc)
funding_hours = [0, 8, 16]  # Hours when funding occurs (UTC)

# Display current UTC time for debugging
st.sidebar.markdown(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Find the next funding time
candidates = []

# Today's remaining funding times
today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
for hour in funding_hours:
    candidate = today.replace(hour=hour)
    if candidate > now_utc:
        candidates.append(candidate)

# If all of today's funding times have passed, use tomorrow's first funding time
if not candidates:
    tomorrow = today + timedelta(days=1)
    candidates.append(tomorrow.replace(hour=0))  # 00:00 UTC tomorrow

# Get the earliest future funding time
next_funding = min(candidates)

# Calculate time difference
time_until_next = next_funding - now_utc
hours, remainder = divmod(time_until_next.total_seconds(), 3600)
minutes, seconds = divmod(remainder, 60)

# Calculate the previous funding time
prev_candidates = []
for hour in reversed(funding_hours):
    candidate = today.replace(hour=hour)
    if candidate <= now_utc:
        prev_candidates.append(candidate)
        break

# If no funding time today has passed yet, use yesterday's last funding time
if not prev_candidates:
    yesterday = today - timedelta(days=1)
    prev_candidates.append(yesterday.replace(hour=16))  # 16:00 UTC yesterday

# Get the most recent past funding time
prev_funding = max(prev_candidates)
time_since_prev = now_utc - prev_funding
since_hours, since_remainder = divmod(time_since_prev.total_seconds(), 3600)
since_minutes, since_seconds = divmod(since_remainder, 60)

# Display countdown timer with funding history title
col_title, col_timer, col_last = st.columns([2, 1, 1])
with col_title:
    st.subheader("📜 Funding Periods History")
with col_timer:
    st.markdown(f"**Next Funding: {int(hours):02d}:{int(minutes):02d}**")
with col_last:
    st.markdown(f"**Last Funding: {int(since_hours):02d}:{int(since_minutes):02d} ago**")

# Display filtered data
df_display = df_filtered[["timestamp", "fundingRate", "price", "profit", "btc_balance", "position", "source"]].copy()
df_display.columns = ["Time", "Funding Rate", "BTC Price ($)", "Profit ($)", "Balance", "Direction", "Source"]
df_display = df_display.sort_values("Time", ascending=False).reset_index(drop=True)
st.dataframe(df_display, use_container_width=True, height=300)
