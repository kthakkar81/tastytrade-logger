"""
Unit tests for Tastytrade Logger
Run with: pytest test_tastytrade_logger.py -v
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time

from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor


class TestOAuthClient:
    """Test OAuth authentication and API calls"""

    def test_client_initialization(self):
        """Test client initializes with correct config"""
        with patch('config.TASTYTRADE_CLIENT_ID', '6ff780ff-0c22-4a4a-8326-a83b31d9afe5'):
            with patch('config.TASTYTRADE_CLIENT_SECRET', 'test_secret'):
                with patch('config.TASTYTRADE_REFRESH_TOKEN', 'test_refresh'):
                    client = TastytradeClient()
                    assert client.client_id == '6ff780ff-0c22-4a4a-8326-a83b31d9afe5'
                    assert client.client_secret == 'test_secret'
                    assert client.refresh_token == 'test_refresh'
                    assert client.access_token is None

    @patch('requests.Session.post')
    def test_successful_authentication(self, mock_post):
        """Test successful OAuth token refresh"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'access_token': 'test_access_token',
            'expires_in': 900
        }
        mock_post.return_value = mock_response

        with patch('config.TASTYTRADE_CLIENT_SECRET', 'test_secret'):
            with patch('config.TASTYTRADE_REFRESH_TOKEN', 'test_refresh'):
                client = TastytradeClient()
                result = client.authenticate()

                assert result is True
                assert client.access_token == 'test_access_token'
                assert client.token_expiration > time.time()

    @patch('requests.Session.post')
    def test_failed_authentication(self, mock_post):
        """Test failed authentication handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Invalid credentials"
        mock_post.return_value = mock_response

        with patch('config.TASTYTRADE_CLIENT_SECRET', 'bad_secret'):
            with patch('config.TASTYTRADE_REFRESH_TOKEN', 'bad_refresh'):
                client = TastytradeClient()
                result = client.authenticate()

                assert result is False
                assert client.access_token is None

    def test_token_expiration_check(self):
        """Test token expiration detection"""
        with patch('config.TASTYTRADE_CLIENT_SECRET', 'test_secret'):
            with patch('config.TASTYTRADE_REFRESH_TOKEN', 'test_refresh'):
                client = TastytradeClient()
                client.access_token = 'test_token'

                # Set token to expire in past
                client.token_expiration = time.time() - 100
                assert not client._ensure_authenticated()

                # Set token to expire in future
                client.token_expiration = time.time() + 500
                assert client._ensure_authenticated()

    @patch('requests.Session.get')
    def test_get_transactions(self, mock_get):
        """Test fetching transactions"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'items': [
                    {'id': '123', 'transaction-type': 'Trade'},
                    {'id': '124', 'transaction-type': 'Trade'}
                ]
            },
            'pagination': {'total-pages': 1}
        }
        mock_get.return_value = mock_response

        with patch('config.TASTYTRADE_ACCOUNT_NUMBER', '5WI56413'):
            client = TastytradeClient()
            client.access_token = 'test_token'
            client.token_expiration = time.time() + 500

            transactions = client.get_transactions()

            assert len(transactions) == 2
            assert transactions[0]['id'] == '123'


class TestTransactionProcessor:
    """Test transaction processing and classification"""

    def test_processor_initialization(self):
        """Test processor initializes correctly"""
        processor = TransactionProcessor()
        assert processor.transactions == []
        assert len(processor.grouped_orders) == 0

    def test_load_transactions(self):
        """Test loading and grouping transactions"""
        processor = TransactionProcessor()

        sample_transactions = [
            {
                'id': '1',
                'transaction-type': 'Trade',
                'order-id': 'ORDER_1',
                'action': 'SELL_TO_OPEN'
            },
            {
                'id': '2',
                'transaction-type': 'Trade',
                'order-id': 'ORDER_1',
                'action': 'BUY_TO_OPEN'
            },
            {
                'id': '3',
                'transaction-type': 'Trade',
                'order-id': 'ORDER_2',
                'action': 'SELL_TO_OPEN'
            }
        ]

        processor.load_transactions(sample_transactions)

        assert len(processor.transactions) == 3
        assert len(processor.grouped_orders) == 2
        assert len(processor.grouped_orders['ORDER_1']) == 2
        assert len(processor.grouped_orders['ORDER_2']) == 1

    def test_opening_action_detection(self):
        """Test opening action detection"""
        processor = TransactionProcessor()

        assert processor._is_opening_action({'action': 'SELL_TO_OPEN'}) is True
        assert processor._is_opening_action({'action': 'BUY_TO_OPEN'}) is True
        assert processor._is_opening_action({'action': 'SELL_TO_CLOSE'}) is False
        assert processor._is_opening_action({'action': 'BUY_TO_CLOSE'}) is False

    def test_closing_action_detection(self):
        """Test closing action detection"""
        processor = TransactionProcessor()

        assert processor._is_closing_action({'action': 'SELL_TO_CLOSE'}) is True
        assert processor._is_closing_action({'action': 'BUY_TO_CLOSE'}) is True
        assert processor._is_closing_action({'action': 'SELL_TO_OPEN'}) is False
        assert processor._is_closing_action({'action': 'BUY_TO_OPEN'}) is False

    def test_csp_classification(self):
        """Test CSP strategy classification"""
        processor = TransactionProcessor()

        csp_leg = [{
            'action': 'SELL_TO_OPEN',
            'symbol': 'UBER  260501P00074000'
        }]

        strategy = processor._classify_strategy(csp_leg)
        assert strategy == 'CSP'

    def test_bull_put_spread_classification(self):
        """Test Bull Put Spread classification"""
        processor = TransactionProcessor()

        spread_legs = [
            {
                'action': 'SELL_TO_OPEN',
                'symbol': 'UBER  260501P00074000'
            },
            {
                'action': 'BUY_TO_OPEN',
                'symbol': 'UBER  260501P00070000'
            }
        ]

        strategy = processor._classify_strategy(spread_legs)
        assert strategy == 'Bull Put Spread'

    def test_bear_call_spread_classification(self):
        """Test Bear Call Spread classification"""
        processor = TransactionProcessor()

        spread_legs = [
            {
                'action': 'SELL_TO_OPEN',
                'symbol': 'UBER  260501C00080000'
            },
            {
                'action': 'BUY_TO_OPEN',
                'symbol': 'UBER  260501C00085000'
            }
        ]

        strategy = processor._classify_strategy(spread_legs)
        assert strategy == 'Bear Call Spread'

    def test_net_price_calculation_credit(self):
        """Test net price calculation for credit received"""
        processor = TransactionProcessor()

        legs = [
            {'action': 'SELL_TO_OPEN', 'value': '100.0'},
            {'action': 'BUY_TO_OPEN', 'value': '50.0'}
        ]

        net = processor._calculate_net_price(legs)
        assert net == 50.0  # Credit of $50

    def test_net_price_calculation_debit(self):
        """Test net price calculation for debit paid"""
        processor = TransactionProcessor()

        legs = [
            {'action': 'BUY_TO_OPEN', 'value': '200.0'},
            {'action': 'SELL_TO_OPEN', 'value': '100.0'}
        ]

        net = processor._calculate_net_price(legs)
        assert net == -100.0  # Debit of $100

    def test_fee_calculation(self):
        """Test total fee calculation"""
        processor = TransactionProcessor()

        legs = [
            {
                'commission': '0.50',
                'clearing-fees': '0.10',
                'regulatory-fees': '0.05'
            },
            {
                'commission': '0.50',
                'clearing-fees': '0.10',
                'regulatory-fees': '0.05'
            }
        ]

        total_fees = processor._calculate_fees(legs)
        assert total_fees == 1.30

    def test_underlying_extraction(self):
        """Test underlying symbol extraction"""
        processor = TransactionProcessor()

        leg = {'symbol': 'UBER  260501P00074000'}
        underlying = processor._get_underlying(leg)
        assert underlying == 'UBER'

        leg2 = {'underlying-symbol': 'TSLA'}
        underlying2 = processor._get_underlying(leg2)
        assert underlying2 == 'TSLA'

    def test_quantity_extraction(self):
        """Test quantity extraction"""
        processor = TransactionProcessor()

        legs = [{'quantity': '10'}]
        qty = processor._get_quantity(legs)
        assert qty == 10

        legs2 = [{'quantity': '-5'}]  # Negative for sells
        qty2 = processor._get_quantity(legs2)
        assert qty2 == 5  # Should return absolute value

    def test_trade_date_formatting(self):
        """Test trade date formatting"""
        processor = TransactionProcessor()

        leg = {'executed-at': '2026-04-24T19:34:43.784Z'}
        date = processor._get_trade_date(leg)
        assert date == '04/24/2026'


class TestIntegration:
    """Integration test markers (run separately with live API)"""

    @pytest.mark.integration
    def test_live_api_authentication(self):
        """Test live API authentication - requires valid credentials"""
        client = TastytradeClient()
        result = client.authenticate()
        assert result is True
        assert client.access_token is not None

    @pytest.mark.integration
    def test_live_transaction_fetch(self):
        """Test fetching real transactions - requires valid credentials"""
        client = TastytradeClient()
        client.authenticate()
        transactions = client.get_transactions()
        assert isinstance(transactions, list)

    @pytest.mark.integration
    def test_end_to_end_processing(self):
        """Test complete pipeline from API to processed trades"""
        # Authenticate
        client = TastytradeClient()
        assert client.authenticate() is True

        # Fetch transactions
        transactions = client.get_transactions()
        assert len(transactions) > 0

        # Process transactions
        processor = TransactionProcessor()
        processor.load_transactions(transactions)
        trades = processor.process_orders()

        # Validate results
        assert len(trades) > 0
        assert all('action' in trade for trade in trades)
        assert all('strategy' in trade for trade in trades)
        assert all('net_price' in trade for trade in trades)


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
