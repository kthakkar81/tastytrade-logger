"""
Retry specific trade from Import Errors
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from spreadsheet_logger import SpreadsheetLogger
from datetime import datetime
import config


def main():
    """Retry RUT Bull Put Spread CLOSE"""
    today = datetime.now().strftime('%Y-%m-%d')

    print("Retrying RUT Bull Put Spread CLOSE trade...")
    print()

    # Fetch transactions
    client = TastytradeClient()
    if not client.authenticate():
        print("✗ Authentication failed")
        return

    transactions = client.get_transactions(start_date=today, end_date=today)

    # Process trades
    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    # Filter for RUT Bull Put Spread CLOSE
    rut_trade = None
    for trade in trades:
        if (trade.get('underlying') == 'RUT' and
            trade.get('strategy') == 'Bull Put Spread' and
            trade.get('action') == 'CLOSE'):
            rut_trade = trade
            break

    if not rut_trade:
        print("✗ No RUT Bull Put Spread CLOSE found in today's trades")
        return

    print(f"Found trade: {rut_trade.get('underlying')} {rut_trade.get('strategy')}")
    print(f"Strikes: {rut_trade.get('strikes')}")
    print(f"Expiration: {rut_trade.get('expiration')}")
    print()

    # Log to production spreadsheet
    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        print("✗ Spreadsheet authentication failed")
        return

    if logger.append_trade(rut_trade):
        print("\n✓ Successfully logged RUT Bull Put Spread CLOSE")
    else:
        print("\n✗ Failed to log trade")


if __name__ == "__main__":
    main()
