"""
Spreadsheet Logger
Writes processed trades to Google Sheets trading log
"""
from typing import List, Dict
from datetime import datetime
from zoneinfo import ZoneInfo
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
        self.spreadsheet = None
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
            self.spreadsheet = spreadsheet

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
            except gspread.exceptions.WorksheetNotFound:
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

    def _parse_date(self, date_str: str):
        """
        Keep date string as-is for Google Sheets (will be recognized as date by Sheets)

        Args:
            date_str: Date string in format "6/2/2026" or "06/02/2026"

        Returns:
            Date string (Google Sheets will auto-detect and format as date)
        """
        # Just return the string as-is - Google Sheets will recognize "6/2/2026" as a date
        # when using value_input_option='USER_ENTERED'
        return date_str if date_str else ''

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
            opening_date = self._parse_date(trade.get('trade_date', ''))
            closing_date = ''
            status = 'Open'
            net_price = trade.get('net_price', 0)

            # Parse strikes
            strikes_str = trade.get('strikes', '')
            strikes = self._parse_strikes(strikes_str, strategy)

            # For IC (Iron Condor), put strikes in notes and leave strike columns blank
            if strategy == 'IC':
                notes = f"Strikes: {strikes_str}"
                short_strike = ''
                long_strike = ''
            else:
                notes = ''
                short_strike = strikes['short']
                long_strike = strikes['long']

            row = [
                opening_date,           # Opening Date (datetime object)
                closing_date,           # Closing Date (blank for opens)
                underlying,             # Underlying
                strategy,               # Strategy Type
                status,                 # Status
                self._parse_date(expiration),  # Expiration (datetime object)
                short_strike,           # Short/CSP/CC Strike
                long_strike,            # Long Strike
                '',                     # Delta (blank for now)
                fees,                   # Fees (number)
                net_price,              # Opening Net Price (number)
                '',                     # Closing Net Price (blank for opens)
                quantity,               # Contracts (number)
                '',                     # Total PnL (blank for opens)
                notes                   # Notes/Setup
            ]

        elif action == 'CLOSE':
            # Closing transaction - log as separate row for now
            # TODO: Could enhance to find and update matching open row
            opening_date = ''
            closing_date = self._parse_date(trade.get('trade_date', ''))
            status = 'Closed'
            net_price = trade.get('net_price', 0)

            strikes_str = trade.get('strikes', '')
            strikes = self._parse_strikes(strikes_str, strategy)

            # For IC (Iron Condor), put strikes in notes and leave strike columns blank
            if strategy == 'IC':
                notes = f"Strikes: {strikes_str}"
                short_strike = ''
                long_strike = ''
            else:
                notes = ''
                short_strike = strikes['short']
                long_strike = strikes['long']

            row = [
                opening_date,           # Opening Date (blank - manual match needed)
                closing_date,           # Closing Date (datetime object)
                underlying,             # Underlying
                strategy,               # Strategy Type
                status,                 # Status
                self._parse_date(expiration),  # Expiration (datetime object)
                short_strike,           # Short/CSP/CC Strike
                long_strike,            # Long Strike
                '',                     # Delta
                fees,                   # Fees (number)
                '',                     # Opening Net Price (blank)
                net_price,              # Closing Net Price (number)
                quantity,               # Contracts (number)
                '',                     # Total PnL (calculate manually)
                notes                   # Notes
            ]

        elif action == 'ROLL':
            # Roll = close old + open new
            # For now, return the new opening position
            # TODO: Could log both the close and the new open
            opening_date = self._parse_date(trade.get('trade_date', ''))
            closing_date = ''
            status = 'Open'
            net_price = trade.get('open_net_price', 0)
            roll_credit = trade.get('roll_credit', 0)

            strikes = self._parse_strikes(trade.get('new_strikes', ''), trade.get('new_strategy', ''))

            row = [
                opening_date,           # Opening Date (datetime object)
                closing_date,
                underlying,
                trade.get('new_strategy', ''),
                status,
                self._parse_date(trade.get('new_expiration', '')),  # Expiration (datetime object)
                strikes['short'],
                strikes['long'],
                '',
                fees,                   # Fees (number)
                net_price,              # Opening Net Price (number)
                '',
                quantity,               # Contracts (number)
                '',
                '',
                f"Roll credit: ${roll_credit:.2f}"  # Keep formatted in notes
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
        matches = self.find_all_open_trades(trade)
        return matches[0] if matches else None

    def find_all_open_trades(self, trade: Dict) -> List[int]:
        """
        Find ALL matching OPEN trade rows in spreadsheet

        Args:
            trade: CLOSE trade to match

        Returns:
            List of row numbers (1-indexed), oldest first
        """
        if not self.sheet:
            return []

        try:
            # Get all rows from spreadsheet
            all_rows = self.sheet.get_all_values()

            # Skip header row
            if len(all_rows) <= 1:
                return []

            # Extract matching criteria from CLOSE trade
            underlying = trade.get('underlying', '')
            strategy = trade.get('strategy', '')
            expiration = trade.get('expiration', '')
            strikes_str = trade.get('strikes', '')
            strikes = self._parse_strikes(strikes_str, strategy)

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

            # Normalize underlying symbol (SPXW -> SPX, RUTW -> RUT)
            def normalize_underlying(symbol):
                if not symbol:
                    return ''
                # SPXW is the weekly SPX, RUTW is the weekly RUT - treat as equivalent
                return symbol.replace('SPXW', 'SPX').replace('RUTW', 'RUT')

            underlying_normalized = normalize_underlying(underlying)

            matching_rows = []

            # Search from top to bottom (oldest first)
            for i in range(1, len(all_rows)):
                row = all_rows[i]

                # Skip if not enough columns
                if len(row) < 8:
                    continue

                # Column indices: 2=Underlying, 3=Strategy, 4=Status, 5=Expiration, 6=Short Strike, 7=Long Strike, 15=Notes
                row_underlying = row[2]
                row_strategy = row[3]
                row_status = row[4]
                row_expiration = row[5]
                row_short_strike = row[6]
                row_long_strike = row[7]
                row_notes = row[15] if len(row) > 15 else ''

                # Normalize row expiration and underlying for comparison
                row_expiration_normalized = normalize_date(row_expiration)
                row_underlying_normalized = normalize_underlying(row_underlying)

                # Match criteria: same underlying, strategy, expiration, strikes, and status is "Open"
                # For IC (Iron Condor), also match on strikes in notes
                strikes_match = False
                if strategy == 'IC':
                    # Compare strikes from notes field
                    if f"Strikes: {strikes_str}" in row_notes:
                        strikes_match = True
                else:
                    # Compare individual strike columns
                    strikes_match = (row_short_strike == strikes['short'] and
                                   row_long_strike == strikes['long'])

                if (row_underlying_normalized == underlying_normalized and
                    row_strategy == strategy and
                    row_status == 'Open' and
                    row_expiration_normalized == expiration_normalized and
                    strikes_match):

                    matching_rows.append(i + 1)  # 1-indexed row number

            return matching_rows

        except Exception as e:
            print(f"✗ Error finding open trades: {e}")
            import traceback
            traceback.print_exc()
            return []

    def find_existing_open(self, trade: Dict) -> int:
        """
        Check if an OPEN trade already exists in the spreadsheet

        Args:
            trade: OPEN trade to check

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

            # Extract matching criteria from OPEN trade
            underlying = trade.get('underlying', '')
            strategy = trade.get('strategy', '')
            expiration = trade.get('expiration', '')
            strikes_str = trade.get('strikes', '')
            strikes = self._parse_strikes(strikes_str, strategy)
            opening_date = trade.get('trade_date', '')
            quantity = trade.get('quantity', 0)

            # Normalize functions (same as find_all_open_trades)
            def normalize_date(date_str):
                if not date_str:
                    return ''
                try:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        month = str(int(parts[0]))
                        day = str(int(parts[1]))
                        year = parts[2]
                        return f"{month}/{day}/{year}"
                except:
                    pass
                return date_str

            def normalize_underlying(symbol):
                if not symbol:
                    return ''
                return symbol.replace('SPXW', 'SPX').replace('RUTW', 'RUT')

            expiration_normalized = normalize_date(expiration)
            opening_date_normalized = normalize_date(opening_date)
            underlying_normalized = normalize_underlying(underlying)

            # Search from bottom up (most recent first)
            for i in range(len(all_rows) - 1, 0, -1):
                row = all_rows[i]

                # Skip if not enough columns
                if len(row) < 13:
                    continue

                # Column indices: 0=Opening Date, 2=Underlying, 3=Strategy, 4=Status, 5=Expiration, 6=Short Strike, 7=Long Strike, 12=Quantity, 15=Notes
                row_opening_date = row[0]
                row_underlying = row[2]
                row_strategy = row[3]
                row_status = row[4]
                row_expiration = row[5]
                row_short_strike = row[6]
                row_long_strike = row[7]
                row_quantity_str = row[12] if len(row) > 12 and row[12] else '0'
                row_quantity = int(float(row_quantity_str))
                row_notes = row[15] if len(row) > 15 else ''

                # Normalize for comparison
                row_expiration_normalized = normalize_date(row_expiration)
                row_opening_date_normalized = normalize_date(row_opening_date)
                row_underlying_normalized = normalize_underlying(row_underlying)

                # Match criteria: same underlying, strategy, expiration, strikes, opening date, and quantity
                strikes_match = False
                if strategy == 'IC':
                    if f"Strikes: {strikes_str}" in row_notes:
                        strikes_match = True
                else:
                    strikes_match = (row_short_strike == strikes['short'] and
                                   row_long_strike == strikes['long'])

                if (row_underlying_normalized == underlying_normalized and
                    row_strategy == strategy and
                    row_expiration_normalized == expiration_normalized and
                    row_opening_date_normalized == opening_date_normalized and
                    row_quantity == quantity and
                    strikes_match):

                    return i + 1  # Return 1-indexed row number

            return None

        except Exception as e:
            print(f"✗ Error checking for existing open: {e}")
            import traceback
            traceback.print_exc()
            return None

    def find_existing_closed(self, trade: Dict) -> int:
        """
        Check if a CLOSE trade already exists in the spreadsheet
        Handles cases where close was split across multiple positions

        Args:
            trade: CLOSE trade to check

        Returns:
            Row number (1-indexed) of first match if found, None otherwise
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
            strikes_str = trade.get('strikes', '')
            strikes = self._parse_strikes(strikes_str, strategy)
            closing_date = trade.get('trade_date', '')
            quantity = trade.get('quantity', 0)

            # Normalize functions
            def normalize_date(date_str):
                if not date_str:
                    return ''
                try:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        month = str(int(parts[0]))
                        day = str(int(parts[1]))
                        year = parts[2]
                        return f"{month}/{day}/{year}"
                except:
                    pass
                return date_str

            def normalize_underlying(symbol):
                if not symbol:
                    return ''
                return symbol.replace('SPXW', 'SPX').replace('RUTW', 'RUT')

            expiration_normalized = normalize_date(expiration)
            closing_date_normalized = normalize_date(closing_date)
            underlying_normalized = normalize_underlying(underlying)

            # Find all matching closed positions
            matching_closed = []
            total_closed_qty = 0

            for i in range(len(all_rows) - 1, 0, -1):
                row = all_rows[i]

                # Skip if not enough columns
                if len(row) < 13:
                    continue

                # Column indices: 1=Closing Date, 2=Underlying, 3=Strategy, 4=Status, 5=Expiration, 6=Short Strike, 7=Long Strike, 12=Quantity, 15=Notes
                row_closing_date = row[1]
                row_underlying = row[2]
                row_strategy = row[3]
                row_status = row[4]
                row_expiration = row[5]
                row_short_strike = row[6]
                row_long_strike = row[7]
                row_quantity_str = row[12] if len(row) > 12 and row[12] else '0'
                row_quantity = int(float(row_quantity_str))
                row_notes = row[15] if len(row) > 15 else ''

                # Only match Closed positions
                if row_status != 'Closed':
                    continue

                # Normalize for comparison
                row_expiration_normalized = normalize_date(row_expiration)
                row_closing_date_normalized = normalize_date(row_closing_date)
                row_underlying_normalized = normalize_underlying(row_underlying)

                # Match criteria: same underlying, strategy, expiration, strikes, and closing date
                strikes_match = False
                if strategy == 'IC':
                    if f"Strikes: {strikes_str}" in row_notes:
                        strikes_match = True
                else:
                    strikes_match = (row_short_strike == strikes['short'] and
                                   row_long_strike == strikes['long'])

                if (row_underlying_normalized == underlying_normalized and
                    row_strategy == strategy and
                    row_expiration_normalized == expiration_normalized and
                    row_closing_date_normalized == closing_date_normalized and
                    strikes_match):

                    matching_closed.append(i + 1)
                    total_closed_qty += row_quantity

            # Return first match if total quantity matches
            if matching_closed and total_closed_qty == quantity:
                return matching_closed[0]

            return None

        except Exception as e:
            print(f"✗ Error checking for existing close: {e}")
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

            # Update cells (1-indexed columns)
            # Parse closing date to datetime object
            closing_date_obj = self._parse_date(closing_date)

            updates = [
                {'range': f'B{row_num}', 'values': [[closing_date_obj]]},  # Closing Date (datetime)
                {'range': f'E{row_num}', 'values': [['Closed']]},  # Status
                {'range': f'J{row_num}', 'values': [[total_fees]]},  # Fees (number)
                {'range': f'L{row_num}', 'values': [[close_net_price]]},  # Closing Net Price (number)
                {'range': f'N{row_num}', 'values': [[total_pnl]]},  # Total PnL (number)
            ]

            self.sheet.batch_update(updates, value_input_option='USER_ENTERED')

            print(f"✓ Updated {trade.get('underlying')} {trade.get('strategy', '')} (row {row_num})")
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

            # For ROLL trades, first close the old position, then open new one
            if action == 'ROLL':
                # If the new leg is already logged, this roll was handled on an
                # earlier run inside the lookback window. Re-running must not
                # re-append it, and must not re-report the old position as
                # missing — it is missing precisely because we already closed it.
                new_position = {
                    'underlying': trade.get('underlying'),
                    'strategy': trade.get('new_strategy', ''),
                    'expiration': trade.get('new_expiration', ''),
                    'strikes': trade.get('new_strikes', ''),
                    'quantity': trade.get('quantity', 0),
                    'trade_date': trade.get('trade_date', '')
                }
                existing_roll = self.find_existing_open(new_position)
                if existing_roll:
                    print(f"⊘ Skipped duplicate ROLL {trade.get('underlying')} "
                          f"{trade.get('new_strategy', '')} (already at row {existing_roll})")
                    self.clear_error(trade)
                    return True

                # Create a pseudo-CLOSE trade for the old position
                old_position = {
                    'underlying': trade.get('underlying'),
                    'strategy': trade.get('old_strategy', ''),
                    'expiration': trade.get('old_expiration', ''),
                    'strikes': trade.get('old_strikes', ''),
                    'quantity': trade.get('quantity', 0),
                    'trade_date': trade.get('trade_date', ''),
                    'net_price': trade.get('close_net_price', 0),
                    'fees': trade.get('fees', 0) / 2  # Split fees between close and open
                }

                # Try to find and close the old position
                row_num = self.find_open_trade(old_position)
                if row_num:
                    # Close the old position
                    if not self.update_close_trade(row_num, old_position):
                        self.log_error(trade, 'Failed to close old position in ROLL')
                        print(f"✗ Failed to close old position for ROLL {trade.get('underlying')} - logged to Import Errors")
                        return False
                else:
                    # No matching old position found - log error but still open new position
                    error_msg = f"ROLL: No matching OPEN found for old position (exp: {trade.get('old_expiration')}, strikes: {trade.get('old_strikes')})"
                    self.log_error(trade, error_msg)
                    print(f"✗ {error_msg}")
                    # Don't return False - still append the new position

                # Now append the new position
                row = self.format_trade_row(trade)
                new_row_num = self._append_row_at_column_a(row)
                self.format_new_row(new_row_num)

                print(f"✓ Logged ROLL {trade.get('underlying')} {trade.get('new_strategy', '')}")

                # Clear any associated import errors
                self.clear_error(trade)

                return True

            # For CLOSE trades, find and update all matching OPEN rows
            if action == 'CLOSE':
                matching_rows = self.find_all_open_trades(trade)

                if not matching_rows:
                    # Check if this position was already closed (to avoid duplicate error logs on re-run)
                    already_closed = self.find_existing_closed(trade)
                    if already_closed:
                        print(f"⊘ Skipped duplicate CLOSE {trade.get('underlying')} {strategy} (already closed at row {already_closed})")
                        # Clear any associated import errors since the trade is already successfully logged
                        self.clear_error(trade)
                        return True  # Return success since it's already closed

                    # No matching OPEN found and not already closed - log to error sheet
                    self.log_error(trade, 'No matching OPEN found')
                    print(f"✗ No matching OPEN for {trade.get('underlying')} {strategy} - logged to Import Errors")
                    return False

                # Calculate total open quantity across all matches
                total_open_qty = 0
                row_quantities = []
                for row_num in matching_rows:
                    existing_row = self.sheet.row_values(row_num)
                    existing_qty_str = existing_row[12] if len(existing_row) > 12 and existing_row[12] else '0'
                    existing_qty = int(float(existing_qty_str))
                    total_open_qty += existing_qty
                    row_quantities.append((row_num, existing_qty))

                close_qty = trade.get('quantity', 0)

                # Handle partial sale: split OPEN row if only one match and close_qty < total_open_qty
                if close_qty < total_open_qty and len(matching_rows) == 1:
                    remaining_qty = total_open_qty - close_qty
                    print(f"⚙ Partial sale detected: splitting {total_open_qty} contracts into ({close_qty} + {remaining_qty})")

                    # Split the single OPEN row into two
                    original_row_num = matching_rows[0]
                    new_rows = self._split_open_row(original_row_num, close_qty, remaining_qty)

                    if new_rows:
                        # Update matching_rows and row_quantities to point to the matching-qty split
                        matching_row_num, remaining_row_num = new_rows
                        matching_rows = [matching_row_num]
                        row_quantities = [(matching_row_num, close_qty)]
                        total_open_qty = close_qty  # Update to match
                        print(f"✓ Split complete: row {matching_row_num} ({close_qty} contracts) + row {remaining_row_num} ({remaining_qty} contracts)")
                    else:
                        self.log_error(trade, 'Failed to split OPEN row for partial sale')
                        return False

                # Verify total quantities match
                if total_open_qty != close_qty:
                    self.log_error(trade, f'Quantity mismatch: Total OPEN={total_open_qty}, CLOSE={close_qty}')
                    print(f"✗ Quantity mismatch for {trade.get('underlying')} {strategy} (Total OPEN={total_open_qty}, CLOSE={close_qty}) - logged to Import Errors")
                    return False

                # Close each matching position with proportional pricing
                total_net_price = trade.get('net_price', 0)
                total_fees = trade.get('fees', 0)

                success_count = 0
                for row_num, row_qty in row_quantities:
                    # Calculate proportional values for this position
                    qty_ratio = row_qty / close_qty
                    proportional_trade = trade.copy()
                    proportional_trade['quantity'] = row_qty
                    proportional_trade['net_price'] = total_net_price * qty_ratio
                    proportional_trade['fees'] = total_fees * qty_ratio

                    if self.update_close_trade(row_num, proportional_trade):
                        success_count += 1

                # Clear any associated import errors if all closes succeeded
                if success_count == len(row_quantities):
                    self.clear_error(trade)

                return success_count == len(row_quantities)

            # For OPEN trades, check for duplicate before appending
            if action == 'OPEN':
                # Check if this OPEN already exists
                existing_open = self.find_existing_open(trade)
                if existing_open:
                    print(f"⊘ Skipped duplicate OPEN {trade.get('underlying')} {strategy} (already at row {existing_open})")
                    # Clear any associated import errors since the trade is already successfully logged
                    self.clear_error(trade)
                    return True  # Return success since it's already logged

            # Append new row
            row = self.format_trade_row(trade)
            new_row_num = self._append_row_at_column_a(row)
            self.format_new_row(new_row_num)

            print(f"✓ Logged {action} {trade.get('underlying')} {strategy}")

            # Clear any associated import errors
            self.clear_error(trade)

            return True

        except Exception as e:
            # Log any processing errors to Import Errors sheet
            error_msg = f"Processing error: {str(e)}"
            self.log_error(trade, error_msg)
            print(f"✗ Failed to append trade: {e} - logged to Import Errors")
            import traceback
            traceback.print_exc()
            return False

    def _append_row_at_column_a(self, row: List[str]) -> int:
        """
        Append a row starting at column A (not at the end of the widest row)

        Args:
            row: List of cell values to append

        Returns:
            Row number where the data was written (1-indexed)
        """
        # Find the last row with data in column A
        all_rows = self.sheet.get_all_values()
        last_data_row = 0
        for i in range(len(all_rows) - 1, -1, -1):
            if i < len(all_rows) and len(all_rows[i]) > 0 and all_rows[i][0].strip():
                last_data_row = i + 1
                break

        # Write to the next row
        target_row = last_data_row + 1

        # Calculate the range (columns A to O for 15 columns, or P for 16)
        num_cols = len(row)
        end_col = chr(ord('A') + num_cols - 1)  # A=0, B=1, ..., O=14, P=15
        range_name = f'A{target_row}:{end_col}{target_row}'

        # Use update with explicit range
        self.sheet.update(values=[row], range_name=range_name, value_input_option='USER_ENTERED')

        return target_row

    def format_new_row(self, row_num: int):
        """
        Apply formatting to a newly appended row to match existing spreadsheet style

        Args:
            row_num: Row number to format (1-indexed)
        """
        try:
            # Apply RIGHT alignment to all columns to match existing rows
            self.sheet.format(f'A{row_num}:P{row_num}', {
                'horizontalAlignment': 'RIGHT',
                'verticalAlignment': 'MIDDLE'
            })

        except Exception as e:
            # Don't fail the whole operation if formatting fails
            pass

    def _split_open_row(self, row_num: int, qty1: int, qty2: int):
        """
        Split an OPEN row into two separate rows with different quantities
        Used for partial sales where only some contracts are closed

        Args:
            row_num: Original row number to split (1-indexed)
            qty1: Quantity for first split (will be matched with CLOSE)
            qty2: Quantity for second split (remains open)

        Returns:
            Tuple of (matching_row_num, remaining_row_num) or None if failed
        """
        try:
            # Get all rows to avoid padding issues with row_values()
            all_rows = self.sheet.get_all_values()

            if row_num < 1 or row_num > len(all_rows):
                print(f"✗ Row {row_num} is out of range (sheet has {len(all_rows)} rows)")
                return None

            # Get the original row (convert to 0-indexed)
            original_row = all_rows[row_num - 1].copy()

            if len(original_row) < 13:
                print(f"✗ Row {row_num} has insufficient columns ({len(original_row)})")
                return None

            # Trim to only the first 15 columns (the actual data columns we use)
            original_row = original_row[:15]

            # Pad to 15 columns if needed
            while len(original_row) < 15:
                original_row.append('')

            # Get original values
            original_qty = int(float(original_row[12])) if original_row[12] else 0
            original_fees_str = original_row[9].replace('$', '').replace(',', '') if original_row[9] else '0'
            original_fees = float(original_fees_str)
            original_price_str = original_row[10].replace('$', '').replace(',', '').replace('(', '-').replace(')', '') if original_row[10] else '0'
            original_price = float(original_price_str)

            # Calculate proportional values
            ratio1 = qty1 / original_qty if original_qty > 0 else 0
            ratio2 = qty2 / original_qty if original_qty > 0 else 0

            # Create two copies of the row with adjusted quantities, prices, and fees
            row1 = original_row.copy()
            row2 = original_row.copy()

            # Update row1 (qty1 contracts)
            row1[12] = qty1  # Quantity
            row1[9] = original_fees * ratio1  # Proportional fees
            row1[10] = original_price * ratio1  # Proportional opening price

            # Update row2 (qty2 contracts)
            row2[12] = qty2  # Quantity
            row2[9] = original_fees * ratio2  # Proportional fees
            row2[10] = original_price * ratio2  # Proportional opening price

            print(f"  Split: ${original_price:.2f} → ${original_price * ratio1:.2f} + ${original_price * ratio2:.2f}, Fees: ${original_fees:.2f} → ${original_fees * ratio1:.2f} + ${original_fees * ratio2:.2f}")

            # Insert both new rows at the original position
            # This avoids potential append_row issues
            self.sheet.insert_row(row1, row_num, value_input_option='USER_ENTERED')
            self.format_new_row(row_num)

            self.sheet.insert_row(row2, row_num + 1, value_input_option='USER_ENTERED')
            self.format_new_row(row_num + 1)

            # Delete the original row (now pushed down by 2)
            self.sheet.delete_rows(row_num + 2)

            # The new rows are at the original position
            return (row_num, row_num + 1)

        except Exception as e:
            print(f"✗ Failed to split row {row_num}: {e}")
            import traceback
            traceback.print_exc()
            return None

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
            # ROLL trades carry new_*/old_* keys rather than the flat ones, so
            # fall back to the new leg. clear_error() resolves these fields the
            # same way — if the two disagree, an error can never be cleared.
            error_row = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
                trade.get('underlying', ''),
                trade.get('strategy') or trade.get('new_strategy', ''),
                trade.get('expiration') or trade.get('new_expiration', ''),
                trade.get('strikes') or trade.get('new_strikes', ''),
                trade.get('action', ''),
                error_msg,
                f"Date: {trade.get('trade_date', '')}, Qty: {trade.get('quantity', '')}"
            ]
            self.error_sheet.append_row(error_row)
        except Exception as e:
            print(f"⚠ Failed to log error: {e}")
            import traceback
            traceback.print_exc()

    def clear_error(self, trade: Dict):
        """
        Clear any matching errors from Import Errors sheet after successful processing

        Args:
            trade: Trade that was successfully processed
        """
        if not self.error_sheet:
            return

        try:
            # Get all error rows
            all_errors = self.error_sheet.get_all_values()

            # Skip header row
            if len(all_errors) <= 1:
                return

            # Normalize functions (same as find_all_open_trades)
            def normalize_date(date_str):
                if not date_str:
                    return ''
                try:
                    parts = date_str.split('/')
                    if len(parts) == 3:
                        month = str(int(parts[0]))
                        day = str(int(parts[1]))
                        year = parts[2]
                        return f"{month}/{day}/{year}"
                except:
                    pass
                return date_str

            def normalize_underlying(symbol):
                if not symbol:
                    return ''
                return symbol.replace('SPXW', 'SPX').replace('RUTW', 'RUT')

            # Extract trade details for matching (must resolve fields exactly
            # as log_error() writes them, including the ROLL new_* fallbacks)
            underlying = normalize_underlying(trade.get('underlying', ''))
            strategy = trade.get('strategy') or trade.get('new_strategy', '')
            expiration = normalize_date(
                trade.get('expiration') or trade.get('new_expiration', ''))
            strikes = trade.get('strikes') or trade.get('new_strikes', '')
            action = trade.get('action', '')

            # Find matching error rows (search from bottom up to avoid index shifts during deletion)
            rows_to_delete = []
            for i in range(len(all_errors) - 1, 0, -1):
                error_row = all_errors[i]

                # Skip if not enough columns
                if len(error_row) < 6:
                    continue

                # Column indices: 1=Underlying, 2=Strategy, 3=Expiration, 4=Strikes, 5=Action
                error_underlying = normalize_underlying(error_row[1])
                error_strategy = error_row[2]
                error_expiration = normalize_date(error_row[3])
                error_strikes = error_row[4]
                error_action = error_row[5]

                # Match on underlying, strategy, expiration, strikes, and action
                if (error_underlying == underlying and
                    error_strategy == strategy and
                    error_expiration == expiration and
                    error_strikes == strikes and
                    error_action == action):

                    rows_to_delete.append(i + 1)  # 1-indexed row number

            # Delete matching rows
            for row_num in rows_to_delete:
                self.error_sheet.delete_rows(row_num)
                print(f"  ✓ Cleared error for {underlying} {strategy} from Import Errors (row {row_num})")

        except Exception as e:
            # Don't fail the whole operation if clearing errors fails
            print(f"⚠ Failed to clear error: {e}")
            import traceback
            traceback.print_exc()

    def _aggregate_close_trades(self, trades: List[Dict]) -> List[Dict]:
        """
        Aggregate multiple CLOSE trades for the same position into one combined trade

        Args:
            trades: List of all trades

        Returns:
            List of trades with CLOSE trades aggregated
        """
        from collections import defaultdict

        # Separate CLOSE trades from others
        close_trades = [t for t in trades if t.get('action') == 'CLOSE']
        other_trades = [t for t in trades if t.get('action') != 'CLOSE']

        if not close_trades:
            return trades

        # Group CLOSE trades by position key
        grouped = defaultdict(list)
        for trade in close_trades:
            # Normalize strikes for comparison
            strikes = self._parse_strikes(trade.get('strikes', ''), trade.get('strategy', ''))
            key = (
                trade.get('underlying', ''),
                trade.get('strategy', ''),
                trade.get('expiration', ''),
                strikes['short'],
                strikes['long'],
                trade.get('trade_date', '')
            )
            grouped[key].append(trade)

        # Aggregate groups with multiple trades
        aggregated_closes = []
        for key, group in grouped.items():
            if len(group) == 1:
                # Single trade, no aggregation needed
                aggregated_closes.append(group[0])
            else:
                # Multiple trades - aggregate them
                print(f"  Aggregating {len(group)} CLOSE trades for {group[0].get('underlying')} {group[0].get('strategy')}")

                # Sum quantities, net_price, and fees
                total_quantity = sum(t.get('quantity', 0) for t in group)
                total_net_price = sum(t.get('net_price', 0) for t in group)
                total_fees = sum(t.get('fees', 0) for t in group)

                # Create aggregated trade using first trade as template
                aggregated = group[0].copy()
                aggregated['quantity'] = total_quantity
                aggregated['net_price'] = total_net_price
                aggregated['fees'] = total_fees
                aggregated_closes.append(aggregated)

        # Return all trades with aggregated closes
        return other_trades + aggregated_closes

    def log_run(self, status: str, date_range: str = '',
                trades_logged=0, details: str = '') -> bool:
        """
        Append a heartbeat row to the 'Sync Log' worksheet so every run
        records itself, regardless of whether push notifications work.

        Args:
            status: 'OK' or 'FAILED'
            date_range: Date window that was synced (e.g. '2026-07-02..2026-07-06')
            trades_logged: Number of trades written this run
            details: Free-text summary / error message

        Returns:
            bool: True if the run-log row was written
        """
        SYNC_LOG_HEADER = ['Timestamp (PT)', 'Date Range', 'Status',
                           'Trades Logged', 'Details']
        try:
            if not self.spreadsheet:
                print("⚠ Cannot write Sync Log: spreadsheet not authenticated")
                return False

            # Get or create the Sync Log worksheet
            try:
                log_sheet = self.spreadsheet.worksheet('Sync Log')
                if log_sheet.row_values(1) != SYNC_LOG_HEADER:
                    log_sheet.clear()
                    log_sheet.append_row(SYNC_LOG_HEADER)
            except gspread.exceptions.WorksheetNotFound:
                log_sheet = self.spreadsheet.add_worksheet(
                    title='Sync Log', rows=1000, cols=5)
                log_sheet.append_row(SYNC_LOG_HEADER)

            timestamp = datetime.now(ZoneInfo('America/Los_Angeles')).strftime(
                '%Y-%m-%d %H:%M:%S')
            log_sheet.append_row(
                [timestamp, date_range, status, str(trades_logged), details],
                value_input_option='USER_ENTERED')
            print(f"✓ Sync Log updated: {status} ({date_range})")
            return True

        except Exception as e:
            print(f"⚠ Failed to write Sync Log: {e}")
            return False

    def append_trades(self, trades: List[Dict]) -> int:
        """
        Append multiple trades to the spreadsheet

        Args:
            trades: List of processed trade dictionaries

        Returns:
            Number of trades successfully logged
        """
        # Aggregate CLOSE trades for the same position
        trades = self._aggregate_close_trades(trades)

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

    # Use trade log spreadsheet ID from config
    if not hasattr(config, 'TRADE_LOG_SPREADSHEET_ID'):
        print("✗ Missing TRADE_LOG_SPREADSHEET_ID in config")
        return

    # Fetch and process transactions
    client = TastytradeClient()
    if not client.authenticate():
        return

    transactions = client.get_transactions(start_date='2026-06-10', end_date='2026-06-10')

    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    # Log to spreadsheet
    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        return

    logger.append_trades(trades)


if __name__ == "__main__":
    test_logger()
