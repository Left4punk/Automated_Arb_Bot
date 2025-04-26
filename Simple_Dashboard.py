import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import os

# Use minimal configuration to ensure compatibility
st.set_page_config(
    page_title="Arb Bot Dashboard",
    layout="centered",  # Narrower layout may work better on mobile
    initial_sidebar_state="collapsed"
)

# Title and intro
st.title("📈 Arb Bot Dashboard")
st.markdown("BTC/USDT Funding Rate Analysis")

# Path to data
DATA_PATH = "data/Database.csv"

# Load CSV safely
if not os.path.exists(DATA_PATH):
    st.error("❌ Database.csv not found in data/ directory.")
    st.stop()

# Load Data
try:
    df = pd.read_csv(DATA_PATH, parse_dates=["timestamp"], decimal=",")
    # Ensure timestamp has timezone info
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
except Exception as e:
    st.error(f"❌ Error loading data: {e}")
    st.stop()

# Add data source selector
data_source = st.radio("Select Data Source:", ["Live", "Backtest"], horizontal=True)

# Filter based on selected data source
if data_source == "Live":
    filtered_df = df[df["source"] == "live"]
    source_label = "live"
else:
    filtered_df = df[df["source"] == "backtest"]
    source_label = "backtest"

if filtered_df.empty:
    st.warning(f"No {source_label} data available.")
    st.stop()

# Calculate key metrics
initial_balance = filtered_df["btc_balance"].iloc[0]
final_balance = filtered_df["btc_balance"].iloc[-1]
total_days = (filtered_df["timestamp"].max() - filtered_df["timestamp"].min()).days or 1
apy = ((final_balance / initial_balance) ** (365 / total_days) - 1) * 100

# Basic stats
st.header("Key Metrics")
col1, col2 = st.columns(2)
col1.metric("Initial BTC", f"{initial_balance:.4f}")
col2.metric("Current BTC", f"{final_balance:.4f}")
col1.metric("APY %", f"{apy:.2f}%")
col2.metric("Time Period", f"{total_days} days")

# Display current UTC time
now_utc = datetime.now(tz=timezone.utc)
st.write(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Calculate funding times
funding_hours = [0, 8, 16]  # Hours when funding occurs (UTC)

# Find the next funding time
candidates = []
today = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
for hour in funding_hours:
    candidate = today.replace(hour=hour)
    if candidate > now_utc:
        candidates.append(candidate)

if not candidates:
    tomorrow = today + timedelta(days=1)
    candidates.append(tomorrow.replace(hour=0))

next_funding = min(candidates)
time_until_next = next_funding - now_utc
hours, remainder = divmod(time_until_next.total_seconds(), 3600)
minutes, seconds = divmod(remainder, 60)

# Find previous funding time
prev_candidates = []
for hour in reversed(funding_hours):
    candidate = today.replace(hour=hour)
    if candidate <= now_utc:
        prev_candidates.append(candidate)
        break

if not prev_candidates:
    yesterday = today - timedelta(days=1)
    prev_candidates.append(yesterday.replace(hour=16))

prev_funding = max(prev_candidates)
time_since_prev = now_utc - prev_funding
since_hours, since_remainder = divmod(time_since_prev.total_seconds(), 3600)
since_minutes, since_seconds = divmod(since_remainder, 60)

# Timer display
st.header("Funding Schedule")
col3, col4 = st.columns(2)
col3.info(f"Next funding: {int(hours):02d}:{int(minutes):02d}")
col4.info(f"Last funding: {int(since_hours):02d}:{int(since_minutes):02d} ago")

# Time period selector for charts
st.header("Charts")
time_options = ["Last 24 hours", "Last 7 days", "Last 30 days", "All time"]
selected_time = st.selectbox("Select time period:", time_options)

# Filter data based on selected time period
now_utc_pd = pd.Timestamp(now_utc)  # Convert to pandas timestamp with timezone
if selected_time == "Last 24 hours":
    chart_data = filtered_df[filtered_df["timestamp"] >= now_utc_pd - pd.Timedelta(days=1)]
elif selected_time == "Last 7 days":
    chart_data = filtered_df[filtered_df["timestamp"] >= now_utc_pd - pd.Timedelta(days=7)]
elif selected_time == "Last 30 days":
    chart_data = filtered_df[filtered_df["timestamp"] >= now_utc_pd - pd.Timedelta(days=30)]
else:  # All time
    chart_data = filtered_df

# Only proceed with charts if we have data for the selected period
if not chart_data.empty:
    # Chart type selector
    chart_options = ["Funding Rate", "BTC Balance", "Price", "Profit"]
    selected_chart = st.selectbox("Select chart type:", chart_options)
    
    # Create and display the selected chart
    if selected_chart == "Funding Rate":
        fig = px.line(chart_data, x="timestamp", y="fundingRate", 
                      title=f"Funding Rate Over Time ({source_label})",
                      labels={"timestamp": "Date", "fundingRate": "Funding Rate %"})
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_chart == "BTC Balance":
        fig = px.line(chart_data, x="timestamp", y="btc_balance", 
                      title=f"BTC Balance Over Time ({source_label})",
                      labels={"timestamp": "Date", "btc_balance": "BTC Balance"})
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_chart == "Price":
        fig = px.line(chart_data, x="timestamp", y="price", 
                      title=f"BTC Price Over Time ({source_label})",
                      labels={"timestamp": "Date", "price": "BTC Price (USDT)"})
        st.plotly_chart(fig, use_container_width=True)
    
    elif selected_chart == "Profit":
        fig = px.line(chart_data, x="timestamp", y="profit", 
                      title=f"Profit Over Time ({source_label})",
                      labels={"timestamp": "Date", "profit": "Profit"})
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning(f"No data available for {selected_time.lower()} in {source_label} mode")

# Stats summary
if not chart_data.empty:
    st.header("Period Statistics")
    period_stats = {
        "Average Funding Rate": f"{chart_data['fundingRate'].mean():.6f}%",
        "Max Funding Rate": f"{chart_data['fundingRate'].max():.6f}%",
        "Min Funding Rate": f"{chart_data['fundingRate'].min():.6f}%",
        "Total Profit": f"{chart_data['profit'].sum():.8f} BTC"
    }
    
    stats_cols = st.columns(2)
    for i, (key, value) in enumerate(period_stats.items()):
        stats_cols[i % 2].metric(key, value)

# Recent data table
st.header(f"Latest {source_label.capitalize()} Funding Rates")
latest_data = filtered_df.sort_values("timestamp", ascending=False).head(5)
latest_data = latest_data[["timestamp", "fundingRate", "price", "profit"]]
latest_data.columns = ["Time (UTC)", "Funding Rate", "BTC Price", "Profit"]
st.dataframe(latest_data, use_container_width=True)

# Footer
st.markdown("---")
st.caption(f"Data refreshes hourly at :01 minutes | Viewing {source_label} data") 