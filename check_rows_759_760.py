"""Check rows 759-760"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()
print(f"\nTotal rows: {len(all_rows)}")

for row_num in [759, 760]:
    if len(all_rows) >= row_num:
        row = all_rows[row_num - 1]  # Convert to 0-indexed
        print(f"\n=== Row {row_num} ===")
        print(f"Opening Date: {row[0] if len(row) > 0 else ''}")
        print(f"Closing Date: {row[1] if len(row) > 1 else ''}")
        print(f"Underlying: {row[2] if len(row) > 2 else ''}")
        print(f"Strategy: {row[3] if len(row) > 3 else ''}")
        print(f"Status: {row[4] if len(row) > 4 else ''}")
        print(f"Expiration: {row[5] if len(row) > 5 else ''}")
        print(f"Short Strike: {row[6] if len(row) > 6 else ''}")
        print(f"Long Strike: {row[7] if len(row) > 7 else ''}")
        print(f"Quantity: {row[12] if len(row) > 12 else ''}")
    else:
        print(f"\nRow {row_num} doesn't exist")
