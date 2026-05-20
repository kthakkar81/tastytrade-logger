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
        self.error_sheet = None

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

            # Get or create error log sheet
            try:
                self.error_sheet = spreadsheet.worksheet('Import Errors')
                # Verify header exists and is correct
                first_row = self.error_sheet.row_values(1)
                expected_header = ['Date', 'Underlying', 'Strategy', 'Expiration',
                                 'Strikes', 'Action', 'Error', 'Details']
                if first_row != expected_header:
                    # Clear and add proper header
                    self.error_sheet.clear()
                    self.error_sheet.append_row(expected_header)
            except:
                # Create error sheet if it doesn't exist
                self.error_sheet = spreadsheet.add_worksheet(title='Import Errors', rows=100, cols=10)
                # Add header row
                self.error_sheet.append_row([
                    'Date', 'Underlying', 'Strategy', 'Expiration',
                    'Strikes', 'Action', 'Error', 'Details'
                ])

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
            # Two-leg spread - need to determine which is higher/lower
            try:
                strike1 = float(parts[0].replace('$', '').replace(',', ''))
                strike2 = float(parts[1].replace('$', '').replace(',', ''))

                if strategy == 'Bull Put Spread':
                    # Higher strike is sold, lower is bought
                    if strike1 > strike2:
                        result['short'] = parts[0]  # Higher
                        result['long'] = parts[1]   # Lower
                    else:
                        result['short'] = parts[1]  # Higher
                        result['long'] = parts[0]   # Lower

                elif strategy == 'Bear Call Spread':
                    # Lower strike is sold, higher is bought
                    if strike1 < strike2:
                        result['short'] = parts[0]  # Lower
                        result['long'] = parts[1]   # Higher
                    else:
                        result['short'] = parts[1]  # Lower
                        result['long'] = parts[0]   # Higher

                elif strategy == 'Bull Call Spread':
                    # Lower strike is bought, higher is sold
                    if strike1 < strike2:
                        result['long'] = parts[0]   # Lower
                        result['short'] = parts[1]  # Higher
                    else:
                        result['long'] = parts[1]   # Lower
                        result['short'] = parts[0]  # Higher
                else:
                    # Default: assume first is short, second is long
                    result['short'] = parts[0]
                    result['long'] = parts[1]
            except:
                # Fallback if parsing fails
                result['short'] = parts[0]
                result['long'] = parts[1]

        return result

    def find_open_trade(self, trade: Dict) -> int:
        """
        Find matching OPEN trade row in spreadsheet

        Args:
            trade: CLOSE trade to match

        Returns:
            Row number (1-indexed) if found, None otherwise
        """
        if not self.sheet:
            return None

        try:
            # Get all rows from spreadsheet
            all_rows = self.sheet.get_all_values()

            # Skip header row
            if len(all_rows) <= 1:
                return None

            # Extract matching criteria from CLOSE trade
            underlying = trade.get('underlying', '')
            strategy = trade.get('strategy', '')
            expiration = trade.get('expiration', '')
            strikes = self._parse_strikes(trade.get('strikes', ''), strategy)

            # Normalize expiration date format (remove leading zeros for comparison)
            # Convert "05/29/2026" to "5/29/2026"
            def normalize_date(date_str):
                if not date_str:
                    return ''
                try:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        month = str(int(parts[0]))  # Remove leading zero
                        day = str(int(parts[1]))    # Remove leading zero
                        year = parts[2]
                        return f"{month}/{day}/{year}"
                except:
                    pass
                return date_str

            expiration_normalized = normalize_date(expiration)

            # Search from bottom up (most recent trades first)
            for i in range(len(all_rows) - 1, 0, -1):
                row = all_rows[i]

                # Skip if not enough columns
                if len(row) < 8:
                    continue

                # Column indices: 2=Underlying, 3=Strategy, 4=Status, 5=Expiration, 6=Short Strike, 7=Long Strike
                row_underlying = row[2]
                row_strategy = row[3]
                row_status = row[4]
                row_expiration = row[5]
                row_short_strike = row[6]
                row_long_strike = row[7]

                # Normalize row expiration for comparison
                row_expiration_normalized = normalize_date(row_expiration)

                # Match criteria: same underlying, strategy, expiration, strikes, and status is "Open"
                if (row_underlying == underlying and
                    row_strategy == strategy and
                    row_status == 'Open' and
                    row_expiration_normalized == expiration_normalized and
                    row_short_strike == strikes['short'] and
                    row_long_strike == strikes['long']):

                    return i + 1  # Return 1-indexed row number

            return None

        except Exception as e:
            print(f"✗ Error finding open trade: {e}")
            import traceback
            traceback.print_exc()
            return None

    def update_close_trade(self, row_num: int, trade: Dict) -> bool:
        """
        Update existing OPEN row with CLOSE information

        Args:
            row_num: Row number to update (1-indexed)
            trade: CLOSE trade data

        Returns:
            bool: True if successful
        """
        if not self.sheet:
            return False

        try:
            # Get existing row
            existing_row = self.sheet.row_values(row_num)

            # Extract data from CLOSE trade
            closing_date = trade.get('trade_date', '')
            close_net_price = trade.get('net_price', 0)
            close_fees = trade.get('fees', 0)

            # Parse existing data
            open_net_price_str = existing_row[10].replace('$', '').replace(',', '').replace('(', '-').replace(')', '') if len(existing_row) > 10 and existing_row[10] else '0'
            open_net_price = float(open_net_price_str)

            existing_fees_str = existing_row[9].replace('$', '').replace(',', '') if len(existing_row) > 9 and existing_row[9] else '0'
            existing_fees = float(existing_fees_str)

            contracts_str = existing_row[12] if len(existing_row) > 12 and existing_row[12] else '1'
            contracts = float(contracts_str)

            # Calculate cumulative fees
            total_fees = existing_fees + close_fees

            # Calculate P&L: Column K + Column L
            # K and L are already total values for all contracts
            total_pnl = open_net_price + close_net_price

            # Calculate ROC (return on capital)
            # For spreads: capital at risk = width * contracts * 100
            # For CSP: capital at risk = strike * contracts * 100
            # ROC = P&L / capital at risk
            strategy = existing_row[3] if len(existing_row) > 3 else ''
            short_strike_str = existing_row[6].replace('$', '').replace(',', '') if len(existing_row) > 6 and existing_row[6] else '0'
            long_strike_str = existing_row[7].replace('$', '').replace(',', '') if len(existing_row) > 7 and existing_row[7] else '0'

            short_strike = float(short_strike_str) if short_strike_str else 0
            long_strike = float(long_strike_str) if long_strike_str else 0

            if 'Spread' in strategy and short_strike and long_strike:
                width = abs(short_strike - long_strike)
                capital_at_risk = width * contracts * 100
            elif 'CSP' in strategy and short_strike:
                capital_at_risk = short_strike * contracts * 100
            else:
                capital_at_risk = 0

            roc = (total_pnl / capital_at_risk * 100) if capital_at_risk > 0 else 0

            # Update cells (1-indexed columns)
            updates = [
                {'range': f'B{row_num}', 'values': [[closing_date]]},  # Closing Date
                {'range': f'E{row_num}', 'values': [['Closed']]},  # Status
                {'range': f'J{row_num}', 'values': [[f'${total_fees:.2f}']]},  # Fees
                {'range': f'L{row_num}', 'values': [[f'${close_net_price:.2f}']]},  # Closing Net Price
                {'range': f'N{row_num}', 'values': [[f'${total_pnl:.2f}']]},  # Total PnL
                {'range': f'O{row_num}', 'values': [[f'{roc:.2f}%']]},  # ROC
            ]

            self.sheet.batch_update(updates)

            # Highlight updated row with light green background
            try:
                self.sheet.format(f'A{row_num}:P{row_num}', {
                    'backgroundColor': {
                        'red': 0.85,
                        'green': 0.95,
                        'blue': 0.85
                    }
                })
            except:
                pass  # Ignore formatting errors

            print(f"✓ Updated {trade.get('underlying')} {strategy} (row {row_num})")
            return True

        except Exception as e:
            print(f"✗ Failed to update row {row_num}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def append_trade(self, trade: Dict) -> bool:
        """
        Append a single trade to the spreadsheet, or update existing OPEN row if CLOSE

        Args:
            trade: Processed trade dictionary

        Returns:
            bool: True if successful
        """
        if not self.sheet:
            print("✗ Not connected to spreadsheet")
            return False

        try:
            action = trade.get('action', '')
            strategy = trade.get('strategy', trade.get('new_strategy', ''))

            # Check for Unknown strategy - log to errors
            if strategy == 'Unknown':
                self.log_error(trade, 'Unknown strategy - could not classify')
                print(f"✗ Unknown strategy for {trade.get('underlying')} - logged to Import Errors")
                return False

            # For CLOSE trades, try to find and update existing OPEN row
            if action == 'CLOSE':
                row_num = self.find_open_trade(trade)
                if row_num:
                    return self.update_close_trade(row_num, trade)
                else:
                    # No matching OPEN found - log to error sheet instead
                    self.log_error(trade, 'No matching OPEN found')
                    print(f"✗ No matching OPEN for {trade.get('underlying')} {strategy} - logged to Import Errors")
                    return False

            # For OPEN trades, append new row
            row = self.format_trade_row(trade)
            self.sheet.append_row(row)

            print(f"✓ Logged {action} {trade.get('underlying')} {strategy}")
            return True

        except Exception as e:
            # Log any processing errors to Import Errors sheet
            error_msg = f"Processing error: {str(e)}"
            self.log_error(trade, error_msg)
            print(f"✗ Failed to append trade: {e} - logged to Import Errors")
            import traceback
            traceback.print_exc()
            return False

    def log_error(self, trade: Dict, error_msg: str):
        """
        Log a trade error to the Import Errors sheet

        Args:
            trade: Trade that failed to import
            error_msg: Error message
        """
        if not self.error_sheet:
            return

        try:
            from datetime import datetime
            error_row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
                trade.get('underlying', ''),
                trade.get('strategy', ''),
                trade.get('expiration', ''),
                trade.get('strikes', ''),
                trade.get('action', ''),
                error_msg,
                f"Date: {trade.get('trade_date', '')}, Qty: {trade.get('quantity', '')}"
            ]
            self.error_sheet.append_row(error_row)
        except Exception as e:
            print(f"⚠ Failed to log error: {e}")
            import traceback
            traceback.print_exc()

    def append_trades(self, trades: List[Dict]) -> int:
        """
        Append multiple trades to the spreadsheet

        Args:
            trades: List of processed trade dictionaries

        Returns:
            Number of trades successfully logged
        """
        # Sort trades: OPENs before CLOSEs, then by date
        # This ensures same-day open/close pairs can match
        def sort_key(trade):
            action = trade.get('action', '')
            date = trade.get('trade_date', '')
            # OPEN=0, ROLL=1, CLOSE=2 for sorting
            action_priority = {'OPEN': 0, 'ROLL': 1, 'CLOSE': 2}.get(action, 3)
            return (date, action_priority)

        sorted_trades = sorted(trades, key=sort_key)

        count = 0
        for trade in sorted_trades:
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

    transactions = client.get_transactions(start_date='2026-05-19', end_date='2026-05-19')

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
