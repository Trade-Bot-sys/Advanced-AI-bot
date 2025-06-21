import os
import json
import http.client
import requests
from datetime import datetime

# ✅ Gist raw URL (corrected version)
GIST_RAW_URL = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

# ✅ Function to fetch token from GitHub Gist
def fetch_access_token_from_gist(gist_url):
    try:
        response = requests.get(gist_url)
        if response.status_code == 200:
            tokens = response.json()
            return tokens
        else:
            print("❌ Token fetch failed:", response.status_code)
    except Exception as e:
        print("❌ Error fetching token:", e)
    return None

# ✅ Function to get available funds
def get_available_funds():
    try:
        tokens = fetch_access_token_from_gist(GIST_RAW_URL)
        if not tokens:
            return {"status": False, "error": "Token fetch failed"}

        JWT_TOKEN = tokens.get("access_token", "")
        API_KEY = tokens.get("api_key", "")
        CLIENT_CODE = tokens.get("client_code", "")
        LOCAL_IP = os.getenv('CLIENT_LOCAL_IP')
        PUBLIC_IP = os.getenv('CLIENT_PUBLIC_IP')
        MAC_ADDRESS = os.getenv('MAC_ADDRESS')

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

        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        conn.request("GET", "/rest/secure/angelbroking/user/v1/getRMS", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        # ✅ Optional: Print available fund for manual testing
        if data.get("status") and data.get("data"):
            print("✅ Available Cash:", data["data"].get("availablecash", "N/A"))
        else:
            print("❌ API returned:", data)

        return data

    except Exception as e:
        return {"status": False, "error": str(e)}
