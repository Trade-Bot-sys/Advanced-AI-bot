import streamlit as st
from executor import place_order, get_live_price
from alerts import send_telegram_alert
from datetime import datetime, time
import pytz
import math
from utils import convert_to_ist

# ✅ Market hours check (IST)
def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    return time(9, 15) <= now <= time(15, 30)

# ✅ Manual trade panel
def manual_trade_ui(stock_list, take_profit=10, stop_loss=3, available_funds=0):
    st.subheader("📥 Manual Trade Panel")
    st.sidebar.write(f"💰 Available Funds: ₹{available_funds:,.2f}")

    selected_stock = st.selectbox("Select stock to manually trade", stock_list)
    manual_price = st.number_input("Enter Price (₹)", min_value=0.1, step=0.1, format="%.2f")
    trade_type = st.radio("Choose Trade Type", ["BUY", "SELL"])

    # ✅ Show estimated quantity if price is entered
    if trade_type == "BUY" and manual_price > 0:
        est_qty = math.floor(available_funds / manual_price)
        st.write(f"🧮 Estimated Max Quantity: {est_qty}")

    # ✅ Market timing check
    if not is_market_open():
        st.warning("⏳ Market is closed. Trading hours are 9:15 AM to 3:30 PM IST.")
        return

    # ✅ BUY logic
    if trade_type == "BUY":
        if available_funds <= 0:
            st.warning("⚠️ Insufficient funds to execute a BUY.")
            return

        invest_amt = st.number_input("Enter Amount to Invest (₹)", min_value=1.0, max_value=available_funds, step=1.0)

        if st.button("✅ Execute Manual BUY"):
            quantity = math.floor(invest_amt / manual_price)
            if quantity > 0:
                try:
                    place_order(selected_stock, "BUY", quantity)
                    try:
                        with open("trade_log.csv", "a") as log:
                            log.write(f"{datetime.now()},{selected_stock},BUY,{quantity},{manual_price},manual,manual\n")
                    except Exception as e:
                        st.warning(f"⚠️ Failed to write log: {e}")

                    send_telegram_alert(selected_stock, "BUY", manual_price, take_profit, stop_loss)
                    st.success(f"✅ BUY order placed: {selected_stock} at ₹{manual_price:.2f} × {quantity}")
                except Exception as e:
                    st.error(f"❌ BUY failed: {e}")
            else:
                st.warning("⚠️ Investment amount too low. Quantity = 0")

    # ✅ SELL logic
    elif trade_type == "SELL":
        sell_qty = st.number_input("Enter Quantity to Sell", min_value=1, step=1)
        if st.button("✅ Execute Manual SELL"):
            try:
                place_order(selected_stock, "SELL", sell_qty)
                try:
                    with open("trade_log.csv", "a") as log:
                        log.write(f"{datetime.now()},{selected_stock},SELL,{sell_qty},{manual_price},manual,manual\n")
                except Exception as e:
                    st.warning(f"⚠️ Failed to write log: {e}")

                send_telegram_alert(selected_stock, "SELL", manual_price, take_profit, stop_loss)
                st.success(f"✅ SELL order placed: {selected_stock} at ₹{manual_price:.2f} × {sell_qty}")
            except Exception as e:
                st.error(f"❌ SELL failed: {e}")
