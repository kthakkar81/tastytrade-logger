"""Manually insert SLV 5/28 opening at correct position"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

# Find where to insert (after other 5/28 entries)
all_rows = logger.sheet.get_all_values()
insert_pos = 309  # After row 308 (last 5/28 entry)

# Create row with correct 5/28 data
slv_row = [
    '5/28/2026',           # A: Opening Date
    '',                    # B: Closing Date
    'SLV',                 # C: Underlying
    'Bull Call Spread',    # D: Strategy
    'Open',                # E: Status
    '7/17/2026',           # F: Expiration
    '$65.00',              # G: Short Strike
    '$64.00',              # H: Long Strike
    '',                    # I: Delta
    27.81,                 # J: Fees
    -1677.81,              # K: Opening Net Price (DEBIT - negative)
    '',                    # L: Closing Net Price
    30,                    # M: Quantity
    '',                    # N: Total PnL
    ''                     # O: Notes
]

print(f"Inserting SLV Bull Call Spread at row {insert_pos}...")
print(f"  Date: 5/28/2026")
print(f"  Quantity: 30")
print(f"  Opening Price: -$1,677.81 (DEBIT)")
print(f"  Fees: $27.81")
print()

logger.sheet.insert_row(slv_row, insert_pos, value_input_option='USER_ENTERED')
logger.format_new_row(insert_pos)

print(f"✓ Inserted at row {insert_pos}")

# Verify
all_rows = logger.sheet.get_all_values()
row = all_rows[insert_pos - 1]
print(f"\nVerification:")
print(f"  Row {insert_pos}: {row[2]} {row[3]} - Qty {row[12]}, Price {row[10]}")
