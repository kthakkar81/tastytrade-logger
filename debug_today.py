"""
Debug: Show raw trade data for today
"""
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor
from datetime import datetime
import json


def main():
    today = datetime.now().strftime('%Y-%m-%d')

    client = TastytradeClient()
    if not client.authenticate():
        return

    transactions = client.get_transactions(start_date=today, end_date=today)

    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    print(f"Found {len(trades)} trades:\n")

    for i, trade in enumerate(trades, 1):
        print(f"Trade {i}:")
        print(json.dumps(trade, indent=2, default=str))
        print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
