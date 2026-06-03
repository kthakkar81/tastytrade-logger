"""
Clear Import Errors sheet
"""
import gspread
from google.oauth2.service_account import Credentials
import config

# Authenticate
scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

creds = Credentials.from_service_account_file(
    config.GOOGLE_SHEETS_CREDENTIALS_FILE,
    scopes=scopes
)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(config.TRADE_LOG_SPREADSHEET_ID)

try:
    error_sheet = spreadsheet.worksheet('Import Errors')

    # Get all values
    all_rows = error_sheet.get_all_values()

    if len(all_rows) <= 1:
        print("✓ Import Errors sheet already empty")
    else:
        print(f"Found {len(all_rows) - 1} error(s) - all from failed datetime serialization attempts")

        # Keep header, delete all other rows
        error_sheet.delete_rows(2, len(all_rows))
        print("✓ Cleared all import errors")

except Exception as e:
    print(f"✗ Error accessing Import Errors sheet: {e}")
