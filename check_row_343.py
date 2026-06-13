"""Check row 343 and surrounding rows"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print("\n=== ROWS 340-350 ===\n")
for row_num in range(340, min(351, len(all_rows) + 1)):
    if len(all_rows) >= row_num:
        row = all_rows[row_num - 1]
        underlying = row[2] if len(row) > 2 else ''
        strategy = row[3] if len(row) > 3 else ''
        status = row[4] if len(row) > 4 else ''
        qty = row[12] if len(row) > 12 else ''

        if underlying or strategy:
            print(f"Row {row_num}: {underlying:8} {strategy:18} Status={status:8} Qty={qty}")
