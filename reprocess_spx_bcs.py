"""
Reprocess SPX Bear Call Spread from 6/23
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
import config


def main():
    """Reprocess SPX BCS trade"""
    target_date = '2026-06-23'

    print("=" * 60)
    print(f"REPROCESSING SPX Bear Call Spread from {target_date}")
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

    # Filter for SPX Bear Call Spread only
    spx_bcs_trades = [t for t in trades if t.get('underlying') == 'SPX' and t.get('strategy') == 'Bear Call Spread']

    if not spx_bcs_trades:
        print("✗ No SPX Bear Call Spread trades found")
        return

    print(f"✓ Found {len(spx_bcs_trades)} SPX Bear Call Spread trade(s)")

    for trade in spx_bcs_trades:
        print(f"\n  Action: {trade.get('action')}")
        print(f"  Strikes: {trade.get('strikes')}")
        print(f"  Expiration: {trade.get('expiration')}")
        print(f"  Quantity: {trade.get('quantity')}")
    print()

    # 3. Write to PRODUCTION spreadsheet
    print("Step 3: Writing to PRODUCTION spreadsheet...")
    print(f"Sheet ID: {config.TRADE_LOG_SPREADSHEET_ID}")

    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        print("✗ Spreadsheet authentication failed")
        return

    count = 0
    for trade in spx_bcs_trades:
        if logger.append_trade(trade):
            count += 1

    print()
    print("=" * 60)
    print(f"✓ COMPLETE: {count}/{len(spx_bcs_trades)} SPX BCS trade(s) logged")
    print("=" * 60)


if __name__ == "__main__":
    main()
