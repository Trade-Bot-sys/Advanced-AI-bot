# executor.py

import os
import json
import requests

# Load access token and API key
with open("access_token.json") as f:
    token_data = json.load(f)

API_KEY = token_data["api_key"]
JWT_TOKEN = token_data["access_token"]

# Common request headers for Angel One API
HEADERS = {
    "Authorization": f"Bearer {JWT_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "127.0.0.1",
    "X-MACAddress": "AA:BB:CC:DD:EE:FF",
    "X-PrivateKey": API_KEY
}

# Predefined symbol-token map (you can expand this)
SYMBOL_TOKEN_MAP = {
    "RELIANCE-EQ": "2885",
    "TCS-EQ": "11536",
    "HDFCBANK-EQ": "1333"
}

# ✅ Place an order via Angel One
def place_order(symbol, side, qty):
    try:
        sym = symbol.replace(".NS", "-EQ")
        token = SYMBOL_TOKEN_MAP.get(sym, "2885")
        order = {
            "variety": "NORMAL",
            "tradingsymbol": sym,
            "symboltoken": token,
            "transactiontype": side,  # BUY or SELL
            "exchange": "NSE",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": "0",
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(qty)
        }
        r = requests.post(
            "https://apiconnect.angelbroking.com/rest/secure/angelbroking/order/v1/placeOrder",
            headers=HEADERS, json=order
        )
        return r.json()
    except Exception as e:
        print("❌ Order Error:", e)
        return {}

# ✅ Get live price from Yahoo Finance as fallback
def get_live_price(symbol):
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}.NS"
        response = requests.get(url)
        data = response.json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except Exception as e:
        print(f"❌ Price Fetch Error for {symbol}: {e}")
        return None