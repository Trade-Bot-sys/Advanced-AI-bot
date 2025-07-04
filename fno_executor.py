import pandas as pd
import datetime
import os
from angel_api import get_ltp, place_order  # ✅ your existing functions
from telegram.alert import send_alert

df_instruments = pd.read_csv("instruments.csv")  # Daily instrument file

def get_atm_option(symbol="NIFTY", option_type="CE"):
    try:
        ltp = float(get_ltp(symbol)["data"]["ltp"])
        nearest_strike = int(round(ltp / 50) * 50)  # Strike step for NIFTY

        expiry = df_instruments[
            (df_instruments["name"] == symbol) &
            (df_instruments["segment"] == "NFO-OPT")
        ]["expiry"].drop_duplicates().sort_values().iloc[0]

        row = df_instruments[
            (df_instruments["name"] == symbol) &
            (df_instruments["expiry"] == expiry) &
            (df_instruments["strike"] == nearest_strike) &
            (df_instruments["symbol"].str.endswith(option_type))
        ].iloc[0]

        return row["symbol"], row["token"], nearest_strike, expiry

    except Exception as e:
        send_alert(f"❌ Option fetch error: {e}")
        return None, None, None, None

def place_order_fno(symbol="NIFTY", signal="BUY", qty=50):
    if signal == "HOLD":
        send_alert(f"⚪ HOLD signal for {symbol}. No order placed.")
        return

    option_type = "CE" if signal == "BUY" else "PE"
    trading_symbol, token, strike, expiry = get_atm_option(symbol, option_type)

    if not trading_symbol:
        send_alert("❌ Failed to determine F&O option.")
        return

    order = {
        "variety": "NORMAL",
        "tradingsymbol": trading_symbol,
        "symboltoken": token,
        "transactiontype": "BUY",
        "exchange": "NFO",  # ✅ required for options
        "ordertype": "MARKET",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "quantity": qty
    }

    try:
        response = place_order(order)

        if isinstance(response, dict) and "data" in response and "orderid" in response["data"]:
            order_id = response["data"]["orderid"]
            send_alert(f"✅ {signal} {symbol} {strike}{option_type} | Qty: {qty} | Order ID: {order_id}")
            log_trade(symbol, trading_symbol, strike, signal, qty)
        else:
            send_alert(f"❌ Order failed: {response.get('message', 'Unknown error')}")

    except Exception as e:
        send_alert(f"❌ Order Exception: {e}")

def log_trade(symbol, trading_symbol, strike, signal, qty):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_row = pd.DataFrame([[timestamp, symbol, trading_symbol, strike, signal, qty]],
        columns=["timestamp", "symbol", "option", "strike", "signal", "qty"])

    log_file = "logs/trades.csv"
    if os.path.exists(log_file):
        log_row.to_csv(log_file, mode="a", header=False, index=False)
    else:
        log_row.to_csv(log_file, index=False)
