"""Check if SLV Bull Call Spread already exists"""
from spreadsheet_logger import SpreadsheetLogger
import config

# Test trade
test_trade = {
    'underlying': 'SLV',
    'strategy': 'Bull Call Spread',
    'expiration': '7/17/2026',
    'strikes': '$65.00/$64.00',
    'quantity': 30,
    'action': 'OPEN',
    'trade_date': '5/28/2026'
}

logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
if not logger.authenticate():
    exit(1)

# Check for existing
existing = logger.find_existing_open(test_trade)
if existing:
    print(f"\n✓ Found existing OPEN at row {existing}")

    # Get the row details
    all_rows = logger.sheet.get_all_values()
    row = all_rows[existing - 1]

    print(f"\nRow details:")
    print(f"  Opening Date: {row[0]}")
    print(f"  Underlying: {row[2]}")
    print(f"  Strategy: {row[3]}")
    print(f"  Status: {row[4]}")
    print(f"  Quantity: {row[12]}")
    print(f"  Price: {row[10]}")
    print(f"  Fees: {row[9]}")
else:
    print("\n✗ No existing OPEN found")
