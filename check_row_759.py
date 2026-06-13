"""Check row 759"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()
print(f"\nTotal rows: {len(all_rows)}")

if len(all_rows) >= 759:
    row = all_rows[758]  # 0-indexed
    print(f"\nRow 759 (0-indexed 758):")
    for i, cell in enumerate(row):
        if cell:
            print(f"  Column {i}: {cell}")
else:
    print(f"Row 759 doesn't exist (sheet only has {len(all_rows)} rows)")
