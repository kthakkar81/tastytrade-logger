"""Debug script to check SLV matching logic"""
from spreadsheet_logger import SpreadsheetLogger
import config

# Create test CLOSE trade
close_trade = {
    'underlying': 'SLV',
    'strategy': 'Bull Call Spread',
    'expiration': '7/17/2026',
    'strikes': '$65.00/$64.00',
    'quantity': 10,
    'action': 'CLOSE'
}

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    print("Failed to authenticate")
    exit(1)

# Parse strikes from CLOSE trade
strikes_str = close_trade.get('strikes', '')
strategy = close_trade.get('strategy', '')
strikes = logger._parse_strikes(strikes_str, strategy)

print(f"\n=== CLOSE TRADE ===")
print(f"Strikes string: {strikes_str}")
print(f"Parsed short: '{strikes['short']}'")
print(f"Parsed long: '{strikes['long']}'")
print()

# Get all rows
all_rows = logger.sheet.get_all_values()

print("=== CHECKING ROWS ===\n")
for i in range(1, len(all_rows)):
    row = all_rows[i]

    if len(row) > 2 and row[2] == 'SLV' and row[3] == 'Bull Call Spread' and row[4] == 'Open':
        row_short = row[6] if len(row) > 6 else ''
        row_long = row[7] if len(row) > 7 else ''
        row_exp = row[5] if len(row) > 5 else ''
        row_qty = row[12] if len(row) > 12 else ''

        short_match = row_short == strikes['short']
        long_match = row_long == strikes['long']

        print(f"Row {i + 1}:")
        print(f"  Expiration: '{row_exp}'")
        print(f"  Short strike: '{row_short}' (matches: {short_match})")
        print(f"  Long strike: '{row_long}' (matches: {long_match})")
        print(f"  Quantity: {row_qty}")
        print()

# Try the actual find method
print("=== USING find_all_open_trades ===")
matches = logger.find_all_open_trades(close_trade)
print(f"Found {len(matches)} matches: {matches}")
