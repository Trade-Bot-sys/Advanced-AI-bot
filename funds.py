# funds.py
import os
import json
import http.client
from datetime import datetime

# ✅ Get funds (access_token passed from outside)
def get_available_funds(access_token):
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
