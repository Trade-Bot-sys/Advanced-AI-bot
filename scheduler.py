from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time
from pytz import timezone
import threading
from bot import trade_logic, monitor_holdings
from alerts import send_trade_summary_email  # ✅ Added

# ✅ Define timezone
INDIA_TZ = timezone("Asia/Kolkata")

def is_market_open():
    """Returns True if market is open now (Mon–Fri, 9:15 AM – 3:30 PM IST)."""
    now = datetime.now(INDIA_TZ)
    open_time = time(9, 15)
    close_time = time(15, 30)
    is_weekday = now.weekday() < 5
    return is_weekday and open_time <= now.time() <= close_time

def get_market_status():
    """Returns current market status for use in UI."""
    return "🟢 OPEN" if is_market_open() else "🔴 CLOSED"

def schedule_daily_trade():
    """Starts background scheduler for AI trade logic + trailing/exit logic."""
    scheduler = BackgroundScheduler(timezone=INDIA_TZ)

    def run_trade():
        if is_market_open():
            print("✅ Market open — running trade logic")
            threading.Thread(target=trade_logic).start()
        else:
            print("❌ Market closed — skipping trade logic")

    def run_exit_check():
        if is_market_open():
            print("🔁 Checking exit conditions for open trades...")
            threading.Thread(target=monitor_holdings).start()

    def send_daily_email():
        print("📬 Sending daily summary email...")
        threading.Thread(target=send_trade_summary_email).start()

    # ✅ Schedule trade logic daily at 9:15 AM IST
    scheduler.add_job(run_trade, trigger="cron", hour=9, minute=15)

    # 🔁 Schedule exit check every 10 minutes
    scheduler.add_job(run_exit_check, trigger="interval", minutes=10)

    # 📩 Schedule daily summary email at 4:30 PM IST
    scheduler.add_job(send_daily_email, trigger="cron", hour=16, minute=30)

    scheduler.start()
    print("⏱️ Scheduler started")
