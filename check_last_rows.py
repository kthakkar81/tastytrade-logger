"""Check last 10 rows of sheet"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()
total = len(all_rows)

print(f"\nTotal rows: {total}")
print("\n=== LAST 10 ROWS ===\n")

for i in range(max(1, total - 10), total):
    row = all_rows[i]
    opening_date = row[0] if len(row) > 0 else ''
    underlying = row[2] if len(row) > 2 else ''
    strategy = row[3] if len(row) > 3 else ''
    status = row[4] if len(row) > 4 else ''
    qty = row[12] if len(row) > 12 else ''

    if underlying or strategy:
        print(f"Row {i + 1}: {opening_date:12} {underlying:8} {strategy:18} {status:8} Qty={qty}")
