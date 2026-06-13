"""Log 5/28 SLV opening"""
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

print(f"Found {len(slv_trades)} SLV Bull Call trades\n")

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

for trade in slv_trades:
    print(f"Logging: {trade.get('action')} {trade.get('strategy')} Qty={trade.get('quantity')}, Price={trade.get('net_price')}, Fees={trade.get('fees')}")
    logger.append_trade(trade)
