# token_utils.py
import requests
import json
from datetime import datetime
from utils import convert_to_ist
gist_url = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"

def fetch_tokens():
    try:
        response = requests.get(gist_url)
        if response.status_code == 200:
            tokens = response.json()
            return tokens
    except Exception as e:
        print("❌ Error fetching token:", e)
    return None

def get_access_token():
    tokens = fetch_tokens()
    return tokens.get("access_token") if tokens else None

def get_api_key():
    tokens = fetch_tokens()
    return tokens.get("api_key") if tokens else None

def get_client_code():
    tokens = fetch_tokens()
    return tokens.get("client_code") if tokens else None
