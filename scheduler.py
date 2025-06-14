# scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time
from bot import trade_logic
# from trailing import check_trailing_sl  # Optional: Only if you use a trailing SL system

def is_market_open():
    """Returns True if market is open now (Mon–Fri, 9:15 AM – 3:30 PM IST)."""
    now = datetime.now()
    open_time = time(9, 15)
    close_time = time(15, 30)
    is_weekday = now.weekday() < 5
    return is_weekday and open_time <= now.time() <= close_time

def get_market_status():
    """Returns current market status for use in UI."""
    return "🟢 OPEN" if is_market_open() else "🔴 CLOSED"

def schedule_daily_trade():
    """Starts background scheduler for AI trade logic + trailing stop logic."""
    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")

    def run_trade():
        if is_market_open():
            print("✅ Market open — executing trade logic")
            trade_logic()
        else:
            print("❌ Market closed — skipping bot")

    def run_trailing_logic():
        if is_market_open():
            print("🔁 Checking trailing stop-loss...")
            # check_trailing_sl()  # Add your trailing SL handler if needed

    # 🔁 Schedule daily trade at 9:15 AM
    scheduler.add_job(run_trade, trigger="cron", hour=9, minute=15)

    # 🔁 Run trailing SL checker every 10 mins
    scheduler.add_job(run_trailing_logic, trigger="interval", minutes=10)

    scheduler.start()