import os
import json
import pandas as pd
from datetime import datetime, time
from utils import convert_to_ist
from executor import (
    place_order,
    get_live_price,
    cancel_order,
    modify_order,
    get_order_book,
    get_trade_book,
    get_ltp,
    get_order_status
)
from alerts import send_telegram_alert
import yfinance as yf
import plotly.graph_objects as go
import joblib
import requests
from io import BytesIO
from funds import get_available_funds
from token_utils import fetch_access_token_from_gist
from model.signal_predictor import predict_signal
from fno_executor import place_order_fno

# ✅ Load access token
gist_url = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"
tokens = fetch_access_token_from_gist(gist_url)
access_token = tokens.get("access_token")

if not access_token:
    raise Exception("❌ Failed to fetch access token. Check Gist or token_utils.py.")

# ✅ Fetch available funds
funds_data = get_available_funds()
if funds_data and funds_data.get("status"):
    available_funds = float(funds_data['data'].get('availablecash', 0))
else:
    print(f"❌ Failed to fetch funds: {funds_data.get('error', 'Unknown error')}")
    available_funds = 0

# ✅ Load AI model from Gist (base64 .txt version)
model = None
try:
    model_url = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/nifty25_model_b64.txt"
    
    print("📥 Downloading model from Gist...")
    response = requests.get(model_url)
    response.raise_for_status()
    
    print("🧠 Decoding and loading model...")
    model_b64 = response.text.strip()
    model_bytes = base64.b64decode(model_b64)
    model = joblib.load(BytesIO(model_bytes))
    
    print("✅ Model loaded from Gist.")
except Exception as e:
    print(f"❌ Error loading model from Gist: {e}")

# ✅ Load stock list
try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# ✅ Trade configuration
TAKE_PROFIT = 10
STOP_LOSS = 3
TRAIL_BUFFER = 2
MAX_HOLD_DAYS = 5

portfolio = {}

def is_market_open():
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)


def run():
    for symbol in ["NIFTY", "BANKNIFTY"]:
        signal = predict_signal(symbol)
        place_order_fno(symbol, signal, qty=50)
        
def plot_trade_chart(symbol, entry_price, exit_price):
    try:
        df = yf.download(symbol, period="30d", interval="1d")
        df.dropna(inplace=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df["Close"], mode="lines", name="Price"))
        fig.add_trace(go.Scatter(x=[df.index[-1]], y=[entry_price], mode="markers+text",
                                 marker=dict(color="green", size=12), text=["BUY"],
                                 textposition="top center", name="BUY"))
        fig.add_trace(go.Scatter(x=[df.index[-1]], y=[exit_price], mode="markers+text",
                                 marker=dict(color="red", size=12), text=["SELL"],
                                 textposition="bottom center", name="SELL"))
        fig.update_layout(title=f"{symbol} Trade Chart", xaxis_title="Date", yaxis_title="Price")
        os.makedirs("charts", exist_ok=True)
        fig.write_html(f"charts/{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
    except Exception as e:
        print(f"❌ Chart error for {symbol}: {e}")

def compute_indicators_for_prediction(df):
    df['SMA'] = df['Close'].rolling(window=14).mean()
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df.dropna(inplace=True)
    return df

def predict_signal(symbol):
    if model is None:
        return "HOLD"
    try:
        df = yf.download(symbol, period="1mo", interval="1d", auto_adjust=True)
        if df.empty or len(df) < 20:
            return "HOLD"
        df = compute_indicators_for_prediction(df)
        latest = df[["SMA", "RSI", "MACD", "Signal"]].iloc[-1:]
        pred = model.predict(latest)[0]
        return "BUY" if pred == 1 else "SELL"
    except Exception as e:
        print(f"❌ Prediction error for {symbol}: {e}")
        return "HOLD"

def trade_logic():
    global available_funds
    if not is_market_open():
        print("⏰ Market is closed.")
        return
    print(f"🚀 Starting trade logic at {datetime.now()}")
    top_stocks = []
    trades_executed = False

    for symbol in STOCK_LIST:
        try:
            signal = predict_signal(symbol)
            if signal == "BUY":
                price = get_live_price(symbol)
                if price and available_funds >= price:
                    top_stocks.append(symbol)
        except Exception as e:
            msg = f"⚠️ Signal error on {symbol}: {e}"
            print(msg)
            send_telegram_alert(symbol, "ERROR", 0, reason=msg)

    top_stocks = top_stocks[:5]

    for symbol in top_stocks:
        try:
            if symbol in portfolio:
                continue

            entry_price = get_live_price(symbol)
            if not entry_price:
                print(f"❌ Could not fetch live price for {symbol}")
                continue

            max_qty = int(available_funds // entry_price)
            if max_qty < 1:
                print(f"⚠️ Not enough funds for {symbol}")
                continue

            response = place_order(symbol, "BUY", max_qty)
            print(f"📤 Order response for {symbol}: {response}")

            if response and isinstance(response, dict) and response.get("status"):
                portfolio[symbol] = {
                    "entry": entry_price,
                    "time": datetime.now(),
                    "qty": max_qty
                }
                available_funds -= max_qty * entry_price
                trades_executed = True
                print(f"✅ Bought {symbol} × {max_qty} at ₹{entry_price:.2f} | ₹{available_funds:.2f} left")
                send_telegram_alert(symbol, "BUY", entry_price, reason="AI Strategy")
            else:
                msg = f"❌ Failed to place BUY order for {symbol}: {response}"
                print(msg)
                send_telegram_alert(symbol, "ERROR", 0, reason=msg)

        except Exception as e:
            msg = f"❌ Order error for {symbol}: {e}"
            print(msg)
            send_telegram_alert(symbol, "ERROR", 0, reason=msg)

    if not trades_executed:
        msg = "⚠️ No trades executed today. All signals were HOLD or insufficient funds."
        print(msg)
        send_telegram_alert("BOT", "INFO", 0, reason=msg)


def monitor_holdings():
    for symbol, info in list(portfolio.items()):
        try:
            current_price = get_live_price(symbol)
            pnl = current_price - info["entry"]
            signal = predict_signal(symbol)
            time_held = (datetime.now() - info["time"]).days

            if (
                pnl >= TAKE_PROFIT or
                pnl <= -STOP_LOSS or
                signal == "SELL" or
                time_held >= MAX_HOLD_DAYS
            ):
                place_order(symbol, "SELL", info["qty"])
                send_telegram_alert(symbol, "SELL", current_price, reason="AI Exit/TP/SL")
                plot_trade_chart(symbol, info["entry"], current_price)
                with open("trade_log.csv", "a") as log:
                    log.write(f"{datetime.now()},{symbol},SELL,{info['qty']},{current_price},{pnl},AI_EXIT\n")
                del portfolio[symbol]
                print(f"💰 Sold {symbol} | PnL: ₹{pnl:.2f}")
        except Exception as e:
            print(f"❌ Monitoring error for {symbol}: {e}")
        
# ✅ Run the bot
if __name__ == "__main__":
    trade_logic()
    monitor_holdings()
