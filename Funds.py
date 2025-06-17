import os
import json
import http.client
import requests
from datetime import datetime

# ✅ Gist URL for access token
gist_url = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

# ✅ Download and store token
def fetch_access_token():
    try:
        response = requests.get(gist_url)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"❌ Error fetching token: {e}")
        return None

def is_token_fresh():
    try:
        token_time = datetime.fromtimestamp(os.path.getmtime("access_token.json")).date()
        return token_time == datetime.now().date()
    except:
        return False

# ✅ Get and validate tokens
tokens = fetch_access_token()
if tokens:
    with open("access_token.json", "w") as f:
        json.dump(tokens, f, indent=2)

if not tokens or not is_token_fresh():
    st.warning("⚠️ Token not fresh. Regenerating...")
    generate_token()
    tokens = fetch_access_token()
    if tokens:
        with open("access_token.json", "w") as f:
            json.dump(tokens, f, indent=2)
    else:
        st.error("❌ Token fetch failed.")
        st.stop()

  # ✅ Extract token data
access_token = tokens.get("access_token")
api_key = tokens.get("api_key")
client_code = tokens.get("client_code")

# ✅ Get funds
def get_available_funds():
    try:
        conn = http.client.HTTPSConnection("apiconnect.angelone.in")
        headers = {
            'Authorization': f'Bearer {access_token}',
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
