"""Debug script to check SLV CLOSE trade"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')

print(f"Checking transactions for {today}")

client = TastytradeClient()
if not client.authenticate():
    print("Auth failed")
    exit(1)

transactions = client.get_transactions(start_date=today, end_date=today)
processor = TransactionProcessor()
processor.load_transactions(transactions)
trades = processor.process_orders()

print("\n=== TRADES ===\n")
for trade in trades:
    if trade.get('underlying') == 'SLV':
        print(f"Action: {trade.get('action')}")
        print(f"Strategy: {trade.get('strategy')}")
        print(f"Strikes: {trade.get('strikes')}")
        print(f"Expiration: {trade.get('expiration')}")
        print(f"Quantity: {trade.get('quantity')}")
        print(f"Trade Date: {trade.get('trade_date')}")
        print()
