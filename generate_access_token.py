import http.client
import json
import os
import pyotp
import schedule
import time
from datetime import datetime
import pytz

def generate_token():
    try:
        print(f"[{datetime.now()}] ⏳ Starting token generation...")
        api_key = "JeYhSd2A"
        client_code = "AAAN475750" 
        # ✅ Fetch secrets from Replit environment
        client_code_env = os.getenv('CLIENT_CODE')
        password = os.getenv('CLIENT_PIN')
        totp_secret = os.getenv('TOTP_SECRET')
        apikey = os.getenv('API_KEY')
        local_ip = os.getenv('CLIENT_LOCAL_IP')
        public_ip = os.getenv('CLIENT_PUBLIC_IP')
        mac_address = os.getenv('MAC_ADDRESS')

        # ✅ Check if any secrets are missing
        required_keys = {
            'CLIENT_CODE': client_code_env,
            'CLIENT_PIN': password,
            'TOTP_SECRET': totp_secret,
            'API_KEY': apikey,
            'CLIENT_LOCAL_IP': local_ip,
            'CLIENT_PUBLIC_IP': public_ip,
            'MAC_ADDRESS': mac_address
        }

        missing_keys = [k for k, v in required_keys.items() if not v]
        if missing_keys:
            print(f"❌ Missing environment keys in Replit: {', '.join(missing_keys)}")
            return

        # ✅ Generate TOTP
        totp = pyotp.TOTP(totp_secret).now()

        # ✅ Prepare payload and headers
        payload = json.dumps({
            "clientcode": client_code_env,
            "password": password,
            "totp": totp,
            "state": "active"
        })

        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-UserType': 'USER',
            'X-SourceID': 'WEB',
            'X-ClientLocalIP': local_ip,
            'X-ClientPublicIP': public_ip,
            'X-MACAddress': mac_address,
            'X-PrivateKey': apikey
        }

        # ✅ Send request
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()

        print("Login Response:", data)

        # ✅ Parse response
        response_data = json.loads(data)
        print("🧾 Parsed Response JSON:", json.dumps(response_data, indent=2))

        if 'data' not in response_data:
            print("❌ Error: Login failed. No 'data' in response.")
            return
        
        access_token = response_data['data'].get('jwtToken')
        feed_token = response_data['data'].get('feedToken')
        #client_code_api = response_data['data'].get('clientcode') or response_data['data'].get('clientCode')

        if not all([access_token, feed_token]):
            print("❌ Missing values in response.")
            return

        # ✅ Save to file
        with open("access_token.json", "w") as f:
            json.dump({
                
                "feed_token": feed_token,
                "access_token": access_token,
                "api_key": api_key,
                "client_code": client_code
            }, f, indent=2)

        print(f"[{datetime.now()}] ✅ access_token.json saved successfully")

    except Exception as e:
        print(f"[{datetime.now()}] ❌ Error during token generation:", str(e))


def run_scheduler():
    print(f"[{datetime.now()}] ✅ Scheduler started. Waiting for 09:10 AM IST...")

    schedule.every().day.at("09:10").do(generate_token)

    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    generate_token()  # 🔁 Run immediately once
    # run_scheduler()   # 🔁 Uncomment to run daily at 09:10 AM
