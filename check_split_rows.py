"""Check the split rows in detail"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print(f"Total rows: {len(all_rows)}\n")

for row_num in [760, 761]:
    if len(all_rows) >= row_num:
        row = all_rows[row_num - 1]
        print(f"=== Row {row_num} (length={len(row)}) ===")
        for i in range(min(16, len(row))):
            col_name = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P'][i]
            print(f"{col_name} ({i}): '{row[i]}'")
        print()
