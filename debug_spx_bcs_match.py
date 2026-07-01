"""
Debug SPX Bear Call Spread matching
"""
from spreadsheet_logger import SpreadsheetLogger
import config


def main():
    """Check for matching SPX BCS OPEN trades"""

    # The CLOSE trade details
    close_trade = {
        'action': 'CLOSE',
        'underlying': 'SPX',
        'strategy': 'Bear Call Spread',
        'expiration': '7/31/2026',
        'strikes': '$7,730.00/$7,700.00',
        'quantity': 1,
        'trade_date': '6/23/2026',
        'net_price': 0,
        'fees': 0
    }

    print("=" * 60)
    print("SEARCHING FOR MATCHING SPX BEAR CALL SPREAD OPEN")
    print("=" * 60)
    print()
    print("Looking for CLOSE trade:")
    print(f"  Underlying: {close_trade['underlying']}")
    print(f"  Strategy: {close_trade['strategy']}")
    print(f"  Expiration: {close_trade['expiration']}")
    print(f"  Strikes: {close_trade['strikes']}")
    print()

    # Connect to spreadsheet
    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        print("✗ Authentication failed")
        return

    # Parse strikes for comparison
    strikes = logger._parse_strikes(close_trade['strikes'], close_trade['strategy'])
    print(f"Parsed strikes:")
    print(f"  Short: {strikes['short']}")
    print(f"  Long: {strikes['long']}")
    print()

    # Get all rows from spreadsheet
    all_rows = logger.sheet.get_all_values()

    print(f"Scanning {len(all_rows) - 1} rows in spreadsheet...")
    print()

    # Look for potential matches
    matches = []
    for i in range(1, len(all_rows)):
        row = all_rows[i]
        if len(row) < 8:
            continue

        row_underlying = row[2]
        row_strategy = row[3]
        row_status = row[4]
        row_expiration = row[5]
        row_short_strike = row[6]
        row_long_strike = row[7]

        # Check if it's SPX Bear Call Spread
        if row_underlying == 'SPX' and row_strategy == 'Bear Call Spread':
            matches.append({
                'row': i + 1,
                'status': row_status,
                'expiration': row_expiration,
                'short_strike': row_short_strike,
                'long_strike': row_long_strike
            })

    if not matches:
        print("✗ No SPX Bear Call Spread rows found in spreadsheet")
        return

    print(f"Found {len(matches)} SPX Bear Call Spread row(s):")
    print()
    for match in matches:
        is_open = "✓" if match['status'] == 'Open' else "✗"
        print(f"Row {match['row']} [{is_open}]:")
        print(f"  Status: {match['status']}")
        print(f"  Expiration: {match['expiration']}")
        print(f"  Short Strike: {match['short_strike']}")
        print(f"  Long Strike: {match['long_strike']}")

        # Compare with close trade
        exp_match = match['expiration'] == close_trade['expiration'] or \
                   match['expiration'] == '07/31/2026'  # Check with leading zero
        short_match = match['short_strike'] == strikes['short']
        long_match = match['long_strike'] == strikes['long']

        print(f"  Matches:")
        print(f"    Expiration: {'✓' if exp_match else '✗'}")
        print(f"    Short Strike: {'✓' if short_match else '✗'} (need {strikes['short']})")
        print(f"    Long Strike: {'✓' if long_match else '✗'} (need {strikes['long']})")
        print()


if __name__ == "__main__":
    main()
