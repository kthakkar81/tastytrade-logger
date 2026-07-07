"""
Sync recent trades to the PRODUCTION spreadsheet.

Fetches a rolling lookback window (not just today) so that if a scheduled
run is delayed — e.g. the Mac was asleep/off at the scheduled time and
launchd runs the job on the next wake — any days missed in between are
still backfilled. Duplicate detection in the logger makes re-syncing the
same days idempotent.

Every run records itself to the 'Sync Log' worksheet (status, date range,
trade count, details) so "did it run?" is always answerable by looking at
the sheet, independent of push notifications.
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import config

# How many calendar days back to sync on every run. A delayed catch-up run
# uses this window to backfill any days missed while the Mac was down.
LOOKBACK_DAYS = 5


def main():
    """Run sync for the rolling lookback window on the production sheet."""
    # Use Pacific timezone explicitly (cloud/UTC environments compute the
    # wrong date otherwise).
    pacific_tz = ZoneInfo('America/Los_Angeles')
    today = datetime.now(pacific_tz)
    start_date = (today - timedelta(days=LOOKBACK_DAYS - 1)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    date_range = f"{start_date}..{end_date}"

    print("=" * 60)
    print(f"TASTYTRADE LOGGER - PRODUCTION SYNC for {date_range}")
    print("=" * 60)
    print()

    # Authenticate the spreadsheet logger up front so we can always write a
    # Sync Log heartbeat row, even if the Tastytrade side fails below.
    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    sheet_ok = logger.authenticate()
    if not sheet_ok:
        print("✗ Spreadsheet authentication failed — cannot log run")
        return 1

    def record(status, count=0, details=''):
        logger.log_run(status, date_range=date_range,
                       trades_logged=count, details=details)

    try:
        # 1. Fetch transactions across the lookback window
        print("Step 1: Fetching transactions from Tastytrade...")
        client = TastytradeClient()
        if not client.authenticate():
            print("✗ Authentication failed")
            record('FAILED', details='Tastytrade authentication failed')
            return 1

        transactions = client.get_transactions(start_date=start_date,
                                                end_date=end_date)

        if not transactions:
            print(f"✓ No transactions found for {date_range}")
            record('OK', details='No transactions in window')
            return 0

        print(f"✓ Fetched {len(transactions)} raw transactions")
        print()

        # 2. Process trades
        print("Step 2: Processing transactions...")
        processor = TransactionProcessor()
        processor.load_transactions(transactions)
        trades = processor.process_orders()

        if not trades:
            print("✓ No trades to log")
            record('OK', details='No trades to log in window')
            return 0

        print(f"✓ Processed {len(trades)} trades")

        strategies = {}
        for trade in trades:
            strategy = trade.get('strategy', trade.get('new_strategy', 'Unknown'))
            strategies[strategy] = strategies.get(strategy, 0) + 1

        strategy_summary = ", ".join(
            f"{s}: {c}" for s, c in sorted(strategies.items()))
        print("\nTrades by strategy:")
        for strategy, count in sorted(strategies.items()):
            print(f"  {strategy}: {count}")
        print()

        # 3. Write to PRODUCTION spreadsheet (idempotent — dedupes re-runs)
        print("Step 3: Writing to PRODUCTION spreadsheet...")
        print(f"Sheet ID: {config.TRADE_LOG_SPREADSHEET_ID}")
        count = logger.append_trades(trades)

        print()
        print("=" * 60)
        print(f"✓ COMPLETE: {count}/{len(trades)} new trades logged to PRODUCTION")
        print("=" * 60)
        record('OK', count=count,
               details=f"{count} new of {len(trades)} in window; {strategy_summary}")
        return 0

    except Exception as e:
        import traceback
        traceback.print_exc()
        record('FAILED', details=f"{type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
