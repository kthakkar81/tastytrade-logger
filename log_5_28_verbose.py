"""Log 5/28 SLV with verbose output"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
import config

client = TastytradeClient()
if not client.authenticate():
    exit(1)

transactions = client.get_transactions(start_date='2026-05-28', end_date='2026-05-28')
processor = TransactionProcessor()
processor.load_transactions(transactions)
trades = processor.process_orders()

# Find SLV trade
slv_trades = [t for t in trades if t.get('underlying') == 'SLV' and 'Call' in t.get('strategy', '')]

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

print(f"\nBefore logging - total rows: {len(logger.sheet.get_all_values())}\n")

for trade in slv_trades:
    print(f"Trade data:")
    print(f"  Action: {trade.get('action')}")
    print(f"  Date: {trade.get('trade_date')}")
    print(f"  Underlying: {trade.get('underlying')}")
    print(f"  Strategy: {trade.get('strategy')}")
    print(f"  Quantity: {trade.get('quantity')}")
    print(f"  Net Price: {trade.get('net_price')}")
    print(f"  Fees: {trade.get('fees')}")
    print(f"  Strikes: {trade.get('strikes')}")
    print(f"  Expiration: {trade.get('expiration')}")
    print()

    result = logger.append_trade(trade)
    print(f"Result: {result}")

print(f"\nAfter logging - total rows: {len(logger.sheet.get_all_values())}\n")

# Find the new row
all_rows = logger.sheet.get_all_values()
for i in range(len(all_rows) - 1, max(0, len(all_rows) - 20), -1):
    row = all_rows[i]
    if len(row) > 2 and row[2] == 'SLV':
        print(f"Found SLV at row {i + 1}:")
        print(f"  Opening: {row[0]}, Strategy: {row[3]}, Qty: {row[12] if len(row) > 12 else ''}")
        break
