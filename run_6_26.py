"""
Fetch 6/26 trades and sync to PRODUCTION spreadsheet
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
import config


def main():
    """Run sync for 6/26 on production sheet"""
    target_date = '2026-06-26'

    print("=" * 60)
    print(f"TASTYTRADE LOGGER - PRODUCTION SYNC for {target_date}")
    print("=" * 60)
    print()

    # 1. Fetch transactions
    print("Step 1: Fetching transactions from Tastytrade...")
    client = TastytradeClient()
    if not client.authenticate():
        print("✗ Authentication failed")
        return

    transactions = client.get_transactions(start_date=target_date, end_date=target_date)

    if not transactions:
        print(f"✓ No transactions found for {target_date}")
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
        strategy = trade.get('strategy', trade.get('new_strategy', 'Unknown'))
        strategies[strategy] = strategies.get(strategy, 0) + 1

    print("\nTrades by strategy:")
    for strategy, count in sorted(strategies.items()):
        print(f"  {strategy}: {count}")
    print()

    # 3. Write to PRODUCTION spreadsheet
    print("Step 3: Writing to PRODUCTION spreadsheet...")
    print(f"Sheet ID: {config.TRADE_LOG_SPREADSHEET_ID}")

    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        print("✗ Spreadsheet authentication failed")
        return

    count = logger.append_trades(trades)

    print()
    print("=" * 60)
    print(f"✓ COMPLETE: {count}/{len(trades)} trades logged to PRODUCTION")
    print("=" * 60)


if __name__ == "__main__":
    main()
