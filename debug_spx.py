#!/usr/bin/env python3
"""Debug: Show all SPX transactions from today."""

from tastytrade_client import TastytradeClient

client = TastytradeClient()
client.authenticate()
transactions = client.get_transactions('2026-06-15', '2026-06-15')

print(f"Total transactions: {len(transactions)}\n")

for i, txn in enumerate(transactions, 1):
    if txn.get('underlying-symbol') == 'SPX':
        print(f"\n--- SPX Transaction {i} ---")
        print(f"  Symbol: {txn.get('symbol')}")
        print(f"  Action: {txn.get('action')}")
        print(f"  Quantity: {txn.get('quantity')}")
        print(f"  Net Value: ${txn.get('net-value')}")
        print(f"  Commissions: ${txn.get('commissions')}")
        print(f"  Fees: ${txn.get('fees')}")
