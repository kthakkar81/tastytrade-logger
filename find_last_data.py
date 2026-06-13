"""Find last row with actual data"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print(f"Total rows: {len(all_rows)}\n")

# Find last row with data
for i in range(len(all_rows) - 1, -1, -1):
    row = all_rows[i]
    # Check if row has any non-empty cells
    if any(cell for cell in row):
        print(f"Last row with data: {i + 1}")
        underlying = row[2] if len(row) > 2 else ''
        strategy = row[3] if len(row) > 3 else ''
        opening_date = row[0] if len(row) > 0 else ''
        print(f"  Date: {opening_date}, {underlying} {strategy}")
        break
