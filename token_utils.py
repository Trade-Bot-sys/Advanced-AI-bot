# token_utils.py
import os
import json
import requests
from datetime import datetime
from utils import convert_to_ist

GIST_RAW_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

def fetch_access_token_from_gist(gist_url):
    try:
        response = requests.get(gist_url)
        if response.status_code == 200:
            return response.json()
        else:
            st.error("❌ Failed to fetch access_token.json from Gist")
            return None
    except Exception as e:
        st.error(f"❌ Error fetching access_token.json: {e}")
        return None

def is_token_fresh():
    try:
        file_path = "access_token.json"
        if not os.path.exists(file_path):
            return False
        token_time = datetime.fromtimestamp(os.path.getmtime(file_path)).date()
        return token_time == datetime.now().date()
    except:
        return False

tokens = fetch_access_token_from_gist(GIST_RAW_URL)

if tokens:
    with open("access_token.json", "w") as f:
        json.dump(tokens, f, indent=2)

if not tokens or not is_token_fresh():
    st.warning("⚠️ Token not fresh. Regenerating...")
    generate_token()
    tokens = fetch_access_token_from_gist(GIST_RAW_URL)
    if tokens:
        with open("access_token.json", "w") as f:
            json.dump(tokens, f, indent=2)
    else:
        st.error("❌ Failed to fetch token even after regeneration.")
        st.stop()
if tokens:
    access_token = tokens.get("access_token")
    feed_token = tokens.get("feed_token")
    api_key = tokens.get("api_key")
    client_code = tokens.get("client_code")
else:
    st.stop()
