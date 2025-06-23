from collections import defaultdict
import pandas as pd
from datetime import datetime

# Dictionary to store real-time candle data per symbol
candles = defaultdict(list)

# 🟢 Called every time new LTP (last traded price) is received from WebSocket
def update_realtime_candle(symbol, ltp):
    now = datetime.now().replace(second=0, microsecond=0)
    if not candles[symbol] or candles[symbol][-1]["timestamp"] != now:
        # Start a new 1-minute candle
        candles[symbol].append({
            "timestamp": now,
            "Open": ltp,
            "High": ltp,
            "Low": ltp,
            "Close": ltp
        })
    else:
        # Update current candle
        candle = candles[symbol][-1]
        candle["High"] = max(candle["High"], ltp)
        candle["Low"] = min(candle["Low"], ltp)
        candle["Close"] = ltp

# 🔁 Returns a DataFrame of all 1-min candles for the symbol
def get_realtime_candles(symbol):
    if symbol not in candles:
        return pd.DataFrame()
    return pd.DataFrame(candles[symbol]).set_index("timestamp")
