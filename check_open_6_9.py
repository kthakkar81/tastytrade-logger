#!/usr/bin/env python3
"""Check the SPX Bear Call opening transaction from 6/9."""

from tastytrade_client import TastytradeClient

client = TastytradeClient()
client.authenticate()
transactions = client.get_transactions('2026-06-09', '2026-06-09')

print(f"Total transactions on 6/9: {len(transactions)}\n")

# Find the SPX Bear Call OPEN from 6/9
for txn in transactions:
    if txn.get('underlying-symbol') == 'SPX' and txn.get('action') in ['Sell to Open', 'Buy to Open']:
        symbol = txn.get('symbol', '')
        if '7500' in symbol or '7530' in symbol:
            print(f"Symbol: {symbol}")
            print(f"Action: {txn.get('action')}")
            print(f"Net Value: ${txn.get('net-value')}")
            print(f"Net Value Effect: {txn.get('net-value-effect')}")
            print(f"Commissions: ${txn.get('commissions')}")
            print(f"Fees: ${txn.get('fees')}")
            print()
