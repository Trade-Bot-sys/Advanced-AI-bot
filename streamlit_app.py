# ai_trading_dashboard.py
import os
import json
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import base64
import joblib
import http.client
from datetime import datetime
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")
st.title("📈 Smart AI Trading Dashboard - Angel One")

# ✅ Load AI model
try:
    ai_model = joblib.load("ai_model/advanced_model.pkl")
    print("✅ AI model loaded successfully.")
except Exception as e:
    ai_model = None
    print(f"❌ Failed to load AI model: {e}")

# ✅ Streamlit page config

# ✅ Imports
from generate_access_token import generate_token
from alerts import send_telegram_alert, send_trade_summary_email
from executor import get_live_price
from strategies import get_final_signal, should_exit_trade
from scheduler import schedule_daily_trade, get_market_status
from helpers import load_holdings, save_holdings, run_backtest
from manual_trade import manual_trade_ui
from angel_api import place_order, cancel_order, get_ltp, get_trade_book
from utils import convert_to_ist
from token_utils import fetch_access_token_from_gist, is_token_fresh
#from funds import get_available_funds
#from funds import fetch_access_token_from_gist

gist_url = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"
tokens = fetch_access_token_from_gist(gist_url) 
access_token = tokens.get("access_token")
# ✅ Validate and load tokens

if not tokens or not is_token_fresh():
    st.warning("⚠️ Token not fresh or missing.")
    st.stop()

# ✅ Extract tokens
access_token = tokens.get("access_token")
api_key = tokens.get("api_key")
client_code = tokens.get("client_code")

# ✅ Fetch and display funds
from funds import get_available_funds
# ✅ Fetch available funds using access_token
funds = get_available_funds()
if funds and funds.get("status"):
    available_funds = float(funds['data']['availablecash'])
    st.sidebar.metric("💰 Available Cash", f"₹ {available_funds:,.2f}")
else:
    available_funds = 0
    st.sidebar.error(funds.get("error", "Failed to fetch funds"))
    
# ✅ Load Nifty 500
try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS"]

# ✅ Sidebar Settings
st.sidebar.header("⚙️ Trade Settings")
def_tp = st.sidebar.number_input("Take Profit (₹)", value=10.0)
def_sl = st.sidebar.number_input("Stop Loss (₹)", value=5.0)
def_qty = st.sidebar.number_input("Quantity", value=1)

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
bot_symbols = sorted(df_trades["symbol"].dropna().unique().tolist())
bot_stock = st.sidebar.selectbox("View Traded Stock", bot_symbols)

if bot_stock:
    st.subheader(f"📊 Live Chart: {bot_stock}")
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
    st.plotly_chart(fig, use_container_width=True)

    # Show prediction
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
                if result:
                    st.success(f"Backtest completed for {backtest_stock}")
                    st.metric("📈 Accuracy", f"{result['accuracy']*100:.2f}%")
                    st.metric("💰 Total Return", f"{result['return']*100:.2f}%")
                    st.metric("✅ Win Rate", f"{result['win_rate']*100:.2f}%")
                    st.line_chart(result["equity"])
        except Exception as e:
            st.error(f"❌ Backtest error: {e}")

# ✅ Summary email
if st.button("📩 Send Daily Trade Summary"):
    send_trade_summary_email()
    st.success("✅ Daily summary email sent.")

# ✅ Scheduler start
schedule_daily_trade()
st.success("✅ Smart AI Dashboard loaded with Angel One auto trading and analytics support.")
