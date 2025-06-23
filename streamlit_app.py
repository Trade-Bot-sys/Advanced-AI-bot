# streamlit_app.py (Smart AI Dashboard with Nifty 35, WebSocket & AI Trades)
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
from alerts import send_telegram_alert, send_trade_summary_email, send_general_telegram_message
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
    st.sidebar.error("❌ Failed to fetch funds")

NIFTY_35 = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "LT", "SBIN", "KOTAKBANK",
    "AXISBANK", "HINDUNILVR", "ITC", "BHARTIARTL", "BAJFINANCE", "ASIANPAINT",
    "MARUTI", "HCLTECH", "WIPRO", "ULTRACEMCO", "TECHM", "NTPC", "TITAN",
    "POWERGRID", "JSWSTEEL", "SUNPHARMA", "ADANIENT", "ADANIPORTS", "DIVISLAB",
    "CIPLA", "ONGC", "GRASIM", "BPCL", "EICHERMOT", "COALINDIA", "HDFCLIFE"
]
STOCK_LIST = [f"{s}.NS" for s in NIFTY_35]

st.sidebar.header("⚙️ Trade Settings")
def_tp = st.sidebar.number_input("Take Profit (₹)", value=10.0)
def_sl = st.sidebar.number_input("Stop Loss (₹)", value=5.0)
def_qty = st.sidebar.number_input("Quantity", value=1)

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

st.sidebar.header("📈 Live Nifty 35 Chart")
selected_stock = st.sidebar.selectbox("Choose Stock", STOCK_LIST)

placeholder = st.empty()
latest_price = st.empty()

async def live_websocket_feed():
    url = f"wss://smartapisocket.angelone.in/smart-stream?clientCode={os.getenv('ANGEL_CLIENT_CODE')}&feedToken={os.getenv('ANGEL_FEED_TOKEN')}&apiKey={os.getenv('ANGEL_API_KEY')}"
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps({
            "task": "cn", "channel": "nse_cm|{symbol_token}", "token": os.getenv("ANGEL_FEED_TOKEN"), "user": os.getenv("ANGEL_CLIENT_CODE")
        }))

        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                ltp = float(data['ltp']) if 'ltp' in data else None
                ts = datetime.now()
                if ltp:
                    fig = go.Figure(go.Indicator(mode="number+delta", value=ltp, title=f"Live Price - {selected_stock}"))
                    placeholder.plotly_chart(fig, use_container_width=True)
                    signal = get_final_signal(selected_stock, ltp, ai_model)
                    if signal == "BUY":
                        place_order(selected_stock, "BUY", def_qty)
                        send_telegram_alert(selected_stock, "BUY", ltp, def_tp, def_sl)
                    elif signal == "SELL":
                        place_order(selected_stock, "SELL", def_qty)
                        send_telegram_alert(selected_stock, "SELL", ltp, def_tp, def_sl)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"WebSocket error: {e}")
                break

def start_websocket():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(live_websocket_feed())

threading.Thread(target=start_websocket, daemon=True).start()

manual_trade_ui(STOCK_LIST, def_tp, def_sl, available_funds)

# ✅ Holdings display
st.sidebar.header("📊 Holdings Portfolio")
holdings = load_holdings()
for symbol, data in holdings.copy().items():
    entry = data["entry"]
    qty = data["qty"]
    buy_time = datetime.fromisoformat(data["buy_time"])
    current_price = get_live_price(symbol)
    if should_exit_trade(symbol, entry, buy_time, def_tp, def_sl, trailing_buffer=2.5, max_days=3):
        place_order(symbol, "SELL", qty)
        send_telegram_alert(symbol, "SELL", current_price, 0, 0)
        holdings.pop(symbol, None)
        save_holdings(holdings)
        st.warning(f"🚨 Auto EXIT: {symbol} at ₹{current_price:.2f}")


# ✅ Chart section
st.sidebar.header("📈 Bot Traded Stock Chart")
bot_symbols = sorted(STOCK_LIST)
bot_stock = st.sidebar.selectbox("View Traded Stock", bot_symbols)

if bot_stock:
    st.subheader(f"📊 Live Chart: {bot_stock}")
    placeholder = st.empty()
    for _ in range(30):
        chart_df = live_price_df  # This should come from your websocket listener
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
