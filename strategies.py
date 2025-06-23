import os
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from utils import convert_to_ist
from token_utils import fetch_model_from_gist
from websocket_data import get_realtime_candles  # <-- new module for WebSocket price data
import joblib

# === Load AI Model (From Gist) ===
MODEL_GIST_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/nifty25_model.pkl"
model = None
ai_enabled = False

try:
    model = fetch_model_from_gist(MODEL_GIST_URL)
    ai_enabled = True
    print("✅ AI model loaded from Gist.")
except Exception as e:
    print(f"⚠️ AI model load failed: {e}. Fallback to rule-based strategies.")

# === RSI Computation ===
def compute_rsi(prices, period=14):
    delta = np.diff(prices)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.convolve(gain, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(loss, np.ones(period)/period, mode='valid')
    rs = avg_gain / (avg_loss + 1e-6)
    rsi = 100 - (100 / (1 + rs))
    rsi = np.concatenate(([50]*(period-1), rsi))  # Pad with neutral RSI
    return rsi

# === 1. AI Signal Strategy ===
def get_ai_signal(symbol):
    if not ai_enabled or model is None:
        print(f"[AI] {symbol}: Model not loaded. Skipping AI strategy.")
        return "HOLD"

    try:
        df = get_realtime_candles(symbol, interval='1d', limit=90)
        if df.empty:
            raise ValueError("No price data from websocket")

        df["Return"] = df["close"].pct_change()
        df["MA10"] = df["close"].rolling(window=10).mean()
        df["MA20"] = df["close"].rolling(window=20).mean()
        df["RSI"] = compute_rsi(df["close"].values, 14)
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
def get_rsi_signal(symbol):
    try:
        df = get_realtime_candles(symbol, interval='1d', limit=30)
        if df.empty:
            raise ValueError("No RSI data")
        rsi = compute_rsi(df["close"].values, 14)[-1]
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
def get_sentiment_score(symbol):
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
def get_final_signal(symbol):
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

        if sentiment_score > 4:
            buy_votes += 1
        elif sentiment_score < 2:
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
def should_exit_trade(symbol, entry_price, buy_time, risk=1, reward=3, trailing_buffer=1.5, max_days=3):
    try:
        df = get_realtime_candles(symbol, interval="1m", limit=60*max_days)
        if df.empty:
            raise ValueError("No intraday data")

        current_price = df["close"].iloc[-1]
        days_held = (datetime.now() - buy_time).days
        profit = current_price - entry_price

        peak_price = df["close"].max()

        tp = risk * reward
        sl = risk

        if profit > 0 and current_price < (peak_price - trailing_buffer):
            print(f"🔽 Trailing SL hit for {symbol}")
            return True
        if profit >= tp:
            print(f"🎯 Take Profit hit ({tp}) for {symbol}")
            return True
        elif profit <= -sl:
            print(f"🛑 Stop Loss hit ({sl}) for {symbol}")
            return True
        elif days_held >= max_days:
            print(f"📅 Max hold duration hit for {symbol}")
            return True
        return False
    except Exception as e:
        print(f"[Exit Logic] Error for {symbol}: {e}")
        return False
