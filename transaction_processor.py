"""
Transaction Processor
Parses and classifies Tastytrade transactions into tradeable strategies
"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from collections import defaultdict
import config


class TransactionProcessor:
    """Process and classify option transactions"""

    def __init__(self):
        self.transactions = []
        self.grouped_orders = defaultdict(list)

    def load_transactions(self, transactions: List[Dict]):
        """
        Load transactions from API response

        Args:
            transactions: List of transaction dicts from Tastytrade API
        """
        self.transactions = transactions
        self._group_by_order()

    def _group_by_order(self):
        """Group transactions by order ID and consolidate multiple fills"""
        for txn in self.transactions:
            # Only process Trade type transactions
            if txn.get('transaction-type') != 'Trade':
                continue

            order_id = txn.get('order-id')
            if order_id:
                self.grouped_orders[order_id].append(txn)

        # Consolidate multiple fills of the same leg within each order
        for order_id in self.grouped_orders:
            self.grouped_orders[order_id] = self._consolidate_legs(self.grouped_orders[order_id])

        print(f"✓ Grouped {len(self.transactions)} transactions into {len(self.grouped_orders)} orders")

    def _consolidate_legs(self, legs: List[Dict]) -> List[Dict]:
        """
        Consolidate multiple fills of the same leg (same symbol + action)

        Args:
            legs: List of transaction legs for a single order

        Returns:
            Consolidated list of unique legs with summed quantities and values
        """
        consolidated = {}

        for leg in legs:
            symbol = leg.get('symbol', '')
            action = leg.get('action', '')
            key = (symbol, action)

            if key in consolidated:
                # Sum quantities and values for multiple fills
                existing = consolidated[key]
                existing['quantity'] = str(float(existing.get('quantity', 0)) + float(leg.get('quantity', 0)))
                existing['value'] = str(float(existing.get('value', 0)) + float(leg.get('value', 0)))
                existing['net-value'] = str(float(existing.get('net-value', 0)) + float(leg.get('net-value', 0)))
                existing['commission'] = str(float(existing.get('commission', 0)) + float(leg.get('commission', 0)))
                existing['clearing-fees'] = str(float(existing.get('clearing-fees', 0)) + float(leg.get('clearing-fees', 0)))
                existing['regulatory-fees'] = str(float(existing.get('regulatory-fees', 0)) + float(leg.get('regulatory-fees', 0)))
            else:
                # First occurrence of this leg
                consolidated[key] = leg.copy()

        return list(consolidated.values())

    def process_orders(self) -> List[Dict]:
        """
        Process all orders and classify strategies

        Returns:
            List of processed trade dictionaries
        """
        processed_trades = []

        for order_id, legs in self.grouped_orders.items():
            trade = self._process_single_order(order_id, legs)
            if trade:
                processed_trades.append(trade)

        print(f"✓ Processed {len(processed_trades)} trades")
        return processed_trades

    def _process_single_order(self, order_id: str, legs: List[Dict]) -> Optional[Dict]:
        """
        Process a single order and its legs

        Args:
            order_id: Order identifier
            legs: List of transaction legs for this order

        Returns:
            Processed trade dictionary or None
        """
        if not legs:
            return None

        # Separate opening and closing legs
        opening_legs = [leg for leg in legs if self._is_opening_action(leg)]
        closing_legs = [leg for leg in legs if self._is_closing_action(leg)]

        # Determine trade action type
        if opening_legs and closing_legs:
            return self._process_roll(order_id, opening_legs, closing_legs)
        elif opening_legs:
            return self._process_open(order_id, opening_legs)
        elif closing_legs:
            return self._process_close(order_id, closing_legs)

        return None

    def _is_opening_action(self, leg: Dict) -> bool:
        """Check if transaction is an opening action"""
        action = leg.get('action', '').upper()
        return 'OPEN' in action and 'CLOSE' not in action

    def _is_closing_action(self, leg: Dict) -> bool:
        """Check if transaction is a closing action"""
        action = leg.get('action', '').upper()
        return 'CLOSE' in action

    def _process_open(self, order_id: str, legs: List[Dict]) -> Dict:
        """Process opening transaction(s)"""
        return {
            'action': 'OPEN',
            'order_id': order_id,
            'legs': legs,
            'underlying': self._get_underlying(legs[0]),
            'strategy': self._classify_strategy(legs),
            'trade_date': self._get_trade_date(legs[0]),
            'expiration': self._get_expiration(legs[0]),
            'strikes': self._get_strikes(legs),
            'quantity': self._get_quantity(legs),
            'net_price': self._calculate_net_price(legs),
            'fees': self._calculate_fees(legs),
            'notes': ''
        }

    def _process_close(self, order_id: str, legs: List[Dict]) -> Dict:
        """Process closing transaction(s)"""
        return {
            'action': 'CLOSE',
            'order_id': order_id,
            'legs': legs,
            'underlying': self._get_underlying(legs[0]),
            'strategy': self._classify_closing_strategy(legs),
            'trade_date': self._get_trade_date(legs[0]),
            'expiration': self._get_expiration(legs[0]),
            'strikes': self._get_strikes(legs),
            'quantity': self._get_quantity(legs),
            'net_price': self._calculate_net_price(legs),
            'fees': self._calculate_fees(legs),
            'notes': ''
        }

    def _process_roll(self, order_id: str, opening_legs: List[Dict],
                     closing_legs: List[Dict]) -> Dict:
        """Process roll transaction (close old + open new in same order)"""
        # Calculate roll credit/debit
        close_net = self._calculate_net_price(closing_legs)
        open_net = self._calculate_net_price(opening_legs)
        roll_credit = open_net + close_net  # Both should have correct signs

        old_strikes = self._get_strikes(closing_legs)
        new_strikes = self._get_strikes(opening_legs)

        return {
            'action': 'ROLL',
            'order_id': order_id,
            'closing_legs': closing_legs,
            'opening_legs': opening_legs,
            'underlying': self._get_underlying(opening_legs[0]),
            'old_strategy': self._classify_closing_strategy(closing_legs),
            'new_strategy': self._classify_strategy(opening_legs),
            'trade_date': self._get_trade_date(opening_legs[0]),
            'old_expiration': self._get_expiration(closing_legs[0]),
            'new_expiration': self._get_expiration(opening_legs[0]),
            'old_strikes': old_strikes,
            'new_strikes': new_strikes,
            'quantity': self._get_quantity(opening_legs),
            'close_net_price': close_net,
            'open_net_price': open_net,
            'roll_credit': roll_credit,
            'fees': self._calculate_fees(closing_legs + opening_legs),
            'notes': f"Rolled {old_strikes} → {new_strikes}. Roll credit: ${roll_credit:.2f}"
        }

    def _get_underlying(self, leg: Dict) -> str:
        """Extract underlying symbol from transaction"""
        symbol = leg.get('underlying-symbol', leg.get('symbol', ''))
        return symbol.split()[0] if symbol else ''

    def _extract_strike_from_symbol(self, symbol: str) -> Optional[float]:
        """
        Extract strike price from option symbol

        Args:
            symbol: Option symbol (e.g., "IBIT  260529C00043500")

        Returns:
            Strike price as float, or None if unable to parse
        """
        if 'P' in symbol or 'C' in symbol:
            for delimiter in ['P', 'C']:
                if delimiter in symbol:
                    parts = symbol.split(delimiter)
                    if len(parts) >= 2:
                        strike_str = parts[-1].strip()
                        try:
                            strike = float(strike_str)
                            # Normalize: OCC format has 3 implied decimals
                            if strike >= 1000:
                                strike = strike / 1000
                            return strike
                        except:
                            pass
        return None

    def _get_trade_date(self, leg: Dict) -> str:
        """Extract and format trade date"""
        executed_at = leg.get('executed-at', '')
        if executed_at:
            dt = datetime.fromisoformat(executed_at.replace('Z', '+00:00'))
            return dt.strftime('%m/%d/%Y')
        return ''

    def _get_expiration(self, leg: Dict) -> str:
        """Extract option expiration date"""
        # Expiration might be in instrument data or symbol
        expires_at = leg.get('expires-at')
        if expires_at:
            dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            return dt.strftime('%m/%d/%Y')

        # Try parsing from symbol (e.g., "COIN  260501P00190000")
        # Format: <UNDERLYING><SPACES><YYMMDD><P/C><STRIKE>
        symbol = leg.get('symbol', '')

        # Find the P or C delimiter and extract 6 digits before it
        for delimiter in ['P', 'C']:
            if delimiter in symbol:
                # Find position of delimiter
                delim_pos = symbol.index(delimiter)
                # Extract 6 characters before it (the date)
                if delim_pos >= 6:
                    date_str = symbol[delim_pos-6:delim_pos].strip()
                    if len(date_str) == 6 and date_str.isdigit():
                        try:
                            dt = datetime.strptime(date_str, '%y%m%d')
                            return dt.strftime('%m/%d/%Y')
                        except:
                            pass
                break

        return ''

    def _get_strikes(self, legs: List[Dict]) -> str:
        """Extract strike prices from legs"""
        strikes = []
        for leg in legs:
            symbol = leg.get('symbol', '')
            action = leg.get('action', '')

            # Parse strike from symbol (e.g., SPXW260424P6970 → $6,970)
            if 'P' in symbol or 'C' in symbol:
                # Find the last P or C and extract number after it
                for delimiter in ['P', 'C']:
                    if delimiter in symbol:
                        parts = symbol.split(delimiter)
                        if len(parts) >= 2:
                            strike_str = parts[-1]
                            try:
                                strike = float(strike_str)
                                opt_type = 'P' if delimiter == 'P' else 'C'

                                # OCC standard: strikes have 3 implied decimal places
                                # e.g., 350000 = $350.00, 6970000 = $6970.00
                                # If strike >= 1000, it needs decimal correction
                                if strike >= 1000:
                                    strike = strike / 1000

                                # Determine if this is short or long
                                if 'SELL' in action.upper():
                                    strikes.append((strike, opt_type, 'SHORT'))
                                else:
                                    strikes.append((strike, opt_type, 'LONG'))
                            except:
                                pass

        if not strikes:
            return ''

        # Format strikes
        if len(strikes) == 1:
            strike, opt_type, _ = strikes[0]
            return f"${strike:,.2f}{opt_type}"

        # For spreads, show short/long
        strikes.sort(key=lambda x: (x[1], -x[0]))  # Sort by type, then strike desc
        formatted = []
        for strike, opt_type, position in strikes:
            formatted.append(f"${strike:,.2f}")

        return '/'.join(formatted)

    def _get_quantity(self, legs: List[Dict]) -> int:
        """Get quantity (use first leg)"""
        if legs:
            qty = legs[0].get('quantity', 0)
            return abs(int(float(qty)))
        return 0

    def _calculate_net_price(self, legs: List[Dict]) -> float:
        """
        Calculate net price (credit/debit) for the trade including fees

        Uses net-value field which includes commission and fees

        Returns:
            Positive for credits received, negative for debits paid
        """
        net = 0.0

        for leg in legs:
            # Use net-value which includes fees (value - commission - fees)
            net_value = float(leg.get('net-value', 0))
            net_value_effect = leg.get('net-value-effect', '').upper()

            # Credit = money received (positive), Debit = money paid (negative)
            if net_value_effect == 'CREDIT':
                net += abs(net_value)
            elif net_value_effect == 'DEBIT':
                net -= abs(net_value)
            else:
                # Fallback: infer from action if effect not specified
                action = leg.get('action', '').upper()
                if 'SELL' in action:
                    net += abs(net_value)
                else:
                    net -= abs(net_value)

        return net

    def _calculate_fees(self, legs: List[Dict]) -> float:
        """Calculate total fees for transaction"""
        total_fees = 0.0

        for leg in legs:
            commission = float(leg.get('commission', 0))
            clearing_fees = float(leg.get('clearing-fees', 0))
            regulatory_fees = float(leg.get('regulatory-fees', 0))

            total_fees += abs(commission) + abs(clearing_fees) + abs(regulatory_fees)

        return total_fees

    def _classify_strategy(self, legs: List[Dict]) -> str:
        """
        Classify option strategy based on legs

        Returns:
            Strategy name (e.g., 'Bull Put Spread', 'CSP', etc.)
        """
        num_legs = len(legs)

        if num_legs == 1:
            leg = legs[0]
            action = leg.get('action', '').upper()
            symbol = leg.get('symbol', '')

            if 'P' in symbol and 'SELL' in action:
                return 'CSP'
            elif 'C' in symbol and 'SELL' in action:
                return 'Covered Call'
            elif 'P' in symbol and 'BUY' in action:
                return 'Long Put'
            elif 'C' in symbol and 'BUY' in action:
                return 'Long Call'

        elif num_legs == 2:
            # Check if both are same type (puts or calls)
            symbols = [leg.get('symbol', '') for leg in legs]
            is_puts = all('P' in sym for sym in symbols)
            is_calls = all('C' in sym for sym in symbols)

            if is_puts:
                # Check which one is sold (short strike)
                actions = [leg.get('action', '').upper() for leg in legs]
                if 'SELL' in actions[0] or 'SELL' in actions[1]:
                    # One sold, one bought = spread
                    # If sold strike > bought strike = Bull Put Spread
                    # Parse strikes to determine
                    sold_idx = 0 if 'SELL' in actions[0] else 1
                    bought_idx = 1 - sold_idx

                    # For now, assume bull put spread (most common)
                    return 'Bull Put Spread'

            elif is_calls:
                actions = [leg.get('action', '').upper() for leg in legs]
                # Check if it's a spread (one buy, one sell)
                has_buy = any('BUY' in a for a in actions)
                has_sell = any('SELL' in a for a in actions)

                if has_buy and has_sell:
                    # Determine Bull Call Spread vs Bear Call Spread by strike positions
                    # Bull Call Spread: Buy lower strike, Sell higher strike (net debit)
                    # Bear Call Spread: Sell lower strike, Buy higher strike (net credit)
                    buy_idx = 0 if 'BUY' in actions[0] else 1
                    sell_idx = 1 - buy_idx

                    # Parse strikes to compare
                    buy_symbol = legs[buy_idx].get('symbol', '')
                    sell_symbol = legs[sell_idx].get('symbol', '')

                    # Extract strikes (rough comparison)
                    buy_strike = self._extract_strike_from_symbol(buy_symbol)
                    sell_strike = self._extract_strike_from_symbol(sell_symbol)

                    if buy_strike and sell_strike:
                        if buy_strike < sell_strike:
                            return 'Bull Call Spread'
                        else:
                            return 'Bear Call Spread'

                    # Fallback: assume bear call spread (selling premium)
                    return 'Bear Call Spread'

        elif num_legs == 4:
            # Likely Iron Condor
            symbols = [leg.get('symbol', '') for leg in legs]
            num_puts = sum(1 for sym in symbols if 'P' in sym)
            num_calls = sum(1 for sym in symbols if 'C' in sym)

            if num_puts == 2 and num_calls == 2:
                return 'Iron Condor'

        return 'Unknown'

    def _classify_closing_strategy(self, legs: List[Dict]) -> str:
        """
        Classify the original strategy from closing legs

        For closing transactions, actions are inverted:
        - Buy to Close = was originally Sell to Open (short)
        - Sell to Close = was originally Buy to Open (long)

        Returns:
            Strategy name based on the original opening position
        """
        num_legs = len(legs)

        if num_legs == 1:
            leg = legs[0]
            action = leg.get('action', '').upper()
            symbol = leg.get('symbol', '')

            # Invert the action to determine original strategy
            if 'P' in symbol and 'BUY' in action and 'CLOSE' in action:
                # Buy to Close a Put = originally Sell to Open (CSP)
                return 'CSP'
            elif 'C' in symbol and 'BUY' in action and 'CLOSE' in action:
                # Buy to Close a Call = originally Sell to Open (Covered Call)
                return 'Covered Call'
            elif 'P' in symbol and 'SELL' in action and 'CLOSE' in action:
                # Sell to Close a Put = originally Buy to Open (Long Put)
                return 'Long Put'
            elif 'C' in symbol and 'SELL' in action and 'CLOSE' in action:
                # Sell to Close a Call = originally Buy to Open (Long Call)
                return 'Long Call'

        elif num_legs == 2:
            # Check if both are same type (puts or calls)
            symbols = [leg.get('symbol', '') for leg in legs]
            is_puts = all('P' in sym for sym in symbols)
            is_calls = all('C' in sym for sym in symbols)

            if is_puts:
                # Check which one was closed with Buy to Close (was originally short)
                actions = [leg.get('action', '').upper() for leg in legs]
                if 'BUY' in actions[0] or 'BUY' in actions[1]:
                    # One Buy to Close (was sold), one Sell to Close (was bought) = spread
                    return 'Bull Put Spread'

            elif is_calls:
                actions = [leg.get('action', '').upper() for leg in legs]
                # For closing: Buy to Close = was sold, Sell to Close = was bought
                has_buy = any('BUY' in a for a in actions)
                has_sell = any('SELL' in a for a in actions)

                if has_buy and has_sell:
                    # Determine which spread by strike positions
                    buy_idx = 0 if 'BUY' in actions[0] else 1
                    sell_idx = 1 - buy_idx

                    buy_symbol = legs[buy_idx].get('symbol', '')
                    sell_symbol = legs[sell_idx].get('symbol', '')

                    buy_strike = self._extract_strike_from_symbol(buy_symbol)
                    sell_strike = self._extract_strike_from_symbol(sell_symbol)

                    # Invert: Buy to Close means it was originally sold
                    # If we're buying to close the higher strike = Bear Call Spread
                    # If we're buying to close the lower strike = Bull Call Spread
                    if buy_strike and sell_strike:
                        if buy_strike > sell_strike:
                            # Closing: Buy higher, Sell lower = was originally Sell higher, Buy lower = Bear Call
                            return 'Bear Call Spread'
                        else:
                            # Closing: Buy lower, Sell higher = was originally Sell lower, Buy higher = Bull Call
                            return 'Bull Call Spread'

                    return 'Bear Call Spread'

        elif num_legs == 4:
            # Likely Iron Condor
            symbols = [leg.get('symbol', '') for leg in legs]
            num_puts = sum(1 for sym in symbols if 'P' in sym)
            num_calls = sum(1 for sym in symbols if 'C' in sym)

            if num_puts == 2 and num_calls == 2:
                return 'Iron Condor'

        return 'Unknown'


# Test function
def test_processor():
    """Test transaction processing"""
    from tastytrade_client import TastytradeClient

    print("Testing Transaction Processor...\n")

    # Fetch transactions
    client = TastytradeClient()
    if not client.authenticate():
        return

    transactions = client.get_transactions()

    # Process
    processor = TransactionProcessor()
    processor.load_transactions(transactions)
    trades = processor.process_orders()

    # Display sample
    if trades:
        print("\nSample processed trade:")
        trade = trades[0]
        print(f"  Action: {trade['action']}")
        print(f"  Underlying: {trade['underlying']}")
        print(f"  Strategy: {trade['strategy']}")
        print(f"  Strikes: {trade['strikes']}")
        print(f"  Net Price: ${trade['net_price']:.2f}")
        print(f"  Fees: ${trade['fees']:.2f}")


if __name__ == "__main__":
    test_processor()
