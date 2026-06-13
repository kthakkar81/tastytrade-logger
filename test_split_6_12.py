"""Test split for 6/12"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
import config

date = '2026-06-12'

print(f"Testing for {date}\n")

client = TastytradeClient()
if not client.authenticate():
    exit(1)

transactions = client.get_transactions(start_date=date, end_date=date)
processor = TransactionProcessor()
processor.load_transactions(transactions)
trades = processor.process_orders()

# Filter to just SLV
slv_trades = [t for t in trades if t.get('underlying') == 'SLV']

print(f"Found {len(slv_trades)} SLV trades\n")

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

for trade in slv_trades:
    print(f"Processing: {trade.get('action')} {trade.get('strategy')} Qty={trade.get('quantity')}")
    logger.append_trade(trade)
