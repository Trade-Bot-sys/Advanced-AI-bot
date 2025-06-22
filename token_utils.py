import os
import json
import requests
from datetime import datetime
import joblib
import io
import base64
from utils import convert_to_ist
from generate_access_token import generate_token

# === Gist URLs ===
GIST_RAW_URL = "https://gist.github.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/access_token.json"
MODEL_GIST_URL = "https://gist.githubusercontent.com/Trade-Bot-sys/c4a038ffd89d3f8b13f3f26fb3fb72ac/raw/nifty25_model_b64.txt"

# ✅ 1. Fetch access token from Gist
def fetch_access_token_from_gist(gist_url):
    try:
        response = requests.get(gist_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Error fetching access_token.json: {e}")
        return None

# ✅ 2. Check if token is fresh
def is_token_fresh():
    try:
        token_time = datetime.fromtimestamp(os.path.getmtime("access_token.json")).date()
        return token_time == datetime.now().date()
    except:
        return False

# ✅ 3. Fetch model from Gist (base64)
def fetch_model_from_gist(model_gist_url):
    try:
        print("📥 Downloading model from Gist (base64 encoded)...")
        response = requests.get(model_gist_url)
        response.raise_for_status()

        base64_str = response.text.strip()
        model_bytes = io.BytesIO(base64.b64decode(base64_str))
        print("🧠 Decoding and loading model...")
        model = joblib.load(model_bytes)
        print("✅ Model loaded successfully.")
        return model
    except Exception as e:
        print(f"❌ Failed to load model from Gist: {e}")
        raise RuntimeError(f"Model load failed: {e}")

# ✅ 4. Load or regenerate token
def load_tokens():
    tokens = fetch_access_token_from_gist(GIST_RAW_URL)
    if tokens:
        with open("access_token.json", "w") as f:
            json.dump(tokens, f, indent=2)

    if not tokens or not is_token_fresh():
        print("⚠️ Token not fresh. Regenerating...")
        generate_token()
        tokens = fetch_access_token_from_gist(GIST_RAW_URL)
        if tokens:
            with open("access_token.json", "w") as f:
                json.dump(tokens, f, indent=2)
        else:
            raise RuntimeError("❌ Failed to fetch token after regeneration.")

    return tokens

# ✅ 5. Extracted tokens
tokens = load_tokens()
access_token = tokens.get("access_token")
feed_token = tokens.get("feed_token")
api_key = tokens.get("api_key")
client_code = tokens.get("client_code")
