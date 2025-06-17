# funds.py
import os
import json
import http.client
from datetime import datetime

GIST_RAW_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

def fetch_access_token_from_gist(gist_url):
    try:
        response = requests.get(gist_url)
        if response.status_code == 200:
            tokens = response.json()
            with open("access_token.json", "w") as f:
                json.dump(tokens, f, indent=2)
            return tokens
    except Exception as e:
        print("❌ Error fetching token:", e)
    return None

tokens = fetch_access_token_from_gist(GIST_RAW_URL)

if tokens:
    with open("access_token.json", "w") as f:
        json.dump(tokens, f, indent=2)

if tokens:
    access_token = tokens.get("access_token")
    feed_token = tokens.get("feed_token")
    api_key = tokens.get("api_key")
    client_code = tokens.get("client_code")

API_KEY = tokens.get("api_key")
JWT_TOKEN = tokens.get("access_token")
CLIENT_CODE = tokens.get("client_code")
LOCAL_IP = os.getenv('CLIENT_LOCAL_IP')
PUBLIC_IP = os.getenv('CLIENT_PUBLIC_IP')
MAC_ADDRESS = os.getenv('MAC_ADDRESS')

# ✅ Get funds (access_token passed from outside)
def get_available_funds():
    try:
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        headers = {
            'Authorization': f'Bearer {JWT_TOKEN}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': os.getenv('CLIENT_LOCAL_IP'),
            'X-ClientPublicIP': os.getenv('CLIENT_PUBLIC_IP'),
            'X-MACAddress': os.getenv('MAC_ADDRESS'),
            'X-PrivateKey': os.getenv('API_KEY')
        }
        conn.request("GET", "/rest/secure/angelbroking/user/v1/getRMS", headers=headers)
        res = conn.getresponse()
        return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        return {"status": False, "error": str(e)}
