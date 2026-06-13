"""Debug script to check SLV positions"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    print("Failed to authenticate")
    exit(1)

# Get all rows
all_rows = logger.sheet.get_all_values()

print("\n=== SLV POSITIONS ===\n")
print(f"{'Row':<6} {'Status':<10} {'Underlying':<12} {'Strategy':<18} {'Exp':<12} {'Strikes':<20} {'Qty':<6}")
print("-" * 100)

for i, row in enumerate(all_rows[1:], start=2):  # Skip header, start at row 2
    if len(row) > 2 and 'SLV' in row[2]:  # Underlying column
        status = row[4] if len(row) > 4 else ''
        underlying = row[2] if len(row) > 2 else ''
        strategy = row[3] if len(row) > 3 else ''
        expiration = row[5] if len(row) > 5 else ''
        short_strike = row[6] if len(row) > 6 else ''
        long_strike = row[7] if len(row) > 7 else ''
        qty = row[12] if len(row) > 12 else ''

        strikes = f"{short_strike}/{long_strike}"

        print(f"{i:<6} {status:<10} {underlying:<12} {strategy:<18} {expiration:<12} {strikes:<20} {qty:<6}")

print("\n")
