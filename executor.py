# executor.py

from angel_api import (
    place_order as angel_place_order,
    cancel_order as angel_cancel_order,
    modify_order as angel_modify_order,
    get_order_book as angel_get_order_book,
    get_trade_book as angel_get_trade_book,
    get_ltp as angel_get_ltp_data,
    get_order_status as angel_get_order_status
)

# Wrapper to fetch only the price
def get_live_price(symbol):
    try:
        ltp_data = angel_get_ltp_data(symbol)
        return ltp_data.get("ltp", None)
    except Exception as e:
        print(f"❌ Error getting LTP for {symbol}: {e}")
        return None

# Place order wrapper
def place_order(symbol, transaction_type, quantity):
    try:
        return angel_place_order(symbol, transaction_type, quantity)
    except Exception as e:
        print(f"❌ Failed to place {transaction_type} order for {symbol}: {e}")
        return None

# Cancel order wrapper
def cancel_order(order_id, variety="NORMAL"):
    try:
        return angel_cancel_order(order_id, variety)
    except Exception as e:
        print(f"❌ Failed to cancel order {order_id}: {e}")
        return None

# Modify order wrapper
def modify_order(order_id, price, quantity, variety="NORMAL", producttype="INTRADAY"):
    try:
        return angel_modify_order(order_id, price, quantity, variety, producttype)
    except Exception as e:
        print(f"❌ Failed to modify order {order_id}: {e}")
        return None

# Order book
def get_order_book():
    try:
        return angel_get_order_book()
    except Exception as e:
        print(f"❌ Failed to fetch order book: {e}")
        return []

# Trade book
def get_trade_book():
    try:
        return angel_get_trade_book()
    except Exception as e:
        print(f"❌ Failed to fetch trade book: {e}")
        return []

# LTP data
def get_ltp(symbol):
    try:
        return angel_get_ltp_data(symbol)
    except Exception as e:
        print(f"❌ Failed to fetch LTP data: {e}")
        return {}

# Order status
def get_order_status(order_id):
    try:
        return angel_get_order_status(order_id)
    except Exception as e:
        print(f"❌ Failed to get status for order {order_id}: {e}")
        return {}
