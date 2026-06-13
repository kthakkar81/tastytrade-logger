"""Find SLV opening from 5/28"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print("\n=== ALL SLV POSITIONS (Open and Closed) ===\n")
for i, row in enumerate(all_rows[1:], start=2):
    if len(row) > 2 and row[2] == 'SLV':
        opening_date = row[0] if len(row) > 0 else ''
        status = row[4] if len(row) > 4 else ''
        strategy = row[3] if len(row) > 3 else ''
        qty = row[12] if len(row) > 12 else ''
        opening_price = row[10] if len(row) > 10 else ''

        # Check for 5/28 opening date or Bull Call Spread
        if '5/28' in opening_date or 'Bull Call' in strategy:
            print(f"Row {i}:")
            print(f"  Opening Date: {opening_date}")
            print(f"  Strategy: {strategy}")
            print(f"  Status: {status}")
            print(f"  Quantity: {qty}")
            print(f"  Opening Price: {opening_price}")
            print()
