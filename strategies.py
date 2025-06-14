import yfinance as yf
import pandas as pd
import numpy as np
import pickle
import os
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

# === Load AI Model (Without Scaler) ===
MODEL_PATH = "ai_model/advanced_model.pkl"

model = None
ai_enabled = False

try:
    if os.path.exists(MODEL_PATH):
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        ai_enabled = True
        print("✅ AI model loaded.")
    else:
        raise FileNotFoundError("advanced_model.pkl not found.")
except Exception as e:
    print(f"⚠️ AI model load failed: {e}. Fallback to rule-based strategies.")

# === RSI Computation ===
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# === 1. AI Signal Strategy ===
def get_ai_signal(symbol: str) -> str:
    if not ai_enabled or model is None:
        print(f"[AI] {symbol}: Model not loaded. Skipping AI strategy.")
        return "HOLD"

    try:
        df = yf.download(symbol, period="90d", interval="1d")
        df.dropna(inplace=True)

        df["Return"] = df["Close"].pct_change()
        df["MA10"] = df["Close"].rolling(window=10).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["RSI"] = compute_rsi(df["Close"], 14)
        df.dropna(inplace=True)

        features = ["MA10", "MA20", "RSI"]
        X = df[features]

        latest = X.iloc[-1].values.reshape(1, -1)
        prediction = model.predict(latest)[0]
        prob = model.predict_proba(latest)[0][1]

        print(f"[AI] {symbol}: Prediction = {prediction}, Confidence = {prob:.2f}")
        return "BUY" if prediction == 1 else "SELL"
    except Exception as e:
        print(f"[AI Strategy] Error for {symbol}: {e}")
        return "HOLD"

# === 2. RSI Signal Strategy ===
def get_rsi_signal(symbol: str) -> str:
    try:
        df = yf.download(symbol, period="1mo", interval="1d")
        if df.empty or "Close" not in df:
            raise ValueError("Insufficient data for RSI")

        rsi = compute_rsi(df["Close"], 14).iloc[-1]
        print(f"[RSI] {symbol}: RSI = {rsi:.2f}")

        if rsi < 30:
            return "BUY"
        elif rsi > 70:
            return "SELL"
        else:
            return "HOLD"
    except Exception as e:
        print(f"[RSI Strategy] Error for {symbol}: {e}")
        return "HOLD"

# === 3. News Sentiment Score ===
def get_sentiment_score(symbol: str) -> int:
    try:
        query = symbol.replace(".NS", "")
        url = f"https://www.google.com/search?q={query}+stock+news"
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")

        results = soup.find_all("div", class_=re.compile("BNeawe vvjwJb AP7Wnd"))
        score = len(results)

        print(f"[Sentiment] {symbol}: News count = {score}")
        return score
    except Exception as e:
        print(f"[News Sentiment] Error for {symbol}: {e}")
        return 0

# === 4. Multi-Strategy Signal Aggregator ===
def get_final_signal(symbol: str, sentiment_threshold_buy=4, sentiment_threshold_sell=2) -> str:
    try:
        ai_signal = get_ai_signal(symbol)
        rsi_signal = get_rsi_signal(symbol)
        sentiment_score = get_sentiment_score(symbol)

        buy_votes = 0
        sell_votes = 0

        if ai_signal == "BUY":
            buy_votes += 1
        elif ai_signal == "SELL":
            sell_votes += 1

        if rsi_signal == "BUY":
            buy_votes += 1
        elif rsi_signal == "SELL":
            sell_votes += 1

        if sentiment_score > sentiment_threshold_buy:
            buy_votes += 1
        elif sentiment_score < sentiment_threshold_sell:
            sell_votes += 1

        print(f"[Final Signal] {symbol} → BUY votes: {buy_votes}, SELL votes: {sell_votes}")

        if buy_votes >= 2:
            return "BUY"
        elif sell_votes >= 2:
            return "SELL"
        else:
            return "HOLD"
    except Exception as e:
        print(f"[Final Signal] Error for {symbol}: {e}")
        return "HOLD"

# === 5. Exit Logic ===
def should_exit_trade(symbol: str, entry_price: float, buy_time: datetime,
                      tp: float, sl: float, trailing_buffer: float = 2.5, max_days: int = 3) -> bool:
    try:
        df_now = yf.download(symbol, period="1d", interval="1m")
        if df_now.empty or "Close" not in df_now.columns:
            raise ValueError("No intraday data available")

        current_price = df_now["Close"][-1]
        days_held = (datetime.now() - buy_time).days
        profit = current_price - entry_price

        df_hist = yf.download(symbol, period="5d", interval="1m")
        peak_price = df_hist["Close"].max() if not df_hist.empty else current_price

        if profit > 0 and current_price < (peak_price - trailing_buffer):
            print(f"🔽 Trailing SL triggered for {symbol}")
            return True
        if profit >= tp:
            print(f"🎯 Take Profit hit for {symbol}")
            return True
        elif profit <= -sl:
            print(f"🛑 Stop Loss hit for {symbol}")
            return True
        elif days_held >= max_days:
            print(f"📅 Max hold days reached for {symbol}")
            return True
        else:
            return False
    except Exception as e:
        print(f"[Exit Logic] Error for {symbol}: {e}")
        return False
