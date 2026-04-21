"""
Tastytrade API Client
Handles authentication and API requests
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import config


class TastytradeClient:
    """Client for interacting with Tastytrade API"""

    def __init__(self):
        self.api_url = config.TASTYTRADE_API_URL
        self.username = config.TASTYTRADE_USERNAME
        self.password = config.TASTYTRADE_PASSWORD
        self.account_number = config.TASTYTRADE_ACCOUNT_NUMBER
        self.session_token = None
        self.session = requests.Session()

    def authenticate(self) -> bool:
        """
        Authenticate with Tastytrade API and obtain session token

        Returns:
            bool: True if authentication successful
        """
        url = f"{self.api_url}/sessions"
        payload = {
            "login": self.username,
            "password": self.password,
            "remember-me": True
        }
        headers = {'Content-Type': 'application/json'}

        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()

            data = response.json()
            self.session_token = data['data']['session-token']

            # Set session token for future requests
            self.session.headers.update({
                'Authorization': self.session_token
            })

            print(f"✓ Authenticated as {self.username}")
            return True

        except requests.exceptions.RequestException as e:
            print(f"✗ Authentication failed: {e}")
            return False

    def get_transactions(self, start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        per_page: int = 100) -> List[Dict]:
        """
        Get account transactions

        Args:
            start_date: Start date (YYYY-MM-DD), defaults to yesterday
            end_date: End date (YYYY-MM-DD), defaults to today
            per_page: Number of results per page

        Returns:
            List of transaction dictionaries
        """
        if not self.session_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        # Default to yesterday if no start date provided
        if not start_date:
            yesterday = datetime.now() - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')

        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        url = f"{self.api_url}/accounts/{self.account_number}/transactions"
        params = {
            'per-page': per_page,
            'page-offset': 0,
            'start-date': start_date,
            'end-date': end_date
        }

        all_transactions = []

        try:
            while True:
                response = self.session.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                transactions = data['data']['items']
                all_transactions.extend(transactions)

                # Check if there are more pages
                pagination = data.get('pagination', {})
                total_pages = pagination.get('total-pages', 1)
                current_page = params['page-offset'] + 1

                if current_page >= total_pages:
                    break

                params['page-offset'] += 1

            print(f"✓ Fetched {len(all_transactions)} transactions from {start_date} to {end_date}")
            return all_transactions

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to fetch transactions: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """
        Get current open positions

        Returns:
            List of position dictionaries with current market values
        """
        if not self.session_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        url = f"{self.api_url}/accounts/{self.account_number}/positions"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            positions = data['data']['items']

            print(f"✓ Fetched {len(positions)} open positions")
            return positions

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to fetch positions: {e}")
            return []

    def get_balances(self) -> Dict:
        """
        Get account balances and equity information

        Returns:
            Dictionary with balance information
        """
        if not self.session_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        url = f"{self.api_url}/accounts/{self.account_number}/balances"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            balances = data['data']

            print(f"✓ Account balance: ${balances.get('cash-balance', 0):,.2f}")
            return balances

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to fetch balances: {e}")
            return {}


# Test function
def test_api():
    """Test API connection and basic endpoints"""
    print("Testing Tastytrade API connection...\n")

    client = TastytradeClient()

    # Test authentication
    if not client.authenticate():
        return

    # Test fetching transactions
    print("\nFetching recent transactions...")
    transactions = client.get_transactions()

    if transactions:
        print(f"\nSample transaction:")
        sample = transactions[0]
        print(f"  ID: {sample.get('id')}")
        print(f"  Type: {sample.get('transaction-type')}")
        print(f"  Date: {sample.get('executed-at')}")
        print(f"  Symbol: {sample.get('symbol', 'N/A')}")
        print(f"  Value: ${sample.get('value', 0)}")

    # Test fetching positions
    print("\nFetching open positions...")
    positions = client.get_positions()

    if positions:
        print(f"\nSample position:")
        sample = positions[0]
        print(f"  Symbol: {sample.get('symbol')}")
        print(f"  Quantity: {sample.get('quantity')}")
        print(f"  Market Value: ${sample.get('market-value', 0)}")

    # Test fetching balances
    print("\nFetching account balances...")
    balances = client.get_balances()


if __name__ == "__main__":
    test_api()
