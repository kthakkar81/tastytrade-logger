"""Clean up bad rows and restore SLV"""
from spreadsheet_logger import SpreadsheetLogger
import config

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

print("Deleting bad rows 760-761...")
logger.sheet.delete_rows(760, 761)

print("Restoring SLV row at 343...")
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

logger.sheet.insert_row(original_row, 343, value_input_option='USER_ENTERED')
logger.format_new_row(343)

print("✓ Complete")
