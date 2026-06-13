"""Check actual SLV transactions"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor

client = TastytradeClient()
if not client.authenticate():
    exit(1)

# Check opening transaction (5/28)
print("=== OPENING TRANSACTION (5/28) ===\n")
open_txns = client.get_transactions(start_date='2026-05-28', end_date='2026-05-28')
processor = TransactionProcessor()
processor.load_transactions(open_txns)
open_trades = processor.process_orders()

for trade in open_trades:
    if trade.get('underlying') == 'SLV' and 'Call' in trade.get('strategy', ''):
        print(f"Action: {trade.get('action')}")
        print(f"Strategy: {trade.get('strategy')}")
        print(f"Date: {trade.get('trade_date')}")
        print(f"Strikes: {trade.get('strikes')}")
        print(f"Quantity: {trade.get('quantity')}")
        print(f"Net Price: {trade.get('net_price')}")
        print(f"Fees: {trade.get('fees')}")
        print()

# Check closing transaction (6/12)
print("=== CLOSING TRANSACTION (6/12) ===\n")
close_txns = client.get_transactions(start_date='2026-06-12', end_date='2026-06-12')
processor2 = TransactionProcessor()
processor2.load_transactions(close_txns)
close_trades = processor2.process_orders()

for trade in close_trades:
    if trade.get('underlying') == 'SLV':
        print(f"Action: {trade.get('action')}")
        print(f"Strategy: {trade.get('strategy')}")
        print(f"Date: {trade.get('trade_date')}")
        print(f"Strikes: {trade.get('strikes')}")
        print(f"Quantity: {trade.get('quantity')}")
        print(f"Net Price: {trade.get('net_price')}")
        print(f"Fees: {trade.get('fees')}")
        print()
