import os
import json
import requests
from datetime import datetime
import joblib
import io
import base64
from generate_access_token import generate_token

# === Gist URLs ===
GIST_RAW_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"
MODEL_GIST_URL = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/nifty25_model_b64.txt"

# ✅ 1. Fetch access token JSON from Gist
def fetch_access_token_from_gist(gist_url=GIST_RAW_URL):
    try:
        response = requests.get(gist_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching access_token.json from Gist: {e}")
        return None

# ✅ 2. Check if local access_token.json is from today
def is_token_fresh():
    try:
        token_time = datetime.fromtimestamp(os.path.getmtime("access_token.json")).date()
        return token_time == datetime.now().date()
    except:
        return False

# ✅ 3. Fetch and decode AI model from Gist (base64 encoded)
def fetch_model_from_gist(model_gist_url=MODEL_GIST_URL):
    try:
        print("📥 Downloading AI model from Gist...")
        response = requests.get(model_gist_url)
        response.raise_for_status()
        base64_str = response.text.strip()
        model_bytes = io.BytesIO(base64.b64decode(base64_str))
        model = joblib.load(model_bytes)
        print("✅ AI model loaded successfully from Gist.")
        return model
    except Exception as e:
        print(f"❌ Failed to load AI model: {e}")
        raise RuntimeError("Model load failed")

# ✅ 4. Load token locally or refresh if needed
def load_tokens():
    tokens = None

    if os.path.exists("access_token.json") and is_token_fresh():
        print("✅ Using fresh local access_token.json")
        with open("access_token.json", "r") as f:
            tokens = json.load(f)
    else:
        print("⚠️ Local token not fresh. Fetching from Gist...")
        tokens = fetch_access_token_from_gist()
        if not tokens:
            print("🔄 Regenerating token via generate_token()...")
            generate_token()
            tokens = fetch_access_token_from_gist()
        
        if tokens:
            with open("access_token.json", "w") as f:
                json.dump(tokens, f, indent=2)
        else:
            raise RuntimeError("❌ Failed to fetch fresh access_token.json")

    return tokens

# ✅ 5. Extract token values for global use
tokens = load_tokens()
access_token = tokens.get("access_token")
feed_token = tokens.get("feed_token")
api_key = tokens.get("api_key")
client_code = tokens.get("client_code")
