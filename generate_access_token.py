import http.client
import json
import os
import pyotp
import schedule
import time
from datetime import datetime
import requests
from utils import convert_to_ist
from alerts import send_telegram_alert, send_general_telegram_message # ✅ Make sure alerts.py is available

# ---------- Gist Uploader ----------
def update_gist_token(gist_id, github_token, new_content):
    try:
        url = f"https://api.github.com/gists/{gist_id}"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        payload = {
            "files": {
                "access_token.json": {
                    "content": new_content
                }
            }
        }

        response = requests.patch(url, headers=headers, json=payload)
        if response.status_code == 200:
            print("✅ Gist updated successfully.")
            send_general_telegram_message("✅ Angel One token updated in Gist successfully.")
        else:
            print(f"❌ Failed to update Gist: {response.status_code} - {response.text}")
            send_general_telegram_message(f"❌ Gist update failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception while updating Gist: {e}")
        send_general_telegram_message(f"❌ Gist update exception: {e}")

# ---------- Token Generator ----------
def generate_token():
    try:
        print(f"[{datetime.now()}] ⏳ Starting token generation...")

        # ✅ Env vars (required)
        client_code = os.getenv('CLIENT_CODE')
        password = os.getenv('CLIENT_PIN')
        totp_secret = os.getenv('TOTP_SECRET')
        apikey = os.getenv('API_KEY')
        local_ip = os.getenv('CLIENT_LOCAL_IP')
        public_ip = os.getenv('CLIENT_PUBLIC_IP')
        mac_address = os.getenv('MAC_ADDRESS')
        gist_id = os.getenv('GIST_ID')
        github_token = os.getenv('GITHUB_TOKEN')

        # ✅ Check all
        required_keys = {
            'CLIENT_CODE': client_code,
            'CLIENT_PIN': password,
            'TOTP_SECRET': totp_secret,
            'API_KEY': apikey,
            'CLIENT_LOCAL_IP': local_ip,
            'CLIENT_PUBLIC_IP': public_ip,
            'MAC_ADDRESS': mac_address,
            'GIST_ID': gist_id,
            'GITHUB_TOKEN': github_token
        }

        missing = [k for k, v in required_keys.items() if not v]
        if missing:
            print(f"❌ Missing env keys: {', '.join(missing)}")
            send_general_telegram_message(f"❌ Missing env keys: {', '.join(missing)}")
            return

        # ✅ Generate TOTP
        totp = pyotp.TOTP(totp_secret).now()
        payload = json.dumps({
            "clientcode": client_code,
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
            send_general_telegram_message("❌ Login failed: no 'data' in response")
            return

        access_token = response_data['data'].get('jwtToken')
        feed_token = response_data['data'].get('feedToken')

        if not all([access_token, feed_token]):
            print("❌ Missing tokens in response.")
            send_general_telegram_message("❌ Missing access_token or feed_token")
            return

        # ✅ Upload directly to Gist (skip local file)
        new_content = json.dumps({
            "feed_token": feed_token,
            "access_token": access_token,
            "api_key": apikey,
            "client_code": client_code
        }, indent=2)

        update_gist_token(gist_id, github_token, new_content)

    except Exception as e:
        print(f"❌ Exception in generate_token(): {e}")
        send_general_telegram_message(f"❌ Exception in token generation: {e}")

# ---------- Optional Scheduler ----------
def run_scheduler():
    print(f"[{datetime.now()}] 🕒 Scheduler started (08:32 AM IST daily)")
    schedule.every().day.at("08:32").do(generate_token)
    while True:
        schedule.run_pending()
        time.sleep(60)

# ---------- Entry Point ----------
if __name__ == "__main__":
    generate_token()         # ✅ Run once immediately
    # run_scheduler()        # 🔁 Optional schedulermment to run daily
