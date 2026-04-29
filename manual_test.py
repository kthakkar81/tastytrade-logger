"""
Manual verification test
Displays processed trades for manual comparison against Tastytrade UI
Run with: python manual_test.py
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from datetime import datetime, timedelta
import json


def format_trade_for_review(trade, index):
    """Format a trade for manual review"""
    print(f"\n{'=' * 80}")
    print(f"TRADE #{index}")
    print(f"{'=' * 80}")

    action = trade.get('action')
    underlying = trade.get('underlying')
    strategy = trade.get('strategy')
    trade_date = trade.get('trade_date')

    print(f"Action:     {action}")
    print(f"Underlying: {underlying}")
    print(f"Strategy:   {strategy}")
    print(f"Date:       {trade_date}")

    if action == 'ROLL':
        print(f"\nROLL DETAILS:")
        print(f"  Old Expiration: {trade.get('old_expiration')}")
        print(f"  New Expiration: {trade.get('new_expiration')}")
        print(f"  Old Strikes:    {trade.get('old_strikes')}")
        print(f"  New Strikes:    {trade.get('new_strikes')}")
        print(f"  Old Strategy:   {trade.get('old_strategy')}")
        print(f"  New Strategy:   {trade.get('new_strategy')}")
        print(f"\nFINANCIALS:")
        print(f"  Close Net:      ${trade.get('close_net_price', 0):>10,.2f}")
        print(f"  Open Net:       ${trade.get('open_net_price', 0):>10,.2f}")
        print(f"  Roll Credit:    ${trade.get('roll_credit', 0):>10,.2f}")
        print(f"  Fees:           ${trade.get('fees', 0):>10,.2f}")
    else:
        print(f"Expiration: {trade.get('expiration')}")
        print(f"Strikes:    {trade.get('strikes')}")
        print(f"Quantity:   {trade.get('quantity')}")
        print(f"\nFINANCIALS:")
        print(f"  Net Price:      ${trade.get('net_price', 0):>10,.2f}")
        print(f"  Fees:           ${trade.get('fees', 0):>10,.2f}")
        if action == 'OPEN':
            print(f"  Credit Received: ${trade.get('net_price', 0):,.2f}" if trade.get('net_price', 0) > 0 else f"  Debit Paid:      ${abs(trade.get('net_price', 0)):,.2f}")

    # Show raw order ID for reference
    order_id = trade.get('order_id')
    if order_id:
        print(f"\nOrder ID: {order_id}")

    # Show legs
    legs = trade.get('legs', [])
    if legs:
        print(f"\nLEGS ({len(legs)} total):")
        for i, leg in enumerate(legs, 1):
            symbol = leg.get('symbol', 'N/A')
            action_leg = leg.get('action', 'N/A')
            quantity = leg.get('quantity', 0)
            value = leg.get('value', 0)
            print(f"  Leg {i}: {action_leg:<15} {quantity:>3}x {symbol:<25} ${float(value):>10,.2f}")

    print(f"\n{'=' * 80}\n")


def main():
    """Run manual verification"""
    print("\n" + "=" * 80)
    print("TASTYTRADE LOGGER - MANUAL VERIFICATION")
    print("=" * 80)
    print("\nThis script displays processed trades for manual comparison")
    print("against your Tastytrade account history.\n")

    # Get date range from user
    print("Enter date range for verification:")

    # Default to last 7 days
    default_start = (datetime.now() - timedelta(days=7)).strftime('%m-%d-%Y')
    default_end = datetime.now().strftime('%m-%d-%Y')

    start_input = input(f"Start date (MM-DD-YYYY, default: {default_start}): ").strip()
    start_date_display = start_input if start_input else default_start

    end_input = input(f"End date (MM-DD-YYYY, default: {default_end}): ").strip()
    end_date_display = end_input if end_input else default_end

    # Validate dates
    try:
        start_date = datetime.strptime(start_date_display, '%m-%d-%Y')
        end_date = datetime.strptime(end_date_display, '%m-%d-%Y')
    except ValueError:
        print("❌ Invalid date format. Use MM-DD-YYYY")
        return

    if start_date > end_date:
        print("❌ Start date must be before or equal to end date")
        return

    # Convert to API format (YYYY-MM-DD)
    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    print(f"\nFetching transactions from {start_date_display} to {end_date_display}...\n")

    # Authenticate and fetch
    client = TastytradeClient()
    if not client.authenticate():
        print("❌ Authentication failed")
        return

    transactions = client.get_transactions(
        start_date=start_date_str,
        end_date=end_date_str
    )

    if not transactions:
        print("❌ No transactions found in date range")
        return

    print(f"✅ Fetched {len(transactions)} raw transactions\n")

    # Process
    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    if not trades:
        print("❌ No trades processed")
        return

    print(f"✅ Processed into {len(trades)} trades\n")

    # Group by underlying for easier review
    trades_by_underlying = {}
    for trade in trades:
        underlying = trade.get('underlying', 'Unknown')
        if underlying not in trades_by_underlying:
            trades_by_underlying[underlying] = []
        trades_by_underlying[underlying].append(trade)

    print(f"Trades grouped by {len(trades_by_underlying)} underlying(s):")
    for underlying, underlying_trades in sorted(trades_by_underlying.items()):
        print(f"  {underlying}: {len(underlying_trades)} trade(s)")

    print("\n" + "=" * 80)
    print("REVIEW INSTRUCTIONS:")
    print("=" * 80)
    print("1. Open Tastytrade web/app and navigate to your trade history")
    print("2. For each trade below, verify:")
    print("   ✓ Strategy classification is correct")
    print("   ✓ Strike prices match")
    print("   ✓ Net price/credit matches (within pennies for rounding)")
    print("   ✓ Fees are accurate")
    print("   ✓ Rolls are correctly detected and linked")
    print("3. Mark any discrepancies for investigation")
    print("=" * 80)

    input("\nPress Enter to start reviewing trades...")

    # Display each trade
    for i, trade in enumerate(trades, 1):
        format_trade_for_review(trade, i)

        # Pause after each trade for review
        if i < len(trades):
            response = input("Press Enter for next trade, 's' to stop, or 'd' to dump JSON: ").strip().lower()
            if response == 's':
                print("\n⚠️  Review stopped by user")
                break
            elif response == 'd':
                print(f"\nJSON dump of Trade #{i}:")
                print(json.dumps(trade, indent=2, default=str))
                input("\nPress Enter to continue...")

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION CHECKLIST")
    print("=" * 80)
    print("\nDid you verify:")
    print("[ ] All strategy classifications are correct?")
    print("[ ] All strike prices match Tastytrade?")
    print("[ ] All credits/debits match Tastytrade (within rounding)?")
    print("[ ] All fees are accurate?")
    print("[ ] All rolls are correctly detected?")
    print("[ ] No trades are missing?")
    print("[ ] No duplicate trades?")

    print("\n" + "=" * 80)
    print("If all checks passed, the trade logger is ready for automation!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
