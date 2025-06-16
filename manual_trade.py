import streamlit as st
from executor import place_order, get_live_price
from alerts import send_telegram_alert
from datetime import datetime, time
import pytz
import math
from utils import convert_to_ist

# Define Indian market hours (IST)
def is_market_open():
    ist = pytz.timezone("Asia/Kolkata")
    now = datetime.now(ist).time()
    market_open = time(9, 15)
    market_close = time(15, 30)
    return market_open <= now <= market_close

def manual_trade_ui(stock_list, take_profit=10, stop_loss=3, available_funds=0):
    st.subheader("📥 Manual Trade")
    st.sidebar.write(f"💰 Available Funds: ₹{available_funds:.2f}")

    selected_stock = st.selectbox("Select stock to manually trade", stock_list)
    manual_price = st.number_input("Enter Price (₹)", min_value=0.1, step=0.1, format="%.2f")
    trade_type = st.radio("Choose Trade Type", ["BUY", "SELL"])

    if not is_market_open():
        st.warning("⏳ Market is currently closed. Please try trading during live market hours (9:15 AM to 3:30 PM IST).")
        return

    if trade_type == "BUY":
        if available_funds <= 0:
            st.warning("⚠️ You have no available funds in your Angel One account.")
            return

        investment_amount = st.number_input("Enter Amount to Invest (₹)", min_value=1.0, step=1.0, max_value=available_funds)
        if st.button("Execute Manual BUY"):
            quantity = math.floor(investment_amount / manual_price)
            if quantity > 0:
                try:
                    place_order(selected_stock, "BUY", quantity)
                    with open("trade_log.csv", "a") as log:
                        log.write(f"{datetime.now()},{selected_stock},BUY,{quantity},{manual_price},manual,manual\n")

                    send_telegram_alert(selected_stock, "BUY", manual_price, take_profit, stop_loss)
                    st.success(f"✅ BUY order placed: {selected_stock} at ₹{manual_price:.2f} × {quantity} shares")
                except Exception as e:
                    st.error(f"❌ BUY failed: {e}")
            else:
                st.warning("⚠️ Investment too low. Quantity = 0")

    elif trade_type == "SELL":
        sell_quantity = st.number_input("Enter Quantity to Sell", min_value=1, step=1)
        if st.button("Execute Manual SELL"):
            try:
                place_order(selected_stock, "SELL", sell_quantity)
                with open("trade_log.csv", "a") as log:
                    log.write(f"{datetime.now()},{selected_stock},SELL,{sell_quantity},{manual_price},manual,manual\n")

                send_telegram_alert(selected_stock, "SELL", manual_price, take_profit, stop_loss)
                st.success(f"✅ SELL order placed: {selected_stock} at ₹{manual_price:.2f} × {sell_quantity} shares")
            except Exception as e:
                st.error(f"❌ SELL failed: {e}")
