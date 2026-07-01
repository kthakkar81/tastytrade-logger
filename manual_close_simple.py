#!/usr/bin/env python3
"""Manually close the SPX Bear Call Spread from Import Errors."""

import sys
from datetime import datetime
from config import TRADE_LOG_SPREADSHEET_ID
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from tastytrade_client import TastytradeClient

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('google-sheets-credentials.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Target row
TARGET_ROW = 333
CLOSING_DATE = '6/15/2026'

# Get current row data
result = service.spreadsheets().values().get(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range=f'A{TARGET_ROW}:O{TARGET_ROW}'
).execute()

row_data = result.get('values', [[]])[0]

print(f"Current row {TARGET_ROW} data:")
print(f"  Opening Date: {row_data[0] if len(row_data) > 0 else 'N/A'}")
print(f"  Underlying: {row_data[2] if len(row_data) > 2 else 'N/A'}")
print(f"  Strategy: {row_data[3] if len(row_data) > 3 else 'N/A'}")
print(f"  Status: {row_data[4] if len(row_data) > 4 else 'N/A'}")
print(f"  Expiration: {row_data[5] if len(row_data) > 5 else 'N/A'}")
print(f"  Strikes: {row_data[6] if len(row_data) > 6 else 'N/A'}/{row_data[7] if len(row_data) > 7 else 'N/A'}")
print(f"  Contracts: {row_data[12] if len(row_data) > 12 else 'N/A'}")
print(f"  Opening Price: {row_data[10] if len(row_data) > 10 else 'N/A'}")
print(f"  Opening Fees: {row_data[9] if len(row_data) > 9 else 'N/A'}")

# Get closing transaction from Tastytrade
print("\nFetching today's transactions...")
client = TastytradeClient()
client.authenticate()
transactions = client.get_transactions('2026-06-15', '2026-06-15')

# Find SPX Bear Call CLOSE (looking for both legs)
print(f"\nFound {len(transactions)} transactions")

# Look for the specific Bear Call legs: short 7500C, long 7530C
short_leg = None
long_leg = None

for txn in transactions:
    if txn.get('underlying-symbol') != 'SPX':
        continue
    if txn.get('action') != 'Sell to Close' and txn.get('action') != 'Buy to Close':
        continue

    symbol = txn.get('symbol', '')
    if not symbol or 'C' not in symbol:
        continue

    # Parse strike from symbol
    if '7500C' in symbol:
        short_leg = txn
        print(f"Found short leg: {symbol}, action={txn.get('action')}, net-value=${txn.get('net-value')}")
    elif '7530C' in symbol:
        long_leg = txn
        print(f"Found long leg: {symbol}, action={txn.get('action')}, net-value=${txn.get('net-value')}")

if not short_leg or not long_leg:
    print("\n✗ Could not find both legs of SPX Bear Call CLOSE")
    sys.exit(1)

# Calculate closing values
short_net = float(short_leg.get('net-value', 0))
long_net = float(long_leg.get('net-value', 0))
short_comm_fees = abs(float(short_leg.get('commissions', 0)) + float(short_leg.get('fees', 0)))
long_comm_fees = abs(float(long_leg.get('commissions', 0)) + float(long_leg.get('fees', 0)))

CLOSING_NET_PRICE = short_net + long_net
CLOSING_FEES = short_comm_fees + long_comm_fees

# Calculate updates
opening_price = float(row_data[10].replace('$', '').replace(',', '')) if len(row_data) > 10 else 0
opening_fees = float(row_data[9].replace('$', '').replace(',', '')) if len(row_data) > 9 else 0
total_fees = opening_fees + CLOSING_FEES
total_pnl = opening_price + CLOSING_NET_PRICE

print(f"\n{'='*60}")
print(f"CLOSING UPDATE:")
print(f"  Short leg net: ${short_net:.2f} (fees: ${short_comm_fees:.2f})")
print(f"  Long leg net:  ${long_net:.2f} (fees: ${long_comm_fees:.2f})")
print(f"  Closing Net Price: ${CLOSING_NET_PRICE:.2f}")
print(f"  Closing Fees: ${CLOSING_FEES:.2f}")
print(f"  Total Fees: ${total_fees:.2f}")
print(f"  Total P&L: ${total_pnl:.2f}")
print(f"{'='*60}")

# Update the row
update_values = [
    [
        row_data[0] if len(row_data) > 0 else '',  # Opening Date
        CLOSING_DATE,  # Closing Date
        row_data[2] if len(row_data) > 2 else '',  # Underlying
        row_data[3] if len(row_data) > 3 else '',  # Strategy
        'Closed',  # Status
        row_data[5] if len(row_data) > 5 else '',  # Expiration
        row_data[6] if len(row_data) > 6 else '',  # Short Strike
        row_data[7] if len(row_data) > 7 else '',  # Long Strike
        row_data[8] if len(row_data) > 8 else '',  # Delta
        total_fees,  # Total Fees
        opening_price,  # Opening Net Price
        CLOSING_NET_PRICE,  # Closing Net Price
        row_data[12] if len(row_data) > 12 else '',  # Contracts
        total_pnl,  # Total P&L
        row_data[14] if len(row_data) > 14 else ''  # Notes
    ]
]

service.spreadsheets().values().update(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range=f'A{TARGET_ROW}:O{TARGET_ROW}',
    valueInputOption='USER_ENTERED',
    body={'values': update_values}
).execute()

print(f"\n✓ Updated row {TARGET_ROW}")

# Clear the Import Errors entry
print("\nClearing Import Errors sheet...")
service.spreadsheets().values().clear(
    spreadsheetId=TRADE_LOG_SPREADSHEET_ID,
    range='Import Errors!A2:H'
).execute()

print("✓ Cleared Import Errors")
print("\n✓ COMPLETE")
