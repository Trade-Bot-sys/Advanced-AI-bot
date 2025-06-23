# ai_trading_dashboard.py
import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import base64
import joblib
import requests
from datetime import datetime
from io import BytesIO
import asyncio
import websockets
import threading
import time
from alerts import send_telegram_alert, send_trade_summary_email, send_general_telegram_message
from generate_access_token import generate_token
from executor import get_live_price, place_order
from strategies import get_final_signal, should_exit_trade
from scheduler import schedule_daily_trade, get_market_status
from helpers import load_holdings, save_holdings, run_backtest
from manual_trade import manual_trade_ui
from angel_api import get_ltp, get_trade_book
from utils import convert_to_ist
from token_utils import fetch_access_token_from_gist, is_token_fresh
from funds import get_available_funds
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")
st.title("📈 Smart AI Trading Dashboard - Angel One")

params = st.query_params
if 'refresh' in params:
    st.title("🔄 Angel One Token Refresh")
    try:
        generate_token()
        send_general_telegram_message("✅ Angel One token refreshed at 8:30 AM IST.")
        st.success("✅ Token refreshed successfully via EasyCron!")
        st.stop()
    except Exception as e:
        send_general_telegram_message(f"❌ Token refresh failed: {e}")
        st.error(f"❌ Failed to refresh token: {e}")
        st.stop()

MODEL_GIST_URL = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/nifty25_model_b64.txt"

@st.cache_resource(show_spinner="🔄 Loading AI model from Gist...")
def load_model_from_gist():
    try:
        response = requests.get(MODEL_GIST_URL, timeout=30)
        response.raise_for_status()
        base64_str = response.text.strip()
        model_bytes = BytesIO(base64.b64decode(base64_str))
        model = joblib.load(model_bytes)
        return model
    except Exception as e:
        raise RuntimeError(f"Failed to load model: {e}")

try:
    ai_model = load_model_from_gist()
    st.sidebar.success("✅ AI Model loaded from Gist")
except Exception as e:
    ai_model = None
    st.sidebar.error(f"❌ Failed to load model: {e}")

funds_data = get_available_funds()
if funds_data and funds_data.get("status"):
    available_funds = float(funds_data["data"].get("availablecash", 0.0))
    st.sidebar.metric("💰 Available Cash", f"₹ {available_funds:,.2f}")
else:
    available_funds = 0.0
    st.sidebar.error(f"Failed to fetch funds: {funds_data.get('error', 'Unknown error')}")

STOCK_LIST = []
try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS"]

st.sidebar.header("⚙️ Trade Settings")
def_tp = st.sidebar.number_input("Take Profit (₹)", value=10.0)
def_sl = st.sidebar.number_input("Stop Loss (₹)", value=5.0)
def_qty = st.sidebar.number_input("Quantity", value=1)

# 🧠 Live WebSocket Feed
client_code = os.getenv("ANGEL_CLIENT_CODE")
feed_token = os.getenv("ANGEL_FEED_TOKEN")
api_key = os.getenv("ANGEL_API_KEY")

symbol_dropdown = st.sidebar.selectbox("📈 Select Nifty 35 Stock", ["RELIANCE-EQ", "INFY-EQ", "HDFCBANK-EQ", "TCS-EQ", "ICICIBANK-EQ"])
realtime_placeholder = st.empty()
live_prices = []

async def connect_websocket(symbol):
    url = f"wss://smartapisocket.angelone.in/smart-stream?clientCode={client_code}&feedToken={feed_token}&apiKey={api_key}"
    async with websockets.connect(url) as ws:
        sub_request = json.dumps({
            "action": 1,
            "params": {
                "mode": "LTP",
                "tokenList": [
                    {
                        "exchangeType": "1",
                        "symbolToken": symbol,
                        "productType": "EQUITY"
                    }
                ]
            }
        })
        await ws.send(sub_request)

        async def keep_alive():
            while True:
                try:
                    await ws.send('ping')
                except:
                    break
                await asyncio.sleep(30)

        asyncio.create_task(keep_alive())

        while True:
            response = await ws.recv()
            data = json.loads(response)
            if 'ltp' in data:
                live_prices.append(data)

                # AI Prediction + Action
                signal = get_final_signal(data['ltp'], ai_model)
                if signal == "BUY":
                    place_order(symbol_dropdown, "BUY", def_qty)
                    send_telegram_alert(symbol_dropdown, "BUY", data['ltp'], def_tp, def_sl)
                elif signal == "SELL":
                    place_order(symbol_dropdown, "SELL", def_qty)
                    send_telegram_alert(symbol_dropdown, "SELL", data['ltp'], def_tp, def_sl)

                fig = go.Figure()
                fig.add_trace(go.Scatter(y=[p['ltp'] for p in live_prices], mode="lines+markers", name=symbol_dropdown))
                realtime_placeholder.plotly_chart(fig, use_container_width=True)

threading.Thread(target=lambda: asyncio.run(connect_websocket(symbol_dropdown)), daemon=True).start()

# ✅ Google Sheet setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
required_columns = [
    "timestamp", "symbol", "action", "qty", "entry", "tp", "sl", "exit_price", "pnl", "status",
    "strategy", "reason", "holding_days", "exit_time", "trailing_sl_used", "market_condition", "model_confidence"
]
if GOOGLE_CREDENTIALS_JSON:
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key("1GTmmYKh6cFwtSTpWATMDoL0Z0RgQ5OWNaHklOeUXPQs").worksheet("TradeLog")
        records = sheet.get_all_records()
        df_trades = pd.DataFrame(records) if records else pd.DataFrame(columns=required_columns)
        for col in required_columns:
            if col not in df_trades.columns:
                df_trades[col] = None
        st.success("✅ Trade log loaded from Google Sheets")
    except Exception as e:
        st.error(f"❌ Google Sheet error: {e}")
        df_trades = pd.DataFrame(columns=required_columns)
else:
    st.error("❌ Google credentials not set")
    df_trades = pd.DataFrame(columns=required_columns)

# ✅ Holdings display
st.sidebar.header("📊 Holdings Portfolio")
holdings = load_holdings()
if holdings:
    for symbol, data in holdings.items():
        entry_price = data["entry"]
        qty = data["qty"]
        buy_time = datetime.fromisoformat(data["buy_time"])
        live_price = get_live_price(symbol)
        pnl = (live_price - entry_price) * qty
        st.sidebar.write(f"**{symbol}**")
        st.sidebar.write(f"🟢 Entry: ₹{entry_price:.2f} | 📈 Live: ₹{live_price:.2f} | 💰 PnL: ₹{pnl:.2f}")
        st.sidebar.write("---")
else:
    st.sidebar.success("✅ No current holdings.")

# ✅ Chart section
st.sidebar.header("📈 Bot Traded Stock Chart")
bot_symbols = sorted(STOCK_LIST)
bot_stock = st.sidebar.selectbox("View Traded Stock", bot_symbols)

if bot_stock:
    st.subheader(f"📊 Live Chart: {bot_stock}")
    placeholder = st.empty()
    for _ in range(30):
        chart_df = yf.download(bot_stock, period="7d", interval="15m")
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=chart_df.index, open=chart_df["Open"], high=chart_df["High"],
            low=chart_df["Low"], close=chart_df["Close"], name="Candles"))
        trades = df_trades[df_trades["symbol"] == bot_stock]
        for _, row in trades.iterrows():
            fig.add_trace(go.Scatter(
                x=[row["timestamp"]], y=[row["entry"]], mode="markers+text", name=row["action"],
                text=row["action"], textposition="top center",
                marker=dict(size=10, color="green" if row["action"] == "BUY" else "red")
            ))
        placeholder.plotly_chart(fig, use_container_width=True)
        time.sleep(30)

    if not trades.empty:
        latest_trade = trades.sort_values("timestamp", ascending=False).iloc[0]
        st.markdown("### 🧠 AI Prediction Details")
        st.markdown(f"""
        - **🛒 Action**: `{latest_trade['action']}`
        - **🤖 Confidence**: `{latest_trade.get('model_confidence', 'N/A')}`
        - **📊 RSI**: `{latest_trade.get('rsi', 'N/A')}` | MACD: `{latest_trade.get('macd', 'N/A')}` | Returns: `{latest_trade.get('returns', 'N/A')}`
        """)
        if pd.notnull(latest_trade.get("exit_price")):
            pnl = float(latest_trade["exit_price"]) - float(latest_trade["entry"])
            if latest_trade["action"] == "SELL":
                pnl *= -1
            st.metric("📈 Trade PnL", f"₹{pnl:.2f}")

# ✅ Manual trade
manual_trade_ui(STOCK_LIST, def_tp, def_sl, available_funds)

# ✅ Auto exit logic
for symbol, data in holdings.copy().items():
    entry = data["entry"]
    qty = data["qty"]
    buy_time = datetime.fromisoformat(data["buy_time"])
    current_price = get_live_price(symbol)
    if should_exit_trade(symbol, entry, buy_time, def_tp, def_sl, trailing_buffer=2.5, max_days=3):
        place_order(symbol, "SELL", qty)
        send_telegram_alert(symbol, "SELL", current_price, 0, 0)
        with open("trade_log.csv", "a") as log:
            log.write(f"{datetime.now()},{symbol},SELL,{qty},{current_price},0,0\n")
        holdings.pop(symbol, None)
        save_holdings(holdings)
        st.warning(f"🚨 Auto EXIT: {symbol} at ₹{current_price:.2f}")

# ✅ Backtest
st.header("🧪 Backtest AI Strategy")
backtest_stock = st.selectbox("📉 Select Stock for Backtest", STOCK_LIST)

if st.button("Run Backtest"):
    if ai_model is None:
        st.error("❌ AI Model not loaded.")
    else:
        try:
            df = yf.download(backtest_stock, period="6mo", interval="1d")
            if df.empty:
                st.warning("No data found for selected stock.")
            else:
                result = run_backtest(df, ai_model)
                st.success(f"✅ Backtest completed for {backtest_stock}")
                st.subheader("📊 Equity Curve")
                st.line_chart(result["df"]["Equity Curve"])
                st.subheader("📈 Stats")
                st.metric("Accuracy", f"{result['accuracy']:.2%}")
                st.metric("Return", f"{result['return']:.2%}")
                st.metric("Win Rate", f"{result['win_rate']:.2%}")
        except Exception as e:
            st.error(f"❌ Backtest error: {e}")

# ✅ Summary email
if st.button("📩 Send Daily Trade Summary"):
    send_trade_summary_email()
    st.success("✅ Daily summary email sent.")

st.header("🧪 Test Telegram Alert")
if st.button("📲 Send Test Alert to Telegram"):
    try:
        send_telegram_alert(
            symbol="TEST",
            action="BUY",
            price=123.45,
            tp=130,
            sl=118,
            confidence=0.92,
            features=[55.2, 0.67, 0.03],
            reason="Testing Telegram alert from dashboard"
        )
        st.success("✅ Test alert sent successfully to Telegram!")
    except Exception as e:
        st.error(f"❌ Failed to send alert: {e}")

# ✅ Scheduler start
schedule_daily_trade()
st.success("✅ Smart AI Dashboard loaded with Angel One auto trading and analytics support.")
