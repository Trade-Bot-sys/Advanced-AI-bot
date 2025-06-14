import streamlit as st  
from executor import place_order, get_live_price  # Assuming 'place_order' and 'get_live_price' are correctly defined.
from alerts import send_telegram_alert  
from datetime import datetime  
import math  
from angelone_api import get_available_funds  # Import your function to get available funds from Angel One

def manual_trade_ui(stock_list, take_profit=10, stop_loss=3):  
    st.subheader("📥 Manual Trade")

    # Get available funds from Angel One
    available_funds = get_available_funds()  # This should return the available funds (e.g., cash balance)

    # Display available funds in the UI
    st.sidebar.write(f"💰 Available Funds: ₹{available_funds:.2f}")

    selected_stock = st.selectbox("Select stock to manually trade", stock_list)  
    manual_price = st.number_input("Enter Buy Price (₹)", min_value=0.1, step=0.1, format="%.2f")  
    investment_amount = st.number_input("Enter Amount to Invest (₹)", min_value=1.0, step=1.0, max_value=available_funds)  

    if st.button("Execute Manual BUY"):  
        if manual_price > 0 and investment_amount > 0:  
            quantity = math.floor(investment_amount / manual_price)  

            if quantity > 0:  
                try:  
                    # Check if there are sufficient funds to place the order
                    if investment_amount <= available_funds:
                        # Place order to buy stock
                        place_order(selected_stock, "BUY", quantity)  

                        # Log trade details
                        with open("trade_log.csv", "a") as log:  
                            log.write(f"{datetime.now()},{selected_stock},BUY,{quantity},{manual_price},manual,manual\n")  

                        # Send Telegram alert
                        send_telegram_alert(selected_stock, "BUY", manual_price, take_profit, stop_loss)  

                        st.success(f"✅ Manual BUY placed for {selected_stock} at ₹{manual_price:.2f} × {quantity} shares")  
                    else:
                        st.warning("⚠️ Insufficient funds to place the order.")
                except Exception as e:  
                    st.error(f"❌ Manual trade failed: {e}")  
            else:  
                st.warning("⚠️ Amount too low for given price. Quantity calculated as 0.")  
        else:  
            st.warning("⚠️ Please enter valid price and amount.")
