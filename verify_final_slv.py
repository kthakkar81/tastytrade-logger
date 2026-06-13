"""Verify final SLV values"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

all_rows = logger.sheet.get_all_values()

print("\n=== SLV BULL CALL SPREAD - FINAL STATE ===\n")

for row_num in [309, 310]:
    row = all_rows[row_num - 1]

    opening_date = row[0]
    closing_date = row[1]
    status = row[4]
    qty = row[12]
    fees = row[9]
    opening_price = row[10]
    closing_price = row[11] if len(row) > 11 else ''
    pnl = row[13] if len(row) > 13 else ''

    print(f"Row {row_num}: {status} - {qty} contracts")
    print(f"  Opening Date: {opening_date}")
    if closing_date:
        print(f"  Closing Date: {closing_date}")
    print(f"  Opening Price: {opening_price} (DEBIT - you paid)")
    if closing_price:
        print(f"  Closing Price: {closing_price} (CREDIT - you received)")
    print(f"  Fees: {fees}")
    if pnl:
        print(f"  Total P&L: {pnl}")
    print()

# Calculate expected values
print("=== EXPECTED VALUES ===\n")
print("Row 309 (Closed 10 contracts):")
print("  Opening: -$559.27 (DEBIT)")
print("  Closing: +$277.46 (CREDIT)")
print("  Fees: $9.27 (open) + $2.54 (close) = $11.81")
print("  P&L: -559.27 + 277.46 - 11.81 = -$293.62 (LOSS)")
print()
print("Row 310 (Open 20 contracts):")
print("  Opening: -$1,118.54 (DEBIT)")
print("  Fees: $18.54 (opening only)")
