print("✅ Dashboard started")
import os
import json
import pandas as pd
import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import base64
def decode_and_save_base64(input_file, output_file):
    with open(input_file, "rb") as f:
        base64_data = f.read()
    decoded_data = base64.b64decode(base64_data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(decoded_data)
# 🔁 Decode model files if needed
if not os.path.exists("ai_model/model.pkl"):
    decode_and_save_base64("model.b64", "ai_model/model.pkl")

if not os.path.exists("ai_model/scaler.pkl"):
    decode_and_save_base64("scalar.b64", "ai_model/scaler.pkl")

from alerts import send_telegram_alert, send_trade_summary_email
from executor import place_order, get_live_price
#from strategies import get_final_signal, should_exit_trade
try:
    from strategies import get_final_signal, should_exit_trade
except Exception as e:
    print(f"❌ Error importing strategies: {e}")
    
from scheduler import schedule_daily_trade, get_market_status
from helpers import load_holdings, save_holdings, run_backtest
print("✅ App started")
st.set_page_config(layout="wide", page_title="Smart AI Trading Dashboard")
st.title("📈 Smart AI Trading Dashboard - Angel One")

st.sidebar.markdown(f"🕒 Market Status: **{get_market_status()}**")

with open("access_token.json") as f:
    token_data = json.load(f)
API_KEY = token_data["api_key"]
JWT_TOKEN = token_data["access_token"]

try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

st.sidebar.header("⚙️ Trade Settings")
def_tp = st.sidebar.number_input("Take Profit (₹)", value=10.0)
def_sl = st.sidebar.number_input("Stop Loss (₹)", value=5.0)
def_qty = st.sidebar.number_input("Quantity", value=1)

if os.path.exists("trade_log.csv"):
    df_trades = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
else:
    df_trades = pd.DataFrame(columns=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])

# ✅ Live Portfolio Panel
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

# ✅ Traded Stock Chart
st.sidebar.header("📈 Bot Traded Stock Chart")
bot_symbols = sorted(df_trades["symbol"].unique().tolist())
bot_stock = st.sidebar.selectbox("View Traded Stock", bot_symbols)

if bot_stock:
    st.subheader(f"📊 Live Chart: {bot_stock}")
    chart_df = yf.download(bot_stock, period="5d", interval="5m")
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

# ✅ Manual Trade Panel
st.sidebar.header("🧾 Manual Trading Panel")
selected_stock = st.sidebar.selectbox("Select Stock", STOCK_LIST)

if selected_stock:
    st.subheader(f"📉 Live Chart: {selected_stock}")
    chart_df = yf.download(selected_stock, period="5d", interval="5m")
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=chart_df.index, open=chart_df["Open"],
        high=chart_df["High"], low=chart_df["Low"],
        close=chart_df["Close"], name="Candles"))
    st.plotly_chart(fig, use_container_width=True)

    if st.button("📥 Manual Buy"):
        price = get_live_price(selected_stock)
        place_order(selected_stock, "BUY", def_qty)
        send_telegram_alert(selected_stock, "BUY", price, def_tp, def_sl)
        holdings[selected_stock] = {
            "entry": price,
            "qty": def_qty,
            "buy_time": datetime.now().isoformat()
        }
        save_holdings(holdings)
        with open("trade_log.csv", "a") as log:
            log.write(f"{datetime.now()},{selected_stock},BUY,{def_qty},{price},{def_tp},{def_sl}\n")
        st.success(f"✅ Manual BUY placed for {selected_stock} at ₹{price:.2f}")

    if st.button("📤 Manual Sell"):
        price = get_live_price(selected_stock)
        place_order(selected_stock, "SELL", def_qty)
        send_telegram_alert(selected_stock, "SELL", price, def_tp, def_sl)
        holdings.pop(selected_stock, None)
        save_holdings(holdings)
        with open("trade_log.csv", "a") as log:
            log.write(f"{datetime.now()},{selected_stock},SELL,{def_qty},{price},{def_tp},{def_sl}\n")
        st.success(f"✅ Manual SELL placed for {selected_stock} at ₹{price:.2f}")

# ✅ Auto Exit Based on AI
for symbol, data in holdings.items():
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

# ✅ Backtest Panel
st.header("🧪 Backtest AI Strategy")
backtest_stock = st.selectbox("📉 Select Stock for Backtest", STOCK_LIST)
if st.button("Run Backtest"):
    result = run_backtest(backtest_stock)
    if result:
        st.write("### 📊 Backtest Results")
        st.metric("Accuracy", f"{result['accuracy']:.2f}%")
        st.metric("Cumulative Return", f"{result['cumulative_return']:.2f}%")
        st.metric("Win Rate", f"{result['win_rate']:.2f}%")
        st.plotly_chart(result["fig"], use_container_width=True)
    else:
        st.error("❌ Failed to run backtest on selected stock.")

# ✅ Daily Scheduler
schedule_daily_trade()

# ✅ Manual Email Trigger
if st.button("📩 Send Daily Trade Summary"):
    send_trade_summary_email()
    st.success("✅ Daily summary email sent.")

# ✅ Done
st.success("✅ Smart AI Dashboard with Angel One, AI logic, auto trading, portfolio panel, and backtest support.")
