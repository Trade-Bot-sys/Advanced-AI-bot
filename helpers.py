helpers.py

import json from datetime import datetime

HOLDINGS_FILE = "holdings.json"

def load_holdings(): try: with open(HOLDINGS_FILE, "r") as f: return json.load(f) except: return {}

def save_holdings(data): with open(HOLDINGS_FILE, "w") as f: json.dump(data, f, indent=2, default=str)

def log_exit_trade(symbol, exit_price, reason, exit_time): with open("trade_log.csv", "a") as f: f.write(f"{exit_time},{symbol},SELL,1,{exit_price},{reason},,\n")

def pretty_time(ts): return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")

=== Backtest Utility ===

def run_backtest(df, model, scaler): from sklearn.metrics import accuracy_score

df = df.copy()
df.dropna(inplace=True)

df["Return"] = df["Close"].pct_change()
df["MA10"] = df["Close"].rolling(window=10).mean()
df["MA20"] = df["Close"].rolling(window=20).mean()
df["RSI"] = compute_rsi(df["Close"], 14)
df["Target"] = np.where(df["Return"].shift(-1) > 0, 1, 0)

df.dropna(inplace=True)

features = ["MA10", "MA20", "RSI"]
X = df[features]
y = df["Target"]

X_scaled = scaler.transform(X)
y_pred = model.predict(X_scaled)

df["Signal"] = y_pred
df["Strategy Return"] = df["Return"] * df["Signal"]
df["Equity Curve"] = (1 + df["Strategy Return"]).cumprod()

accuracy = accuracy_score(y, y_pred)
total_return = df["Equity Curve"].iloc[-1] - 1
win_rate = sum((df["Signal"] == 1) & (df["Return"] > 0)) / max(sum(df["Signal"] == 1), 1)

return {
    "equity": df[["Equity Curve"]],
    "df": df,
    "accuracy": accuracy,
    "return": total_return,
    "win_rate": win_rate
}

Reusing RSI computation

import numpy as np import pandas as pd

def compute_rsi(series, period=14): delta = series.diff() gain = delta.clip(lower=0) loss = -delta.clip(upper=0)

avg_gain = gain.rolling(window=period).mean()
avg_loss = loss.rolling(window=period).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))
return rsi

