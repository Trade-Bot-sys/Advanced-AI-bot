import http.client
import json
import os
import pyotp
import schedule
import time
from datetime import datetime
import pytz
import firebase_admin
from firebase_admin import credentials, storage

# ---------- Firebase Setup ----------
def init_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("secrets/firebase-adminsdk.json")  # 🔁 adjust path if needed
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'your-project-id.appspot.com'  # 🔁 replace with your bucket
            })
    except Exception as e:
        print(f"❌ Firebase init error: {e}")

def upload_to_firebase():
    try:
        init_firebase()
        bucket = storage.bucket()
        blob = bucket.blob("access_token.json")
        blob.upload_from_filename("access_token.json")
        print("✅ Uploaded access_token.json to Firebase")
    except Exception as e:
        print(f"❌ Firebase upload failed: {e}")

# ---------- Token Generator ----------
def generate_token():
    try:
        print(f"[{datetime.now()}] ⏳ Starting token generation...")

        api_key = "JeYhSd2A"
        client_code = "AAAN475750"

        # ✅ Fetch from ENV
        client_code_env = os.getenv('CLIENT_CODE')
        password = os.getenv('CLIENT_PIN')
        totp_secret = os.getenv('TOTP_SECRET')
        apikey = os.getenv('API_KEY')
        local_ip = os.getenv('CLIENT_LOCAL_IP')
        public_ip = os.getenv('CLIENT_PUBLIC_IP')
        mac_address = os.getenv('MAC_ADDRESS')

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
            print(f"❌ Missing env keys: {', '.join(missing_keys)}")
            return

        # ✅ TOTP
        totp = pyotp.TOTP(totp_secret).now()

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

        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        conn.request("POST", "/rest/auth/angelbroking/user/v1/loginByPassword", payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8")
        conn.close()

        response_data = json.loads(data)
        print("🧾 Login Response:", json.dumps(response_data, indent=2))

        if 'data' not in response_data:
            print("❌ Login failed: no 'data'")
            return

        access_token = response_data['data'].get('jwtToken')
        feed_token = response_data['data'].get('feedToken')

        if not all([access_token, feed_token]):
            print("❌ Missing tokens in response.")
            return

        with open("access_token.json", "w") as f:
            json.dump({
                "feed_token": feed_token,
                "access_token": access_token,
                "api_key": api_key,
                "client_code": client_code
            }, f, indent=2)

        print(f"[{datetime.now()}] ✅ access_token.json saved.")

        # 🔁 Upload to Firebase
        upload_to_firebase()

    except Exception as e:
        print(f"❌ Exception in generate_token(): {e}")

# ---------- Optional Scheduler ----------
def run_scheduler():
    print(f"[{datetime.now()}] 🕒 Scheduler started (09:10 AM IST daily)")
    schedule.every().day.at("09:10").do(generate_token)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---------- Entry Point ----------
if __name__ == "__main__":
    generate_token()         # ✅ Run once immediately
    # run_scheduler()        # 🔁 Uncomment to run daily
