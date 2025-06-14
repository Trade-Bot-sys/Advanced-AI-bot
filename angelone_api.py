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
    access_token, api_key = load_auth_data()
    if not access_token or not api_key:
        return 0.0

    url = "https://apiconnect.angelone.in/rest/secure/angelapi/v1/portfolio/funds"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-UserType": "USER",
        "X-SourceID": "WEB",
        "X-ClientLocalIP": "127.0.0.1",
        "X-ClientPublicIP": "127.0.0.1",
        "X-MACAddress": "00:00:00:00:00:00",
        "X-PrivateKey": api_key
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            funds_data = response.json()
            return float(funds_data.get("data", {}).get("availablecash", 0.0))
        else:
            print(f"❌ Error fetching funds: {response.status_code} - {response.text}")
            return 0.0
    except Exception as e:
        print(f"❌ Error during fund fetch: {e}")
        return 0.0
