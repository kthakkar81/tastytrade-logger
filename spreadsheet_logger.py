"""
Spreadsheet Logger
Writes processed trades to Google Sheets trading log
"""
from typing import List, Dict
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import config


class SpreadsheetLogger:
    """Logs trades to Google Sheets"""

    def __init__(self, spreadsheet_id: str):
        """
        Initialize logger with spreadsheet ID

        Args:
            spreadsheet_id: Google Sheets spreadsheet ID
        """
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.sheet = None

    def authenticate(self) -> bool:
        """
        Authenticate with Google Sheets API

        Returns:
            bool: True if authentication successful
        """
        try:
            # Define scope
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            # Load credentials from config
            if not hasattr(config, 'GOOGLE_SHEETS_CREDENTIALS_FILE'):
                print("✗ Missing GOOGLE_SHEETS_CREDENTIALS_FILE in config")
                print("  Please add your service account credentials file path to config.py")
                return False

            creds = Credentials.from_service_account_file(
                config.GOOGLE_SHEETS_CREDENTIALS_FILE,
                scopes=scopes
            )

            # Authorize and open spreadsheet
            self.client = gspread.authorize(creds)
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)

            # Get first sheet (or specify sheet name if needed)
            self.sheet = spreadsheet.sheet1

            print(f"✓ Connected to spreadsheet: {spreadsheet.title}")
            return True

        except Exception as e:
            print(f"✗ Spreadsheet authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def format_trade_row(self, trade: Dict) -> List[str]:
        """
        Format a processed trade into spreadsheet row format

        Args:
            trade: Processed trade dictionary

        Returns:
            List of cell values for the row
        """
        action = trade.get('action', '')

        # Common fields
        underlying = trade.get('underlying', '')
        strategy = trade.get('strategy', '')
        expiration = trade.get('expiration', '')
        quantity = trade.get('quantity', 0)
        fees = trade.get('fees', 0)

        if action == 'OPEN':
            # Opening transaction
            opening_date = trade.get('trade_date', '')
            closing_date = ''
            status = 'Open'
            net_price = trade.get('net_price', 0)

            # Parse strikes
            strikes = self._parse_strikes(trade.get('strikes', ''), strategy)

            row = [
                opening_date,           # Opening Date
                closing_date,           # Closing Date (blank for opens)
                underlying,             # Underlying
                strategy,               # Strategy Type
                status,                 # Status
                expiration,             # Expiration
                strikes['short'],       # Short/CSP/CC Strike
                strikes['long'],        # Long Strike
                '',                     # Delta (blank for now)
                f"${fees:.2f}",         # Fees
                f"${net_price:.2f}",    # Opening Net Price
                '',                     # Closing Net Price (blank for opens)
                str(quantity),          # Contracts
                '',                     # Total PnL (blank for opens)
                '',                     # ROC (blank for now)
                ''                      # Notes/Setup
            ]

        elif action == 'CLOSE':
            # Closing transaction - log as separate row for now
            # TODO: Could enhance to find and update matching open row
            opening_date = ''
            closing_date = trade.get('trade_date', '')
            status = 'Closed'
            net_price = trade.get('net_price', 0)

            strikes = self._parse_strikes(trade.get('strikes', ''), strategy)

            row = [
                opening_date,           # Opening Date (blank - manual match needed)
                closing_date,           # Closing Date
                underlying,             # Underlying
                strategy,               # Strategy Type
                status,                 # Status
                expiration,             # Expiration
                strikes['short'],       # Short/CSP/CC Strike
                strikes['long'],        # Long Strike
                '',                     # Delta
                f"${fees:.2f}",         # Fees
                '',                     # Opening Net Price (blank)
                f"${net_price:.2f}",    # Closing Net Price
                str(quantity),          # Contracts
                '',                     # Total PnL (calculate manually)
                '',                     # ROC
                ''                      # Notes
            ]

        elif action == 'ROLL':
            # Roll = close old + open new
            # For now, return the new opening position
            # TODO: Could log both the close and the new open
            opening_date = trade.get('trade_date', '')
            closing_date = ''
            status = 'Open'
            net_price = trade.get('open_net_price', 0)
            roll_credit = trade.get('roll_credit', 0)

            strikes = self._parse_strikes(trade.get('new_strikes', ''), trade.get('new_strategy', ''))

            row = [
                opening_date,
                closing_date,
                underlying,
                trade.get('new_strategy', ''),
                status,
                trade.get('new_expiration', ''),
                strikes['short'],
                strikes['long'],
                '',
                f"${fees:.2f}",
                f"${net_price:.2f}",
                '',
                str(quantity),
                '',
                '',
                f"Roll credit: ${roll_credit:.2f}"
            ]

        else:
            # Unknown action
            row = [''] * 16

        return row

    def _parse_strikes(self, strikes_str: str, strategy: str) -> Dict[str, str]:
        """
        Parse strikes string into short and long components

        Args:
            strikes_str: Strike string (e.g., "$350.00/$340.00" or "$350.00P")
            strategy: Strategy type to determine which is short/long

        Returns:
            Dict with 'short' and 'long' keys
        """
        result = {'short': '', 'long': ''}

        if not strikes_str:
            return result

        # Remove option type suffix (P/C) if present
        clean_str = strikes_str.replace('P', '').replace('C', '')

        # Split by slash for spreads
        parts = clean_str.split('/')

        if len(parts) == 1:
            # Single leg (CSP, Covered Call, Long Put/Call)
            if strategy in ['CSP', 'Covered Call']:
                result['short'] = parts[0]
            else:
                result['long'] = parts[0]

        elif len(parts) == 2:
            # Two-leg spread
            if strategy == 'Bull Put Spread':
                # Higher strike is sold, lower is bought
                result['short'] = parts[0]  # First one (higher)
                result['long'] = parts[1]   # Second one (lower)
            elif strategy == 'Bear Call Spread':
                # Lower strike is sold, higher is bought
                result['short'] = parts[0]  # First one (lower)
                result['long'] = parts[1]   # Second one (higher)
            elif strategy == 'Bull Call Spread':
                # Lower strike is bought, higher is sold
                result['long'] = parts[0]   # First one (lower)
                result['short'] = parts[1]  # Second one (higher)
            else:
                # Default: assume first is short, second is long
                result['short'] = parts[0]
                result['long'] = parts[1]

        return result

    def append_trade(self, trade: Dict) -> bool:
        """
        Append a single trade to the spreadsheet

        Args:
            trade: Processed trade dictionary

        Returns:
            bool: True if successful
        """
        if not self.sheet:
            print("✗ Not connected to spreadsheet")
            return False

        try:
            row = self.format_trade_row(trade)
            self.sheet.append_row(row)

            print(f"✓ Logged {trade.get('action')} {trade.get('underlying')} {trade.get('strategy', trade.get('new_strategy', ''))}")
            return True

        except Exception as e:
            print(f"✗ Failed to append trade: {e}")
            import traceback
            traceback.print_exc()
            return False

    def append_trades(self, trades: List[Dict]) -> int:
        """
        Append multiple trades to the spreadsheet

        Args:
            trades: List of processed trade dictionaries

        Returns:
            Number of trades successfully logged
        """
        count = 0
        for trade in trades:
            if self.append_trade(trade):
                count += 1

        print(f"\n✓ Logged {count}/{len(trades)} trades to spreadsheet")
        return count


# Test function
def test_logger():
    """Test spreadsheet logging"""
    from tastytrade_client import TastytradeClient
    from transaction_processor import TransactionProcessor

    print("Testing Spreadsheet Logger...\n")

    # Use test spreadsheet ID from config
    if not hasattr(config, 'TEST_SPREADSHEET_ID'):
        print("✗ Missing TEST_SPREADSHEET_ID in config")
        print("  Please add TEST_SPREADSHEET_ID = '1dykZLMLgXwVU3PXmsu_i_jEHzyPGa-m24Kef8L71R8k' to config.py")
        return

    # Fetch and process transactions
    client = TastytradeClient()
    if not client.authenticate():
        return

    transactions = client.get_transactions(start_date='2026-04-27', end_date='2026-04-27')

    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    # Log to spreadsheet
    logger = SpreadsheetLogger(config.TEST_SPREADSHEET_ID)
    if not logger.authenticate():
        return

    logger.append_trades(trades)


if __name__ == "__main__":
    test_logger()
