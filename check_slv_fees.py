"""Check SLV fees"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print("\n=== SLV BULL CALL SPREAD FEES ===\n")
for row_num in [343, 344]:
    row = all_rows[row_num - 1]
    underlying = row[2]
    strategy = row[3]
    status = row[4]
    qty = row[12]
    fees = row[9] if len(row) > 9 else ''
    opening_price = row[10] if len(row) > 10 else ''
    closing_price = row[11] if len(row) > 11 else ''
    pnl = row[13] if len(row) > 13 else ''

    print(f"Row {row_num}: {status} - Qty {qty}")
    print(f"  Fees: {fees}")
    print(f"  Opening Price: {opening_price}")
    print(f"  Closing Price: {closing_price}")
    print(f"  P&L: {pnl}")
    print()

# Calculate what the fees should be
print("Expected values for row 343 (closed 10 contracts):")
print("  Opening fees for 30 contracts: $4.76")
print("  Proportional opening fees for 10 contracts: $4.76 * (10/30) = $1.59")
print("  Need to check actual closing fees from transaction...")
