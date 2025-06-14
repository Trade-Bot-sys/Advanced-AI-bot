# angelone_api.py
import requests
import json

def load_auth_data():
    try:
        with open("access_token.json", "r") as f:
            data = json.load(f)
            return data["access_token"], data["api_key"]
    except Exception as e:
        print(f"❌ Failed to load access_token.json: {e}")
        return None, None

def get_available_funds():
    try:
        # Load token and client code from access_token.json
        with open("access_token.json") as f:
            token_data = json.load(f)

        access_token = token_data["access_token"]
        client_code = token_data["client_code"]

        # Headers for Angel One SmartAPI
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": "YOUR_API_KEY_HERE"  # 🔁 Replace this with your actual Angel One API key
        }

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"

        payload = {
            "clientcode": client_code
        }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and "data" in data:
            available_cash = float(data["data"].get("availablecash", 0.0))
            return available_cash
        else:
            print("⚠️ Invalid response:", data)
            return 0.0

    except Exception as e:
        print(f"❌ Error fetching funds: {e}")
        return 0.0
