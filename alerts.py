import os
import requests
import smtplib
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# ✅ Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL = os.getenv("EMAIL_ADDRESS")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

# ✅ Telegram Alert
def send_telegram_alert(symbol, action, price, tp=0, sl=0, reason=None):
    """Sends a formatted trade alert to Telegram with optional reason."""
    try:
        msg = f"🚨 {action.upper()} {symbol}\n💸 Price: ₹{price:.2f}"
        if action.upper() == "BUY":
            msg += f"\n🎯 TP: ₹{tp:.2f}, 🛑 SL: ₹{sl:.2f}"
        if reason:
            msg += f"\n📌 Reason: {reason}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        if response.status_code != 200:
            print(f"❌ Telegram Error: {response.text}")
        else:
            print(f"✅ Telegram alert sent for {symbol} ({action})")
    except Exception as e:
        print("❌ Telegram Exception:", e)

# ✅ Daily Summary Email
def send_trade_summary_email(use_google_sheets=False):
    """Sends daily trade summary email using Gmail SMTP."""
    try:
        if use_google_sheets:
            from google_sheets import get_sheet
            sheet = get_sheet("trade_log")
            records = sheet.get_all_records()
            df = pd.DataFrame(records)
        else:
            if not os.path.exists("trade_log.csv"):
                print("⚠️ No trade log found for summary email.")
                return
            df = pd.read_csv("trade_log.csv", names=["timestamp", "symbol", "action", "qty", "entry", "tp", "sl"])

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        today = datetime.now().date()
        today_trades = df[df["timestamp"].dt.date == today]

        if today_trades.empty:
            print("📭 No trades today to email.")
            return

        body = today_trades.to_string(index=False)

        msg = MIMEMultipart()
        msg["Subject"] = "📈 Daily Trade Summary - Smart AI Bot"
        msg["From"] = EMAIL
        msg["To"] = EMAIL
        msg.attach(MIMEText(f"<html><body><pre>{body}</pre></body></html>", "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL, EMAIL_PASS)
            s.send_message(msg)

        print("✅ Daily trade summary email sent.")

    except Exception as e:
        print("❌ Email sending error:", e)
