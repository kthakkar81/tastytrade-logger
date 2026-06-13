"""Find all SLV Bull Call Spreads"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print(f"\nTotal rows in sheet: {len(all_rows)}")
print("\n=== SLV BULL CALL SPREADS ===\n")

for row_num in range(1, len(all_rows) + 1):
    row = all_rows[row_num - 1]
    if len(row) > 3:
        underlying = row[2] if len(row) > 2 else ''
        strategy = row[3] if len(row) > 3 else ''

        if underlying == 'SLV' and 'Bull Call' in strategy:
            status = row[4] if len(row) > 4 else ''
            exp = row[5] if len(row) > 5 else ''
            short_strike = row[6] if len(row) > 6 else ''
            long_strike = row[7] if len(row) > 7 else ''
            qty = row[12] if len(row) > 12 else ''
            opening_date = row[0] if len(row) > 0 else ''
            closing_date = row[1] if len(row) > 1 else ''

            print(f"Row {row_num}:")
            print(f"  Opening: {opening_date}, Closing: {closing_date}")
            print(f"  Status: {status}, Quantity: {qty}")
            print(f"  Expiration: {exp}, Strikes: {short_strike}/{long_strike}")
            print()
