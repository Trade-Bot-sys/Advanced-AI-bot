import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import requests
from bs4 import BeautifulSoup
import re
import pickle
from datetime import datetime
import base64
import os

def decode_and_save_base64(input_file, output_file):
    with open(input_file, "rb") as f:
        base64_data = f.read()
    decoded_data = base64.b64decode(base64_data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "wb") as f:
        f.write(decoded_data)

# Decode and save
decode_and_save_base64("model.b64", "ai_model/model.pkl")
decode_and_save_base64("scaler.b64", "ai_model/scaler.pkl")

# === Load trained model ===
with open("ai_model/model.pkl", "rb") as f:
    model = pickle.load(f)

# === Load pre-fitted scaler ===
with open("ai_model/scaler.pkl", "rb") as f:
    scaler = pickle.load(f)

# === 1. AI Strategy ===
def get_ai_signal(symbol):
    try:
        df = yf.download(symbol, period="90d", interval="1d")
        df.dropna(inplace=True)

        df["Return"] = df["Close"].pct_change()
        df["MA10"] = df["Close"].rolling(window=10).mean()
        df["MA20"] = df["Close"].rolling(window=20).mean()
        df["RSI"] = compute_rsi(df["Close"], 14)
        df["Target"] = np.where(df["Return"].shift(-1) > 0, 1, 0)

        features = ["MA10", "MA20", "RSI"]
        df.dropna(inplace=True)

        X = df[features]
        latest = scaler.transform([X.iloc[-1]])
        prediction = model.predict(latest)

        return "BUY" if prediction[0] == 1 else "SELL"
    except Exception as e:
        print(f"[AI Strategy] Error for {symbol}: {e}")
        return "HOLD"

# === 2. RSI Strategy ===
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_rsi_signal(symbol):
    try:
        df = yf.download(symbol, period="1mo", interval="1d")
        rsi = compute_rsi(df["Close"], 14).iloc[-1]

        if rsi < 30:
            return "BUY"
        elif rsi > 70:
            return "SELL"
        else:
            return "HOLD"
    except Exception as e:
        print(f"[RSI Strategy] Error for {symbol}: {e}")
        return "HOLD"

# === 3. News Sentiment Strategy ===
def get_sentiment_score(symbol):
    try:
        query = symbol.replace(".NS", "")
        url = f"https://www.google.com/search?q={query}+stock+news"
        headers = {"User-Agent": "Mozilla/5.0"}

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        results = soup.find_all("div", class_=re.compile("BNeawe vvjwJb AP7Wnd"))
        score = len(results)

        return score
    except Exception as e:
        print(f"[News Sentiment] Error for {symbol}: {e}")
        return 0

# === 4. Multi-Strategy Signal ===
def get_final_signal(symbol):
    try:
        ai_signal = get_ai_signal(symbol)
        rsi_signal = get_rsi_signal(symbol)
        sentiment_score = get_sentiment_score(symbol)

        buy_votes = 0
        sell_votes = 0

        if ai_signal == "BUY": buy_votes += 1
        if rsi_signal == "BUY": buy_votes += 1
        if sentiment_score > 4: buy_votes += 1

        if ai_signal == "SELL": sell_votes += 1
        if rsi_signal == "SELL": sell_votes += 1
        if sentiment_score < 2: sell_votes += 1

        if buy_votes >= 2:
            return "BUY"
        elif sell_votes >= 2:
            return "SELL"
        else:
            return "HOLD"
    except Exception as e:
        print(f"[Final Signal] Error for {symbol}: {e}")
        return "HOLD"

# === 5. Exit Logic with Trailing SL, TP/SL, Max Hold ===
def should_exit_trade(symbol, entry_price, buy_time, tp, sl, trailing_buffer, max_days):
    try:
        current_price = yf.download(symbol, period="1d", interval="1m")["Close"][-1]
        days_held = (datetime.now() - buy_time).days
        profit = current_price - entry_price

        # Trailing Stop Loss: lock profit if current drops ₹2 from peak
        df_hist = yf.download(symbol, period="5d", interval="1m")
        peak_price = df_hist["Close"].max()
        if profit > 0 and current_price < (peak_price - trailing_buffer):
            print(f"🔽 Trailing SL triggered for {symbol}")
            return True

        if profit >= tp:
            print(f"🎯 TP hit for {symbol}")
            return True
        elif profit <= -sl:
            print(f"🛑 SL hit for {symbol}")
            return True
        elif days_held >= max_days:
            print(f"📅 Max hold days reached for {symbol}")
            return True
        else:
            return False
    except Exception as e:
        print(f"[Exit Logic] Error for {symbol}: {e}")
        return False
