"""
Manual fix for CLOSE trades that failed due to SPXW/RUTW normalization issue
"""
from spreadsheet_logger import SpreadsheetLogger
import config

# Create the two CLOSE trades from Import Errors
close_trades = [
    {
        'action': 'CLOSE',
        'underlying': 'SPXW',  # Will be normalized to SPX
        'strategy': 'Bear Call Spread',
        'expiration': '9/18/2026',
        'strikes': '$8,030.00/$8,000.00',
        'quantity': 1,
        'trade_date': '6/9/2026',
        'net_price': 0,  # Will need to get from transactions
        'fees': 0
    },
    {
        'action': 'CLOSE',
        'underlying': 'RUTW',  # Will be normalized to RUT
        'strategy': 'Bull Call Spread',
        'expiration': '6/30/2026',
        'strikes': '$2,790.00/$2,770.00',
        'quantity': 1,
        'trade_date': '6/9/2026',
        'net_price': 0,  # Will need to get from transactions
        'fees': 0
    }
]

# But we need the actual net_price and fees from the transactions
# Let me fetch the transactions and find these specific closes
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor

print("Fetching 6/9 transactions...")
client = TastytradeClient()
if not client.authenticate():
    exit(1)

transactions = client.get_transactions(start_date='2026-06-09', end_date='2026-06-09')

processor = TransactionProcessor()
processor.load_transactions(transactions)
trades = processor.process_orders()

# Find the SPXW and RUTW close trades
spx_close = None
rut_close = None

for trade in trades:
    if trade.get('action') == 'CLOSE':
        underlying = trade.get('underlying', '')
        strategy = trade.get('strategy', '')

        if 'SPX' in underlying and strategy == 'Bear Call Spread':
            spx_close = trade
            print(f"Found SPX close: {trade}")
        elif 'RUT' in underlying and strategy == 'Bull Call Spread':
            rut_close = trade
            print(f"Found RUT close: {trade}")

if not spx_close or not rut_close:
    print("✗ Could not find both close trades")
    exit(1)

# Now process them
print("\nProcessing close trades...")
logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

# Process SPX close
print("\nProcessing SPX Bear Call Spread close...")
if logger.append_trade(spx_close):
    print("✓ SPX close processed")
else:
    print("✗ SPX close failed")

# Process RUT close
print("\nProcessing RUT Bull Call Spread close...")
if logger.append_trade(rut_close):
    print("✓ RUT close processed")
else:
    print("✗ RUT close failed")

print("\nDone!")
