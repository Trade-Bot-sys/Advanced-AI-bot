# angelone_api.py
import requests
import json
import os

def load_auth_data():
    try:
        with open("access_token.json", "r") as f:
            data = json.load(f)
            return data["access_token"], data["api_key"], data["client_code"]
    except Exception as e:
        print(f"❌ Failed to load access_token.json: {e}")
        return None, None, None

def get_available_funds():
    try:
        access_token, api_key, client_code = load_auth_data()
        if not all([access_token, api_key, client_code]):
            print("❌ Missing required credentials.")
            return 0.0

        # Load device and IP details from Render ENV
        local_ip = os.getenv("CLIENT_LOCAL_IP", "127.0.0.1")
        public_ip = os.getenv("CLIENT_PUBLIC_IP", "127.0.0.1")
        mac_address = os.getenv("MAC_ADDRESS", "00:00:00:00:00:00")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-ClientLocalIP": local_ip,
            "X-ClientPublicIP": public_ip,
            "X-MACAddress": mac_address,
            "X-PrivateKey": api_key
        }

        payload = {
            "clientcode": client_code
        }

        url = "https://apiconnect.angelone.in/rest/secure/angelbroking/user/v1/getRMS"
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        if response.status_code == 200 and "data" in data:
            available_cash = float(data["data"].get("availablecash", 0.0))
            return available_cash
        else:
            print("⚠️ Angel One RMS API failed:", data)
            return 0.0

    except Exception as e:
        print(f"❌ Exception in get_available_funds(): {e}")
        return 0.0
