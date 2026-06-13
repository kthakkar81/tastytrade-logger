"""Clean fix for SLV - delete row 759 and insert at row 343"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

print("Deleting malformed row 759...")
logger.sheet.delete_rows(759)

print("Inserting correct row at 343...")
original_row = [
    '6/10/2026',            # A: Opening Date
    '',                     # B: Closing Date
    'SLV',                  # C: Underlying
    'Bull Call Spread',     # D: Strategy
    'Open',                 # E: Status
    '7/17/2026',            # F: Expiration
    '$65.00',               # G: Short Strike
    '$64.00',               # H: Long Strike
    '',                     # I: Delta
    4.76,                   # J: Fees
    585.80,                 # K: Opening Net Price
    '',                     # L: Closing Net Price
    30,                     # M: Quantity
    '',                     # N: Total PnL
    ''                      # O: Notes
]

# Insert at row 343
logger.sheet.insert_row(original_row, 343, value_input_option='USER_ENTERED')
logger.format_new_row(343)

print("✓ Row inserted at 343")

# Verify
print("\n=== VERIFICATION ===")
all_rows = logger.sheet.get_all_values()
for i in range(341, min(346, len(all_rows))):
    row = all_rows[i]
    if len(row) > 12:
        underlying = row[2] if len(row) > 2 else ''
        strategy = row[3] if len(row) > 3 else ''
        qty = row[12] if len(row) > 12 else ''
        status = row[4] if len(row) > 4 else ''
        print(f"Row {i + 1}: {underlying} {strategy} Qty={qty} Status={status}")
