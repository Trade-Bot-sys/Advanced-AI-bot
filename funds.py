# funds.py

import os
import json
import http.client
import requests  # ✅ You forgot to import this
from datetime import datetime

# ✅ Angel One Gist Access Token URL
GIST_RAW_URL = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

# ✅ Fetch token from Gist
def fetch_access_token_from_gist(gist_url):
    try:
        response = requests.get(gist_url)
        if response.status_code == 200:
            tokens = response.json()
            with open("access_token.json", "w") as f:
                json.dump(tokens, f, indent=2)
            return tokens
        else:
            print("❌ Token fetch failed:", response.status_code)
    except Exception as e:
        print("❌ Error fetching token:", e)
    return None

# ✅ Load tokens
tokens = fetch_access_token_from_gist(GIST_RAW_URL)

# ✅ Default fallback if tokens missing
if not tokens:
    tokens = {
        "access_token": "",
        "feed_token": "",
        "api_key": "",
        "client_code": ""
    }

# ✅ Extract values safely
JWT_TOKEN = tokens.get("access_token", "")
FEED_TOKEN = tokens.get("feed_token", "")
API_KEY = tokens.get("api_key", "")
CLIENT_CODE = tokens.get("client_code", "")
LOCAL_IP = os.getenv('CLIENT_LOCAL_IP')
PUBLIC_IP = os.getenv('CLIENT_PUBLIC_IP')
MAC_ADDRESS = os.getenv('MAC_ADDRESS')

# ✅ Get available funds using Angel One API
def get_available_funds():
    try:
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        headers = {
            'Authorization': f'Bearer {JWT_TOKEN}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': LOCAL_IP,
            'X-ClientPublicIP': PUBLIC_IP,
            'X-MACAddress': MAC_ADDRESS,
            'X-PrivateKey': API_KEY
        }
        conn.request("GET", "/rest/secure/angelbroking/user/v1/getRMS", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))
        return data
    except Exception as e:
        return {"status": False, "error": str(e)}
