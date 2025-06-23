# websocket_data.py

from collections import defaultdict
import pandas as pd
from datetime import datetime

# Store real-time candle data per symbol
candles = defaultdict(list)

def update_realtime_candle(symbol, ltp):
    now = datetime.now().replace(second=0, microsecond=0)
    if not candles[symbol] or candles[symbol][-1]["timestamp"] != now:
        # Start new candle
        candles[symbol].append({
            "timestamp": now,
            "Open": ltp,
            "High": ltp,
            "Low": ltp,
            "Close": ltp
        })
    else:
        # Update existing candle
        candle = candles[symbol][-1]
        candle["High"] = max(candle["High"], ltp)
        candle["Low"] = min(candle["Low"], ltp)
        candle["Close"] = ltp

def get_realtime_candles(symbol):
    if symbol not in candles:
        return pd.DataFrame()
    return pd.DataFrame(candles[symbol]).set_index("timestamp")
