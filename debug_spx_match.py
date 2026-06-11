"""
Debug why SPX Bear Call Spread close isn't matching
"""
import gspread
from google.oauth2.service_account import Credentials
import config

# Auth
scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_file(config.GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=scopes)
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(config.TRADE_LOG_SPREADSHEET_ID)
sheet = spreadsheet.sheet1

# Get row 316
row_316 = sheet.row_values(316)
print(f"Row 316 (full): {row_316}")
print(f"Length: {len(row_316)}")
print()

# Column mapping:
# 0=Opening Date, 1=Closing Date, 2=Underlying, 3=Strategy, 4=Status,
# 5=Expiration, 6=Short Strike, 7=Long Strike, 8=Delta, 9=Fees,
# 10=Opening Net Price, 11=Closing Net Price, 12=Contracts, 13=Total PnL, 14=Notes

print(f"Underlying (col 2): '{row_316[2]}'")
print(f"Strategy (col 3): '{row_316[3]}'")
print(f"Status (col 4): '{row_316[4]}'")
print(f"Expiration (col 5): '{row_316[5]}'")
print(f"Short Strike (col 6): '{row_316[6]}'")
print(f"Long Strike (col 7): '{row_316[7]}'")
print()

# What we're looking for
print("CLOSE trade criteria:")
print("  Underlying: SPX")
print("  Strategy: Bear Call Spread")
print("  Expiration: 9/18/2026")
print("  Strikes: $8,030.00/$8,000.00")
print()

# Parse strikes
from spreadsheet_logger import SpreadsheetLogger
logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)

strikes_str = '$8,030.00/$8,000.00'
strategy = 'Bear Call Spread'
strikes = logger._parse_strikes(strikes_str, strategy)
print(f"Parsed strikes: {strikes}")
print(f"  Short: '{strikes['short']}'")
print(f"  Long: '{strikes['long']}'")
print()

# Check if they match
row_short = row_316[6]
row_long = row_316[7]
print(f"Row strikes match: short={row_short == strikes['short']}, long={row_long == strikes['long']}")
