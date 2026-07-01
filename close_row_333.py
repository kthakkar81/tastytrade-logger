#!/usr/bin/env python3
"""Close row 333 with correct transaction values."""

from config import TRADE_LOG_SPREADSHEET_ID
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('google-sheets-credentials.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

TARGET_ROW = 333
CLOSING_DATE = '6/15/2026'

# From transactions (verified against 6/9 opening):
# Opening: Sell 7500C $5,123.28 - Buy 7530C $4,211.72 = $911.56 ✓
# Closing: Sell 7530C $11,906.28 - Buy 7500C $13,827.72 = -$1,921.44
CLOSING_NET_PRICE = 11906.28 - 13827.72  # = -$1,921.44 (debit to close)
CLOSING_FEES = 2.24  # Standard SPX spread fee

# Get current row
result = service.spreadsheets().values().get(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range=f'A{TARGET_ROW}:O{TARGET_ROW}'
).execute()
row_data = result.get('values', [[]])[0]

opening_price = float(row_data[10].replace('$', '').replace(',', ''))
opening_fees = float(row_data[9].replace('$', '').replace(',', ''))

total_fees = opening_fees + CLOSING_FEES
total_pnl = opening_price + CLOSING_NET_PRICE

print(f"Row {TARGET_ROW} - SPX Bear Call Spread 7500/7530")
print(f"  Opening: ${opening_price:.2f} (credit)")
print(f"  Closing: ${CLOSING_NET_PRICE:.2f} (debit)")
print(f"  Fees: ${opening_fees:.2f} + ${CLOSING_FEES:.2f} = ${total_fees:.2f}")
print(f"  P&L: ${opening_price:.2f} + ${CLOSING_NET_PRICE:.2f} = ${total_pnl:.2f}")

# Update
update_values = [[
    row_data[0] if len(row_data) > 0 else '',
    CLOSING_DATE,
    row_data[2] if len(row_data) > 2 else '',
    row_data[3] if len(row_data) > 3 else '',
    'Closed',
    row_data[5] if len(row_data) > 5 else '',
    row_data[6] if len(row_data) > 6 else '',
    row_data[7] if len(row_data) > 7 else '',
    row_data[8] if len(row_data) > 8 else '',
    total_fees,
    opening_price,
    CLOSING_NET_PRICE,
    row_data[12] if len(row_data) > 12 else '',
    total_pnl,
    row_data[14] if len(row_data) > 14 else ''
]]

service.spreadsheets().values().update(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range=f'A{TARGET_ROW}:O{TARGET_ROW}',
    valueInputOption='USER_ENTERED',
    body={'values': update_values}
).execute()

print(f"\n✓ Updated row {TARGET_ROW}")

# Clear Import Errors
service.spreadsheets().values().clear(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range='Import Errors!A2:H'
).execute()

print("✓ Cleared Import Errors")
