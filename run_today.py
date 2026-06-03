"""
Fetch today's trades and sync to test spreadsheet
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
from datetime import datetime
import config


def main():
    """Run sync for today"""
    today = datetime.now().strftime('%Y-%m-%d')

    print("=" * 60)
    print(f"TASTYTRADE LOGGER - Syncing trades for {today}")
    print("=" * 60)
    print()

    # 1. Fetch transactions
    print("Step 1: Fetching transactions from Tastytrade...")
    client = TastytradeClient()
    if not client.authenticate():
        print("✗ Authentication failed")
        return

    transactions = client.get_transactions(start_date=today, end_date=today)

    if not transactions:
        print(f"✓ No transactions found for {today}")
        return

    print(f"✓ Fetched {len(transactions)} raw transactions")
    print()

    # 2. Process trades
    print("Step 2: Processing transactions...")
    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    if not trades:
        print("✓ No trades to log")
        return

    print(f"✓ Processed {len(trades)} trades")

    # Show summary
    strategies = {}
    for trade in trades:
        strategy = trade.get('strategy', 'Unknown')
        strategies[strategy] = strategies.get(strategy, 0) + 1

    print("\nTrades by strategy:")
    for strategy, count in sorted(strategies.items()):
        print(f"  {strategy}: {count}")
    print()

    # 3. Write to spreadsheet
    print("Step 3: Writing to test spreadsheet...")
    if not hasattr(config, 'TEST_SPREADSHEET_ID'):
        print("✗ Missing TEST_SPREADSHEET_ID in config")
        return

    logger = SpreadsheetLogger(config.TEST_SPREADSHEET_ID)
    if not logger.authenticate():
        print("✗ Spreadsheet authentication failed")
        return

    count = logger.append_trades(trades)

    print()
    print("=" * 60)
    print(f"✓ COMPLETE: {count}/{len(trades)} trades logged successfully")
    print("=" * 60)


if __name__ == "__main__":
    main()
