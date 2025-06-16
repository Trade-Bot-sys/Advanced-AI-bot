from datetime import datetime
import pytz

def convert_to_ist(timestamp_str):
    utc_time = datetime.fromisoformat(timestamp_str)
    utc = pytz.utc
    ist = pytz.timezone("Asia/Kolkata")
    return utc.localize(utc_time).astimezone(ist).strftime("%Y-%m-%d %H:%M:%S")
