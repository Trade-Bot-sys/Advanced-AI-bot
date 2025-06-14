# alerts.py
import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pandas as pd
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL = os.getenv("EMAIL_ADDRESS")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

def send_telegram_alert(symbol, action, price, tp, sl):
    try:
        msg = f"🚨 {action} {symbol}\nPrice: ₹{price}, TP: ₹{tp}, SL: ₹{sl}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except Exception as e:
        print("Telegram Error:", e)

def send_trade_summary_email():
    if not os.path.exists("trade_log.csv"):
        return
    try:
        df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        body = df[df["timestamp"].dt.date == datetime.now().date()].to_string(index=False)
    except Exception as e:
        body = f"Error parsing trade log: {e}"

    msg = MIMEMultipart()
    msg["Subject"] = "📈 Daily Trade Summary"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.attach(MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL, EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print("Email Error:", e)