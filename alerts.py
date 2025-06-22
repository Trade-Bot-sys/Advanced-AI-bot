import os
import requests
import smtplib
import pandas as pd
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from utils import convert_to_ist

load_dotenv()

# ✅ Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
EMAIL = os.getenv("EMAIL_ADDRESS")
EMAIL_PASS = os.getenv("EMAIL_PASSWORD")

# ✅ Simple alert (generic message)
def send_general_telegram_message(msg):
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data=payload)
        if response.status_code == 200:
            print("✅ Telegram alert sent.")
        else:
            print(f"❌ Telegram alert failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error sending Telegram alert: {e}")
        
# ✅ Telegram Alert
def send_telegram_alert(symbol, action, price, tp=None, sl=None, confidence=None, features=None, reason=None):
    msg = f"📢 *{action}* signal for *{symbol}* at ₹{price:.2f}"
    if confidence:
        msg += f"\n🤖 AI Confidence: *{confidence:.2f}*"
    if features:
        msg += f"\n📊 Features → RSI: {features[0]:.2f}, MACD: {features[1]:.2f}, Returns: {features[2]:.4f}"
    if tp and sl:
        msg += f"\n🎯 TP: ₹{tp}, 🛑 SL: ₹{sl}"
    if reason:
        msg += f"\nℹ️ Reason: {reason}"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }

    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data=payload)

# ✅ Daily Summary Email
def send_trade_summary_email(use_google_sheets=False):
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
            df = pd.read_csv("trade_log.csv", names=[
                "timestamp", "symbol", "action", "qty", "entry", "tp", "sl",
                "exit_price", "pnl", "status", "strategy", "reason", "holding_days",
                "exit_time", "trailing_sl_used", "market_condition", "model_confidence"
            ])

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df = df.dropna(subset=["timestamp"])
        df["timestamp_ist"] = df["timestamp"].apply(convert_to_ist)

        today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
        today_trades = df[df["timestamp"].dt.date == today]

        if today_trades.empty:
            print("📭 No trades today to email.")
            return

        # Summary statistics
        total_trades = len(today_trades)
        total_pnl = today_trades["pnl"].sum()
        win_trades = today_trades[today_trades["pnl"] > 0]
        win_rate = (len(win_trades) / total_trades) * 100

        display_cols = ["timestamp_ist", "symbol", "action", "qty", "entry", "tp", "sl", "exit_price", "pnl", "strategy"]
        html_table = today_trades[display_cols].to_html(index=False, justify="center", border=1, classes="styled-table")

        # Build HTML content
        html_content = f"""
        <html>
        <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                padding: 20px;
            }}
            .container {{
                background-color: #ffffff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
                max-width: 800px;
                margin: auto;
            }}
            .styled-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            .styled-table th, .styled-table td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            .styled-table th {{
                background-color: #4CAF50;
                color: white;
            }}
            .summary {{
                margin-top: 20px;
                font-size: 14px;
                line-height: 1.6;
            }}
        </style>
        </head>
        <body>
        <div class="container">
            <h2>📈 Smart AI Bot - Daily Trade Summary</h2>
            <p>Hello Ram,</p>
            <p>Here is your trade report for <strong>{today.strftime('%Y-%m-%d')}</strong>:</p>

            {html_table}

            <div class="summary">
                <p><strong>🔢 Number of Trades:</strong> {total_trades}</p>
                <p><strong>💰 Total P&L:</strong> ₹{total_pnl:.2f}</p>
                <p><strong>🏆 Win Rate:</strong> {win_rate:.2f}%</p>
            </div>

            <p>✅ Keep trading smart with Smart AI Bot!</p>
            <p>🤖 - Smart AI Bot Team</p>
        </div>
        </body>
        </html>
        """

        msg = MIMEMultipart()
        msg["Subject"] = f"📊 Daily Trade Summary - {today.strftime('%d %b %Y')}"
        msg["From"] = EMAIL
        msg["To"] = EMAIL
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL, EMAIL_PASS)
            s.send_message(msg)

        print("✅ Daily trade summary email sent successfully.")

    except Exception as e:
        print(f"❌ Failed to send summary email: {e}")
   
