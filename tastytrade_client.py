"""
Tastytrade API Client with OAuth 2.0 Authentication
Handles token refresh automatically
"""
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import config


class TastytradeClient:
    """Client for interacting with Tastytrade API using OAuth 2.0"""

    def __init__(self):
        self.api_url = config.TASTYTRADE_API_URL
        self.client_id = config.TASTYTRADE_CLIENT_ID
        self.client_secret = config.TASTYTRADE_CLIENT_SECRET
        self.refresh_token = config.TASTYTRADE_REFRESH_TOKEN
        self.account_number = config.TASTYTRADE_ACCOUNT_NUMBER
        self.session = requests.Session()
        self.access_token = None
        self.token_expiration = 0

    def authenticate(self) -> bool:
        """
        Authenticate with Tastytrade API using OAuth 2.0

        Returns:
            bool: True if authentication successful
        """
        try:
            if not self.client_secret or not self.refresh_token:
                print("✗ Missing OAuth credentials. Please set TASTYTRADE_CLIENT_SECRET and TASTYTRADE_REFRESH_TOKEN")
                return False

            return self._refresh_access_token()

        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _refresh_access_token(self) -> bool:
        """
        Get or refresh the access token using refresh token

        Returns:
            bool: True if token refresh successful
        """
        try:
            url = f"{self.api_url}/oauth/token"
            payload = {
                "grant_type": "refresh_token",
                "client_secret": self.client_secret,
                "refresh_token": self.refresh_token
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            response = self.session.post(url, json=payload, headers=headers)

            if response.status_code in [200, 201]:
                data = response.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 900)  # Default 15 minutes

                # Set expiration time with 60 second buffer
                self.token_expiration = time.time() + expires_in - 60

                # Update session headers with new access token
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })

                print(f"✓ OAuth authenticated (token expires in {expires_in}s)")
                return True
            else:
                print(f"✗ Token refresh failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"✗ Token refresh failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid access token, refreshing if needed

        Returns:
            bool: True if authenticated
        """
        # Check if token needs refresh (within 60 seconds of expiration)
        if time.time() >= self.token_expiration:
            print("Token expired, refreshing...")
            return self._refresh_access_token()

        return True

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
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        # Ensure token is valid
        if not self._ensure_authenticated():
            raise Exception("Failed to refresh access token")

        # Default to yesterday if no start date provided
        if not start_date:
            yesterday = datetime.now() - timedelta(days=1)
            start_date = yesterday.strftime('%Y-%m-%d')

        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        try:
            url = f"{self.api_url}/accounts/{self.account_number}/transactions"
            params = {
                'per-page': per_page,
                'page-offset': 0,
                'start-date': start_date,
                'end-date': end_date
            }

            all_transactions = []

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

        except Exception as e:
            print(f"✗ Failed to fetch transactions: {e}")
            return []

    def get_positions(self) -> List[Dict]:
        """
        Get current open positions with market values

        Returns:
            List of position dictionaries with current market values
        """
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        # Ensure token is valid
        if not self._ensure_authenticated():
            raise Exception("Failed to refresh access token")

        try:
            url = f"{self.api_url}/accounts/{self.account_number}/positions"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            positions = data['data']['items']

            print(f"✓ Fetched {len(positions)} open positions")
            return positions

        except Exception as e:
            print(f"✗ Failed to fetch positions: {e}")
            return []

    def get_balances(self) -> Dict:
        """
        Get account balances and equity information

        Returns:
            Dictionary with balance information
        """
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        # Ensure token is valid
        if not self._ensure_authenticated():
            raise Exception("Failed to refresh access token")

        try:
            url = f"{self.api_url}/accounts/{self.account_number}/balances"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            balances = data['data']

            cash_balance = float(balances.get('cash-balance', 0))
            print(f"✓ Account balance: ${cash_balance:,.2f}")
            return balances

        except Exception as e:
            print(f"✗ Failed to fetch balances: {e}")
            return {}

    def get_customer_accounts(self) -> List[Dict]:
        """
        Get all accounts for the authenticated user

        Returns:
            List of account dictionaries
        """
        if not self.access_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        # Ensure token is valid
        if not self._ensure_authenticated():
            raise Exception("Failed to refresh access token")

        try:
            url = f"{self.api_url}/customers/me/accounts"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            accounts = data['data']['items']

            print(f"✓ Found {len(accounts)} account(s):")
            for acc in accounts:
                print(f"  - Account: {acc.get('account', {}).get('account-number')} ({acc.get('account', {}).get('nickname', 'No nickname')})")

            return accounts

        except Exception as e:
            print(f"✗ Failed to fetch accounts: {e}")
            import traceback
            traceback.print_exc()
            return []


# Test function
def test_api():
    """Test API connection and basic endpoints"""
    print("Testing Tastytrade API connection with OAuth...\n")

    client = TastytradeClient()

    # Test authentication
    if not client.authenticate():
        return

    # First, get accounts to find correct account number
    print("\nFetching customer accounts...")
    accounts = client.get_customer_accounts()

    if not accounts:
        print("✗ No accounts found")
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
