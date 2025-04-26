#!/bin/bash

# Optional: Activate your virtual environment
# source venv/bin/activate

echo "🚀 Starting Arbitrage Bot + Dashboard..."

# Start the bot scheduler in background
echo "⏱️ Launching hourly bot scheduler..."
python src/Trading_Bot/Bot_Launcher.py &

# Small delay to ensure Streamlit has time to load
sleep 2

# Start the Streamlit dashboard
echo "📊 Launching Streamlit dashboard..."
python -m streamlit run Dashoard.py &

# Wait a moment before exposing via tunnel
sleep 3

# Launch localtunnel
echo "🌐 Exposing dashboard using localtunnel..."
lt --port 8501
