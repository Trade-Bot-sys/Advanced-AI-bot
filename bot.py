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
from ta.momentum import RSIIndicator
from ta.trend import MACD
#from streamlit_app import get_available_funds
from funds import get_available_funds
from token_utils import fetch_access_token_from_gist

# ✅ Load access token from Gist
access_token = fetch_access_token_from_gist()
if not access_token:
    raise Exception("❌ Failed to fetch access token. Check Gist or token_utils.py.")

# ✅ Fetch available funds
funds_data = get_available_funds()
if funds_data and funds_data.get("status"):
    available_funds = float(funds_data['data'].get('availablecash', 0))
else:
    print(f"❌ Failed to fetch funds: {funds_data.get('error', 'Unknown error')}")
    available_funds = 0

# ✅ Load AI model
model = joblib.load("ai_model/advanced_model.pkl")

# ✅ Load Nifty500 stock list
try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# ✅ Trade Configuration
TAKE_PROFIT = 10  # ₹
STOP_LOSS = 3     # ₹
TRAIL_BUFFER = 2  # ₹
MAX_HOLD_DAYS = 5

portfolio = {}

# ✅ Market timing check
def is_market_open():
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)

# ✅ Trade chart
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

# ✅ AI model prediction
def predict_signal(symbol):
    try:
        df = yf.download(symbol, period="5d", interval="15m")
        if df.empty or len(df) < 50:
            return "HOLD"
        df['RSI'] = RSIIndicator(df['Close']).rsi()
        df['MACD'] = MACD(df['Close']).macd()
        df['Returns'] = df['Close'].pct_change()
        df.dropna(inplace=True)
        latest = df[["RSI", "MACD", "Returns"]].iloc[-1:]
        pred = model.predict(latest)[0]
        return "BUY" if pred == 1 else "SELL" if pred == -1 else "HOLD"
    except Exception as e:
        print(f"❌ Prediction error for {symbol}: {e}")
        return "HOLD"

# ✅ Trade entry logic
def trade_logic():
    global available_funds
    if not is_market_open():
        print("⏰ Market is closed.")
        return
    print(f"🚀 Starting trade logic at {datetime.now()}")
    top_stocks = []

    for symbol in STOCK_LIST:
        try:
            signal = predict_signal(symbol)
            if signal == "BUY":
                price = get_live_price(symbol)
                if available_funds >= price:
                    top_stocks.append(symbol)
        except Exception as e:
            print(f"⚠️ Error on {symbol}: {e}")

    top_stocks = top_stocks[:5]

    for symbol in top_stocks:
        try:
            if symbol in portfolio:
                continue
            entry_price = get_live_price(symbol)
            max_qty = int(available_funds // entry_price)
            if max_qty >= 1:
                place_order(symbol, "BUY", max_qty)
                portfolio[symbol] = {
                    "entry": entry_price,
                    "time": datetime.now(),
                    "qty": max_qty
                }
                available_funds -= max_qty * entry_price
                print(f"✅ Bought {symbol} × {max_qty} at ₹{entry_price:.2f} | ₹{available_funds:.2f} left")
        except Exception as e:
            print(f"❌ Order error for {symbol}: {e}")

# ✅ Monitor and exit logic
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

# ✅ Entry point
if __name__ == "__main__":
    trade_logic()
    monitor_holdings()
