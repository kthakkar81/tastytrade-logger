"""
Tastytrade API Client (custom implementation with device challenge support)
Handles authentication including device challenges
"""
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import config


class TastytradeClient:
    """Client for interacting with Tastytrade API with device challenge support"""

    def __init__(self):
        self.api_url = config.TASTYTRADE_API_URL
        self.username = config.TASTYTRADE_USERNAME
        self.password = config.TASTYTRADE_PASSWORD
        self.account_number = config.TASTYTRADE_ACCOUNT_NUMBER
        self.session = requests.Session()
        self.session_token = None
        self.remember_token = None

    def authenticate(self) -> bool:
        """
        Authenticate with Tastytrade API handling device challenges

        Returns:
            bool: True if authentication successful
        """
        try:
            url = f"{self.api_url}/sessions"
            payload = {
                "login": self.username,
                "password": self.password,
                "remember-me": True
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            print(f"Attempting authentication...")
            response = self.session.post(url, json=payload, headers=headers)

            # Handle device challenge
            if response.status_code == 403:
                response_data = response.json()
                error = response_data.get('error', {})

                if error.get('code') == 'device_challenge_required':
                    print("Device challenge required, handling...")
                    return self._handle_device_challenge(error)

            # Normal authentication success
            if response.status_code in [200, 201]:
                data = response.json()
                self.session_token = data['data']['session-token']
                self.remember_token = data['data'].get('remember-token')

                # Set session token for future requests
                self.session.headers.update({
                    'Authorization': self.session_token
                })

                print(f"✓ Authenticated as {self.username}")
                return True

            # Other errors
            print(f"✗ Authentication failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        except Exception as e:
            print(f"✗ Authentication failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _handle_device_challenge(self, error: Dict) -> bool:
        """
        Handle device authentication challenge

        Args:
            error: Error response containing challenge information

        Returns:
            bool: True if challenge handled successfully
        """
        try:
            redirect = error.get('redirect', {})
            challenge_url = redirect.get('url')

            if not challenge_url:
                print("✗ No challenge URL provided")
                return False

            # Request device challenge
            url = f"{self.api_url}{challenge_url}"
            payload = {
                "login": self.username,
                "password": self.password
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            print(f"Requesting device challenge at: {url}")
            response = self.session.post(url, json=payload, headers=headers)

            if response.status_code in [200, 201]:
                data = response.json()
                challenge_token = data.get('data', {}).get('challenge-token')

                if challenge_token:
                    print("✓ Device challenge token received")
                    print(f"Challenge token: {challenge_token}")

                    # Now retry authentication with challenge token
                    return self._authenticate_with_challenge(challenge_token)
                else:
                    print("✗ No challenge token in response")
                    print(f"Response: {response.text}")
                    return False

            print(f"✗ Device challenge request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        except Exception as e:
            print(f"✗ Device challenge handling failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _authenticate_with_challenge(self, challenge_token: str) -> bool:
        """
        Complete authentication with device challenge token

        Args:
            challenge_token: Device challenge token

        Returns:
            bool: True if authentication successful
        """
        try:
            url = f"{self.api_url}/sessions"
            payload = {
                "login": self.username,
                "password": self.password,
                "remember-me": True
            }
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Tastyworks-Challenge-Token': challenge_token
            }

            print("Completing authentication with challenge token...")
            response = self.session.post(url, json=payload, headers=headers)

            if response.status_code in [200, 201]:
                data = response.json()
                self.session_token = data['data']['session-token']
                self.remember_token = data['data'].get('remember-token')

                # Set session token for future requests
                self.session.headers.update({
                    'Authorization': self.session_token
                })

                print(f"✓ Authenticated successfully with device challenge")

                # Save remember token for future use
                if self.remember_token:
                    print(f"✓ Remember token received (save this for future sessions)")
                    print(f"Remember token: {self.remember_token}")

                return True

            print(f"✗ Authentication with challenge failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

        except Exception as e:
            print(f"✗ Authentication with challenge failed: {e}")
            import traceback
            traceback.print_exc()
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
        if not self.session_token:
            raise Exception("Not authenticated. Call authenticate() first.")

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
        if not self.session_token:
            raise Exception("Not authenticated. Call authenticate() first.")

        try:
            url = f"{self.api_url}/accounts/{self.account_number}/balances"
            response = self.session.get(url)
            response.raise_for_status()

            data = response.json()
            balances = data['data']

            cash_balance = balances.get('cash-balance', 0)
            print(f"✓ Account balance: ${cash_balance:,.2f}")
            return balances

        except Exception as e:
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
