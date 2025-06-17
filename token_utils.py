# token_utils.py
import os
import json
import requests
from datetime import datetime
from utils import convert_to_ist

# ✅ Gist URL to fetch token
gist_url = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

# ✅ Fetch and save tokens
def fetch_tokens():
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

# ✅ Check token freshness by file timestamp
def is_token_fresh():
    try:
        token_time = datetime.fromtimestamp(os.path.getmtime("access_token.json")).date()
        return token_time == datetime.now().date()
    except:
        return False

# ✅ Get just the access token (optional utility)
def get_access_token():
    tokens = fetch_tokens()
    return tokens.get("access_token") if tokens else None

# ✅ Return token file's last update time
def get_token_timestamp():
    try:
        return datetime.fromtimestamp(os.path.getmtime("access_token.json"))
    except:
        return None
