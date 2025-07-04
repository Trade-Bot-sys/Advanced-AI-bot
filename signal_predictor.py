# model/signal_predictor.py
import yfinance as yf

def predict_signal(symbol):
    df = yf.download(f"{symbol}.NS", period="7d", interval="1d")
    df['daily_return'] = df['Close'].pct_change()

    # Simple logic: if uptrend in last 2 days
    if df['daily_return'].iloc[-1] > 0 and df['daily_return'].iloc[-2] > 0:
        return "BUY"
    elif df['daily_return'].iloc[-1] < 0 and df['daily_return'].iloc[-2] < 0:
        return "SELL"
    else:
        return "HOLD"
