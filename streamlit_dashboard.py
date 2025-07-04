import os
import json
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import base64
import pickle
import http.client
from datetime import datetime
import requests
import joblib
import gspread

# ✅ Load trained AI model
try:
    model = joblib.load("ai_model/advanced_model.pkl")
    print("✅ Model loaded successfully.")
except Exception as e:
    model = None
    print(f"❌ Model loading failed: {e}")

# ✅ This must be the first Streamlit command
st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")

from generate_access_token import generate_token
from alerts import send_telegram_alert, send_trade_summary_email
from executor import place_order, get_live_price
from strategies import get_final_signal, should_exit_trade
from scheduler import schedule_daily_trade, get_market_status
from helpers import load_holdings, save_holdings, run_backtest
from manual_trade import manual_trade_ui
from angel_api import place_order, cancel_order, get_ltp, get_trade_book
from utils import convert_to_ist
print("✅ Dashboard started")

GIST_RAW_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

def fetch_access_token_from_gist(gist_url):
    try:
        response = requests.get(gist_url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error("❌ Failed to fetch access_token.json from Gist")
            return None
    except Exception as e:
        st.error(f"❌ Error fetching access_token.json: {e}")
        return None

def is_token_fresh():
    try:
        file_path = "access_token.json"
        if not os.path.exists(file_path):
            return False
        token_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
        return token_time == datetime.now().date()
    except:
        return False

tokens = fetch_access_token_from_gist(GIST_RAW_URL)

if tokens:
    with open("access_token.json", "w") as f:
        json.dump(tokens, f, indent=2)

if not tokens or not is_token_fresh():
    st.warning("⚠️ Token not fresh. Regenerating...")
    generate_token()
    tokens = fetch_access_token_from_gist(GIST_RAW_URL)
    if tokens:
        with open("access_token.json", "w") as f:
            json.dump(tokens, f, indent=2)
    else:
        st.error("❌ Failed to fetch token even after regeneration.")
        st.stop()

try:
    token_time = datetime.fromtimestamp(os.path.getmtime("access_token.json"))
    st.sidebar.markdown(f"📅 Token refreshed: **{token_time.strftime('%Y-%m-%d %H:%M:%S')}**")
except:
    st.sidebar.warning("⚠️ Token timestamp not available.")

if tokens:
    access_token = tokens.get("access_token")
    feed_token = tokens.get("feed_token")
    api_key = tokens.get("api_key")
    client_code = tokens.get("client_code")
else:
    st.stop()

def decode_and_save_base64(input_file, output_file):
    with open(input_file, "rb") as f:
        base64_data = f.read()
    decoded_data = base64.b64decode(base64_data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(decoded_data)

MODEL_PATH = "ai_model/advanced_model.pkl"
try:
    with open(MODEL_PATH, "rb") as f:
        ai_model = pickle.load(f)
    print("✅ AI model loaded successfully")
except Exception as e:
    ai_model = None
    print(f"❌ Failed to load AI model: {e}")

print("✅ Dashboard initialization complete")
print("✅ App started")

st.title("📈 Smart AI Trading Dashboard - Angel One")
st.sidebar.markdown(f"🕒 Market Status: **{get_market_status()}**")

API_KEY = tokens.get("api_key")
JWT_TOKEN = tokens.get("access_token")
CLIENT_CODE = tokens.get("client_code")
LOCAL_IP = os.getenv('CLIENT_LOCAL_IP')
PUBLIC_IP = os.getenv('CLIENT_PUBLIC_IP')
MAC_ADDRESS = os.getenv('MAC_ADDRESS')

def get_available_funds():
    try:
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        headers = {
            'Authorization': f'Bearer {JWT_TOKEN}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': os.getenv('CLIENT_LOCAL_IP'),
            'X-ClientPublicIP': os.getenv('CLIENT_PUBLIC_IP'),
            'X-MACAddress': os.getenv('MAC_ADDRESS'),
            'X-PrivateKey': os.getenv('API_KEY')
        }
        conn.request("GET", "/rest/secure/angelbroking/user/v1/getRMS", headers=headers)
        res = conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))
    except Exception as e:
        return {"status": False, "error": str(e)}

funds = get_available_funds()
if funds.get("status"):
    available_funds = float(funds['data']['availablecash'])
    st.metric("💰 Available Cash", f"₹ {available_funds}")
else:
    available_funds = 0
    st.error(f"Failed to fetch funds: {funds.get('error')}")

try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

st.sidebar.header("⚙️ Trade Settings")
def_tp = st.sidebar.number_input("Take Profit (₹)", value=10.0)
def_sl = st.sidebar.number_input("Stop Loss (₹)", value=5.0)
def_qty = st.sidebar.number_input("Quantity", value=1)

from oauth2client.service_account import ServiceAccountCredentials

# Define required columns globally to avoid NameError
required_columns = [
    "timestamp", "symbol", "action", "qty", "entry", "tp", "sl", "exit_price", "pnl", "status",
    "strategy", "reason", "holding_days", "exit_time", "trailing_sl_used",
    "market_condition", "model_confidence"
]

# Load credentials from environment
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if GOOGLE_CREDENTIALS_JSON:
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Try loading the sheet
        sheet = client.open_by_key("1GTmmYKh6cFwtSTpWATMDoL0Z0RgQ5OWNaHklOeUXPQs").worksheet("TradeLog")
        records = sheet.get_all_records()

        # Create dataframe from records or empty columns
        if records:
            df_trades = pd.DataFrame(records)
        else:
            df_trades = pd.DataFrame(columns=required_columns)

        # Ensure all required columns exist
        for col in required_columns:
            if col not in df_trades.columns:
                df_trades[col] = None

        st.success("✅ Loaded trade log from Google Sheets with full detail.")

    except Exception as e:
        st.error(f"❌ Google Sheets load failed: {e}")
        df_trades = pd.DataFrame(columns=required_columns)
else:
    st.error("❌ Google credentials environment variable (GOOGLE_CREDENTIALS_JSON) missing.")
    df_trades = pd.DataFrame(columns=required_columns)
    
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
        st.sidebar.write(f"🟢 Entry: ₹{entry_price:.2f}")
        st.sidebar.write(f"📈 Live: ₹{live_price:.2f}")
        st.sidebar.write(f"💰 PnL: ₹{pnl:.2f}")
        st.sidebar.write("---")
else:
    st.sidebar.success("✅ No current holdings.")

st.sidebar.header("📈 Bot Traded Stock Chart")
bot_symbols = sorted(df_trades["symbol"].unique().tolist())
bot_stock = st.sidebar.selectbox("View Traded Stock", bot_symbols)

if bot_stock:
    st.subheader(f"📊 Live Chart: {bot_stock}")
    chart_df = yf.download(bot_stock, period="7d", interval="15m")
    fig = go.Figure()

    fig.add_trace(go.Candlestick(
        x=chart_df.index, open=chart_df["Open"],
        high=chart_df["High"], low=chart_df["Low"],
        close=chart_df["Close"], name="Candles"))

    trades = df_trades[df_trades["symbol"] == bot_stock]
    for _, row in trades.iterrows():
        fig.add_trace(go.Scatter(
            x=[row["timestamp"]], y=[row["entry"]],
            mode="markers+text", name=row["action"],
            text=row["action"], textposition="top center",
            marker=dict(size=10, color="green" if row["action"] == "BUY" else "red")
        ))

    st.plotly_chart(fig, use_container_width=True)

manual_trade_ui(STOCK_LIST, def_tp, def_sl, available_funds)

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
    else:
        pnl = (current_price - entry) * qty
        st.info(f"📌 Holding {symbol} | PnL ₹{pnl:.2f}")

#from utils import load_model  # or wherever your model loading function is
def load_model(path="ai_model/advanced_model.pkl"):
    """Load the trained AI model from .pkl file."""
    return joblib.load(path)

st.header("🧪 Backtest AI Strategy")
backtest_stock = st.selectbox("📉 Select Stock for Backtest", STOCK_LIST)

# --- Backtest Section ---
#st.subheader("🔁 Backtest a Stock")

#backtest_stock = st.text_input("Enter stock symbol (e.g. INFY.NS):", "RELIANCE.NS")

if st.button("Run Backtest"):
    if model is None:
        st.error("❌ AI Model not loaded. Please check advanced_model.pkl")
    else:
        try:
            df = yf.download(backtest_stock, period="6mo", interval="1d")
            if df.empty:
                st.warning("No data found for the selected stock.")
            else:
                result = run_backtest(df, model)

                if result:
                    st.success(f"Backtest completed for {backtest_stock}")
                    st.metric("📈 Accuracy", f"{result['accuracy']*100:.2f}%")
                    st.metric("💰 Total Return", f"{result['return']*100:.2f}%")
                    st.metric("✅ Win Rate", f"{result['win_rate']*100:.2f}%")
                    st.line_chart(result["equity"])
        except Exception as e:
            st.error(f"❌ Error running backtest: {e}")

if st.button("📩 Send Daily Trade Summary"):
    send_trade_summary_email()
    st.success("✅ Daily summary email sent.")

schedule_daily_trade()

st.success("✅ Smart AI Dashboard with Angel One, AI logic, auto trading, portfolio panel, and backtest support.")
