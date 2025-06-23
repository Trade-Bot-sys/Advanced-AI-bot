# streamlit_app.py (Final AI Trading Dashboard with Angel One + WebSocket + Token + Nifty 35)
import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import base64
import joblib
import requests
import asyncio
import websockets
import threading
from datetime import datetime
from io import BytesIO
from alerts import send_telegram_alert, send_trade_summary_email
from generate_access_token import generate_token
from executor import place_order, get_live_price
from strategies import get_final_signal, should_exit_trade
from scheduler import schedule_daily_trade
from helpers import load_holdings, save_holdings, run_backtest
from manual_trade import manual_trade_ui
from angel_api import get_ltp
from utils import convert_to_ist
from token_utils import is_token_fresh
from funds import get_available_funds

st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")
st.title("📈 Smart AI Trading Dashboard - Angel One")

# === Token Refresh ===
params = st.query_params
if 'refresh' in params:
    st.title("🔄 Angel One Token Refresh")
    try:
        generate_token()
        send_telegram_alert("SYSTEM", "REFRESH", 0, 0, 0, reason="Token refreshed")
        st.success("✅ Token refreshed successfully!")
        st.stop()
    except Exception as e:
        st.error(f"❌ Failed to refresh token: {e}")
        st.stop()

# === Load AI Model ===
MODEL_GIST_URL = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/nifty25_model_b64.txt"
@st.cache_resource(show_spinner="Loading AI model...")
def load_model():
    response = requests.get(MODEL_GIST_URL)
    base64_str = response.text.strip()
    model_bytes = BytesIO(base64.b64decode(base64_str))
    return joblib.load(model_bytes)

try:
    ai_model = load_model()
    st.sidebar.success("✅ AI model loaded")
except Exception as e:
    ai_model = None
    st.sidebar.error(f"❌ AI model load error: {e}")

# === Funds Info ===
funds = get_available_funds()
available_cash = float(funds["data"].get("availablecash", 0.0)) if funds.get("status") else 0.0
st.sidebar.metric("💰 Available Cash", f"₹ {available_cash:,.2f}")

# === Stock List ===
NIFTY_35 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "SBIN", "KOTAKBANK",
    "AXISBANK", "HINDUNILVR", "ITC", "BHARTIARTL", "BAJFINANCE", "ASIANPAINT",
    "MARUTI", "HCLTECH", "WIPRO", "ULTRACEMCO", "TECHM", "NTPC", "TITAN",
    "POWERGRID", "JSWSTEEL", "SUNPHARMA", "ADANIENT", "ADANIPORTS", "DIVISLAB",
    "CIPLA", "ONGC", "GRASIM", "BPCL", "EICHERMOT", "COALINDIA", "HDFCLIFE"
]
STOCK_LIST = [f"{s}.NS" for s in NIFTY_35]

# === Trade Settings ===
def_tp = st.sidebar.number_input("Take Profit (₹)", value=15.0)
def_sl = st.sidebar.number_input("Stop Loss (₹)", value=5.0)
def_qty = st.sidebar.number_input("Quantity", value=1)

# === Live Price Panel ===
st.sidebar.header("📈 Live Price")
selected_stock = st.sidebar.selectbox("Choose Stock", STOCK_LIST)
placeholder = st.empty()

# === Load Master Symbol Token ===
@st.cache_data
def load_master():
    return pd.read_csv("master.csv")

symbol_token_df = load_master()
def get_token(symbol):
    try:
        token_row = symbol_token_df[symbol_token_df['symbol'] == symbol.replace(".NS", "")]
        return str(token_row.iloc[0]['token'])
    except IndexError:
        print(f"⚠️ Token not found for: {symbol}")
        return ""

# === WebSocket Feed ===
async def live_websocket():
    token = get_token(selected_stock)
    ws_url = f"wss://smartapisocket.angelone.in/smart-stream?clientCode={os.getenv('ANGEL_CLIENT_CODE')}&feedToken={os.getenv('ANGEL_FEED_TOKEN')}&apiKey={os.getenv('ANGEL_API_KEY')}"

    async with websockets.connect(ws_url) as ws:
        await ws.send(json.dumps({
            "task": "cn",
            "channel": f"nse_cm|{token}",
            "token": os.getenv("ANGEL_FEED_TOKEN"),
            "user": os.getenv("ANGEL_CLIENT_CODE")
        }))

        async def ping():
            while True:
                await ws.send(json.dumps({"task": "ping"}))
                await asyncio.sleep(30)

        asyncio.create_task(ping())

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                if 'ltp' in data:
                    ltp = float(data['ltp'])
                    fig = go.Figure(go.Indicator(mode="number+delta", value=ltp, title=f"Live Price: {selected_stock}"))
                    placeholder.plotly_chart(fig, use_container_width=True)

                    # === Signal Check ===
                    signal = get_final_signal(selected_stock, ltp, ai_model)
                    if signal == "BUY":
                        place_order(selected_stock, "BUY", def_qty)
                        send_telegram_alert(selected_stock, "BUY", ltp, def_tp, def_sl)
                    elif signal == "SELL":
                        place_order(selected_stock, "SELL", def_qty)
                        send_telegram_alert(selected_stock, "SELL", ltp, def_tp, def_sl)

                await asyncio.sleep(1)
            except Exception as e:
                st.error(f"WebSocket Error: {e}")
                break

# === Start WebSocket Thread ===
threading.Thread(target=lambda: asyncio.run(live_websocket()), daemon=True).start()

# === Manual Trade UI ===
manual_trade_ui(STOCK_LIST, def_tp, def_sl, available_cash)

# === Holdings Auto-Exit ===
st.sidebar.header("📊 Holdings Portfolio")
holdings = load_holdings()
for symbol, data in holdings.copy().items():
    entry = data["entry"]
    qty = data["qty"]
    buy_time = datetime.fromisoformat(data["buy_time"])
    current_price = get_live_price(symbol)
    if should_exit_trade(symbol, entry, buy_time, def_tp, def_sl):
        place_order(symbol, "SELL", qty)
        send_telegram_alert(symbol, "SELL", current_price, 0, 0)
        holdings.pop(symbol)
        save_holdings(holdings)
        st.warning(f"🚨 EXIT: {symbol} at ₹{current_price:.2f}")

# === Backtest Panel ===
st.header("🧪 Backtest AI Strategy")

bt_symbol = st.selectbox("Choose Stock", STOCK_LIST)

if st.button("Run Backtest"):
    try:
        df_all = pd.read_csv("nifty35_6years_yfinance.csv")  # ✅ Uploaded file
        df_symbol = df_all[df_all["Symbol"] == bt_symbol.replace(".NS", "")]
        if df_symbol.empty:
            st.warning(f"No historical data found for {bt_symbol}")
        else:
            result = run_backtest(df_symbol, ai_model)
            st.line_chart(result["df"]["Equity Curve"])
            st.metric("Accuracy", f"{result['accuracy']:.2%}")
            st.metric("Return", f"{result['return']:.2%}")
    except Exception as e:
        st.error(f"❌ Backtest Error: {e}")

# === Test Telegram ===
if st.button("📲 Test Telegram Alert"):
    send_telegram_alert("TEST", "BUY", 123.45, 130, 118, reason="Test Alert")
    st.success("✅ Alert sent")

# === Daily Scheduler ===
schedule_daily_trade()
st.success("✅ Dashboard fully loaded with Angel One, WebSocket, AI Model")
