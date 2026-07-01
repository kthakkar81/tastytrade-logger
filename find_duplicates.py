#!/usr/bin/env python3
"""Find duplicate OPEN rows for SPX Bear Call Spread."""

from config import TRADE_LOG_SPREADSHEET_ID
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('google-sheets-credentials.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Read all data
result = service.spreadsheets().values().get(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range='A:O'
).execute()

rows = result.get('values', [])
headers = rows[0]

# Find SPX Bear Call Spread positions with Status=Open, Expiration=7/9/2026
target_underlying = 'SPX'
target_strategy = 'Bear Call Spread'
target_expiration = '7/9/2026'
target_status = 'Open'

print(f"\nSearching for: {target_underlying} {target_strategy} {target_expiration} Status={target_status}\n")
print("Row# | Opening Date | Status | Expiration | Strikes | Contracts | Opening Price | Fees")
print("-" * 100)

matches = []
for i, row in enumerate(rows[1:], start=2):  # Start at row 2 (skip header)
    if len(row) < 7:
        continue

    underlying = row[2] if len(row) > 2 else ''
    strategy = row[3] if len(row) > 3 else ''
    status = row[4] if len(row) > 4 else ''
    expiration = row[5] if len(row) > 5 else ''

    if (underlying == target_underlying and
        strategy == target_strategy and
        expiration == target_expiration and
        status == target_status):

        opening_date = row[0] if len(row) > 0 else ''
        strikes = f"{row[6] if len(row) > 6 else ''}/{row[7] if len(row) > 7 else ''}"
        contracts = row[12] if len(row) > 12 else ''
        opening_price = row[10] if len(row) > 10 else ''
        fees = row[9] if len(row) > 9 else ''

        print(f"{i:4} | {opening_date:12} | {status:6} | {expiration:10} | {strikes:20} | {contracts:9} | {opening_price:13} | {fees}")
        matches.append(i)

print(f"\n✓ Found {len(matches)} matching OPEN rows: {matches}")
