#!/usr/bin/env python3
"""Manually close the SPX Bear Call Spread from Import Errors."""

import sys
from datetime import datetime
from config import TRADE_LOG_SPREADSHEET_ID
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file('google-sheets-credentials.json', scopes=SCOPES)
service = build('sheets', 'v4', credentials=creds)

# Target row and transaction details from Import Errors
TARGET_ROW = 333
CLOSING_DATE = '6/15/2026'
CLOSING_NET_PRICE = 775.76  # Need to get from Import Errors or transactions
CLOSING_FEES = 2.24  # Typical fee for 1 contract SPX

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

# Need to fetch the actual closing price from today's transactions
print("\nFetching today's transactions to get closing price...")

# Get from tastytrade API
import os
from dotenv import load_dotenv
import requests

load_dotenv()

# Authenticate
auth_response = requests.post(
    'https://api.tastyworks.com/sessions',
    json={
        'login': os.getenv('TASTYTRADE_USERNAME'),
        'password': os.getenv('TASTYTRADE_PASSWORD'),
        'remember-me': True
    }
)
auth_response.raise_for_status()
session_token = auth_response.json()['data']['session-token']

# Get account number
accounts_response = requests.get(
    'https://api.tastyworks.com/customers/me/accounts',
    headers={'Authorization': session_token}
)
accounts_response.raise_for_status()
account_number = accounts_response.json()['data']['items'][0]['account']['account-number']

# Get today's transactions
txn_response = requests.get(
    f'https://api.tastyworks.com/accounts/{account_number}/transactions',
    headers={'Authorization': session_token},
    params={
        'start-date': '2026-06-15',
        'end-date': '2026-06-15',
        'type': 'Trade'
    }
)
txn_response.raise_for_status()
transactions = txn_response.json()['data']['items']

# Find the SPX Bear Call CLOSE
spx_close = None
for txn in transactions:
    if txn.get('action') == 'Sell to Close' and txn.get('underlying-symbol') == 'SPX':
        symbol = txn.get('symbol', '')
        if 'C' in symbol:  # Call option
            net_value = float(txn.get('net-value', 0))
            value = float(txn.get('value', 0))
            commissions = float(txn.get('commissions', 0))
            fees = float(txn.get('fees', 0))

            print(f"\nFound CLOSE transaction:")
            print(f"  Symbol: {symbol}")
            print(f"  Net Value: ${net_value:.2f}")
            print(f"  Value: ${value:.2f}")
            print(f"  Commissions: ${commissions:.2f}")
            print(f"  Fees: ${fees:.2f}")

            spx_close = txn
            CLOSING_NET_PRICE = net_value
            CLOSING_FEES = abs(commissions + fees)
            break

if not spx_close:
    print("\n✗ Could not find SPX CLOSE transaction")
    sys.exit(1)

# Calculate updates
opening_price = float(row_data[10].replace('$', '').replace(',', '')) if len(row_data) > 10 else 0
opening_fees = float(row_data[9].replace('$', '').replace(',', '')) if len(row_data) > 9 else 0
total_fees = opening_fees + CLOSING_FEES
total_pnl = opening_price + CLOSING_NET_PRICE

print(f"\n{'='*60}")
print(f"CLOSING UPDATE:")
print(f"  Closing Date: {CLOSING_DATE}")
print(f"  Closing Net Price: ${CLOSING_NET_PRICE:.2f}")
print(f"  Closing Fees: ${CLOSING_FEES:.2f}")
print(f"  Total Fees: ${total_fees:.2f}")
print(f"  Total P&L: ${total_pnl:.2f}")
print(f"{'='*60}")

proceed = input("\nProceed with update? (y/n): ")
if proceed.lower() != 'y':
    print("Aborted.")
    sys.exit(0)

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
