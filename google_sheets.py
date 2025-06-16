import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

# Google Sheets setup
SHEET_ID = "1GTmmYKh6cFwtSTpWATMDoL0Z0RgQ5OWNaHklOeUXPQs"
CREDENTIALS_FILE = "smart-ai-bot-463112-a36ec5d41477.json"  # uploaded already

def get_sheet(sheet_name):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet(sheet_name)

# ✅ Update holdings to Google Sheets
def update_holdings_sheet(data):
    sheet = get_sheet("holdings")
    df = pd.DataFrame.from_dict(data, orient="index").reset_index()
    df.columns = ["symbol", "details"]
    sheet.clear()
    sheet.update([df.columns.values.tolist()] + df.values.tolist())
    print("✅ Holdings updated to Google Sheets.")

# ✅ Append trade log entry to Google Sheets
def log_trade_to_sheet(entry):
    sheet = get_sheet("trade_log")
    sheet.append_row(entry)
    print("✅ Trade logged to Google Sheets.")
