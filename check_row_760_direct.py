"""Check row 760"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()
print(f"Total rows: {len(all_rows)}\n")

if len(all_rows) >= 760:
    row = all_rows[759]  # 0-indexed
    print("Row 760 contents:")
    for i in range(min(16, len(row))):
        col = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'][i]
        val = row[i] if row[i] else '(empty)'
        print(f"  {col} ({i}): {val}")
