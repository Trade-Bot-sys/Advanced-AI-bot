import os
import json
import pandas as pd
from datetime import datetime, time
from executor import place_order, get_live_price
from alerts import send_telegram_alert
from strategies import get_final_signal, should_exit_trade, plot_trade_chart

# ✅ Load token
with open("access_token.json") as f:
    token_data = json.load(f)

# ✅ Load stock list
try:
    df_stocks = pd.read_csv("nifty500list.csv")
    STOCK_LIST = [f"{s.strip()}.NS" for s in df_stocks["Symbol"] if isinstance(s, str)]
except:
    STOCK_LIST = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

# ✅ Trade config
TAKE_PROFIT = 10  # ₹
STOP_LOSS = 3      # ₹
QUANTITY = 1
TRAIL_BUFFER = 2   # ₹
MAX_HOLD_DAYS = 5

# Trade tracker
portfolio = {}

# ✅ Market timing
def is_market_open():
    now = datetime.now().time()
    return time(9, 15) <= now <= time(15, 30)

# ✅ Core Trade Logic
def trade_logic():
    if not is_market_open():
        print(f"⏰ Market closed. Skipping at {datetime.now()} 🚫")
        return

    print(f"🚀 Running trade logic at {datetime.now()}...")

    top_stocks = []
    for symbol in STOCK_LIST:
        try:
            signal = get_final_signal(symbol)
            if signal == "BUY":
                top_stocks.append(symbol)
        except Exception as e:
            print(f"⚠️ Error on {symbol}: {e}")

    top_stocks = top_stocks[:5]

    for symbol in top_stocks:
        try:
            if symbol in portfolio:
                print(f"⏸️ Already in portfolio: {symbol}")
                continue

            entry_price = get_live_price(symbol)
            place_order(symbol, "BUY", QUANTITY)
            portfolio[symbol] = {
                "entry": entry_price,
                "time": datetime.now()
            }

            send_telegram_alert(symbol, "BUY", entry_price, TAKE_PROFIT, STOP_LOSS)
            with open("trade_log.csv", "a") as log:
                log.write(f"{datetime.now()},{symbol},BUY,{QUANTITY},{entry_price},{TAKE_PROFIT},{STOP_LOSS}\n")

            print(f"✅ Bought {symbol} at ₹{entry_price}")
        except Exception as e:
            print(f"❌ Trade error for {symbol}: {e}")

# ✅ Check existing holdings for exit
def monitor_holdings():
    for symbol, info in list(portfolio.items()):
        try:
            should_exit = should_exit_trade(
                symbol,
                entry_price=info["entry"],
                buy_time=info["time"],
                tp=TAKE_PROFIT,
                sl=STOP_LOSS,
                trailing_buffer=TRAIL_BUFFER,
                max_days=MAX_HOLD_DAYS
            )

            if should_exit:
                place_order(symbol, "SELL", QUANTITY)
                pnl = get_live_price(symbol) - info["entry"]
                send_telegram_alert(symbol, "SELL", get_live_price(symbol), pnl, "Exit")
                plot_trade_chart(symbol, info["entry"], get_live_price(symbol))
                del portfolio[symbol]
                print(f"💰 Sold {symbol} with PnL: ₹{pnl:.2f}")
        except Exception as e:
            print(f"❌ Exit check failed for {symbol}: {e}")

# ✅ Entry point
if __name__ == "__main__":
    trade_logic()
    monitor_holdings()