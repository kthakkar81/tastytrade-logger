"""Fix SLV split - delete rows 343-344 and restore original 30-contract row"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    print("Failed to authenticate")
    exit(1)

print("\n=== BEFORE ===")
all_rows = logger.sheet.get_all_values()
for i in range(342, min(345, len(all_rows))):
    row = all_rows[i]
    if len(row) > 12:
        print(f"Row {i + 1}: {row[2]} {row[3]} Qty={row[12]} Status={row[4] if len(row) > 4 else ''}")

print("\nDeleting rows 343-344...")
logger.sheet.delete_rows(343, 344)

print("\nRecreating original 30-contract OPEN row...")
# Create the original row
original_row = [
    '6/10/2026',            # Opening Date
    '',                     # Closing Date
    'SLV',                  # Underlying
    'Bull Call Spread',     # Strategy
    'Open',                 # Status
    '7/17/2026',            # Expiration
    '$65.00',               # Short Strike
    '$64.00',               # Long Strike
    '',                     # Delta
    4.76,                   # Fees
    585.80,                 # Opening Net Price
    '',                     # Closing Net Price
    30,                     # Quantity
    '',                     # Total PnL
    ''                      # Notes
]

logger.sheet.append_row(original_row, value_input_option='USER_ENTERED')
all_rows = logger.sheet.get_all_values()
new_row_num = len(all_rows)
logger.format_new_row(new_row_num)

print(f"✓ Restored row at {new_row_num}")

print("\n=== AFTER ===")
all_rows = logger.sheet.get_all_values()
for i in range(341, min(345, len(all_rows))):
    row = all_rows[i]
    if len(row) > 12:
        print(f"Row {i + 1}: {row[2]} {row[3]} Qty={row[12]} Status={row[4] if len(row) > 4 else ''}")
