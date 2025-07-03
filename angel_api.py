import http.client
import json
import os
import http.client
from utils import convert_to_ist

# ✅ Load credentials from online access_token.json (hosted in Gist)
import requests
ACCESS_JSON_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/"
access_data = requests.get(ACCESS_JSON_URL).json()

TOKEN = access_data["access_token"]
API_KEY = access_data["api_key"]

CLIENT_LOCAL_IP = os.getenv('CLIENT_LOCAL_IP')
CLIENT_PUBLIC_IP = os.getenv('CLIENT_PUBLIC_IP')
MAC_ADDRESS = os.getenv('MAC_ADDRESS')

BASE_URL = "apiconnect.angelone.in"

HEADERS = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-UserType': 'USER',
    'X-SourceID': 'WEB',
    'X-ClientLocalIP': CLIENT_LOCAL_IP,
    'X-ClientPublicIP': CLIENT_PUBLIC_IP,
    'X-MACAddress': MAC_ADDRESS,
    'X-PrivateKey': API_KEY
}

def place_order(tradingsymbol, transactiontype, quantity, exchange="NSE", producttype="INTRADAY"):
    conn = http.client.HTTPSConnection(BASE_URL)
    payload = json.dumps({
        "exchange": exchange,
        "tradingsymbol": tradingsymbol,
        "quantity": quantity,
        "disclosedquantity": 0,
        "transactiontype": transactiontype,
        "ordertype": "MARKET",
        "variety": "NORMAL",
        "producttype": producttype
    })
    conn.request("POST", "/rest/secure/angelbroking/order/v1/placeOrder", payload, HEADERS)
    res = conn.getresponse()
    data = json.loads(res.read().decode("utf-8"))

    # ✅ Add this logging block:
    if data.get("status") != True:
        print(f"❌ Order FAILED for {tradingsymbol}: {data}")
    else:
        print(f"✅ Order SUCCESS for {tradingsymbol}: {data}")
    return data


def modify_order(orderid, new_price, new_quantity):
    conn = http.client.HTTPSConnection(BASE_URL)
    payload = json.dumps({
        "variety": "NORMAL",
        "orderid": orderid,
        "ordertype": "LIMIT",
        "producttype": "INTRADAY",
        "duration": "DAY",
        "price": str(new_price),
        "quantity": str(new_quantity)
    })
    conn.request("POST", "/rest/secure/angelbroking/order/v1/modifyOrder", payload, HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


def cancel_order(orderid):
    conn = http.client.HTTPSConnection(BASE_URL)
    payload = json.dumps({
        "variety": "NORMAL",
        "orderid": orderid
    })
    conn.request("POST", "/rest/secure/angelbroking/order/v1/cancelOrder", payload, HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


def get_order_book():
    conn = http.client.HTTPSConnection(BASE_URL)
    conn.request("GET", "/rest/secure/angelbroking/order/v1/getOrderBook", "", HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


def get_trade_book():
    conn = http.client.HTTPSConnection(BASE_URL)
    conn.request("GET", "/rest/secure/angelbroking/order/v1/getTradeBook", "", HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


def get_ltp(tradingsymbol, symboltoken, exchange="NSE"):
    conn = http.client.HTTPSConnection(BASE_URL)
    payload = json.dumps({
        "exchange": exchange,
        "tradingsymbol": tradingsymbol,
        "symboltoken": symboltoken
    })
    conn.request("POST", "/rest/secure/angelbroking/order/v1/getLtpData", payload, HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")


def get_order_status(orderid):
    conn = http.client.HTTPSConnection(BASE_URL)
    conn.request("GET", f"/rest/secure/angelbroking/order/v1/details/{orderid}", "", HEADERS)
    res = conn.getresponse()
    return res.read().decode("utf-8")
