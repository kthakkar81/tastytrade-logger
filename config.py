"""
Configuration settings for Tastytrade Logger
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Tastytrade API
TASTYTRADE_USERNAME = os.getenv('TASTYTRADE_USERNAME')
TASTYTRADE_PASSWORD = os.getenv('TASTYTRADE_PASSWORD')
TASTYTRADE_ACCOUNT_NUMBER = os.getenv('TASTYTRADE_ACCOUNT_NUMBER')
TASTYTRADE_API_URL = os.getenv('TASTYTRADE_API_URL', 'https://api.tastytrade.com')

# Google Sheets
TRADE_LOG_SPREADSHEET_ID = os.getenv('TRADE_LOG_SPREADSHEET_ID')

# Sheet Names
SHEET_TRADE_LOG = 'Trade Log'
SHEET_OPEN_POSITIONS = 'Open Positions'
SHEET_PENDING_TRADES = 'Pending Trades'

# Transaction Classification
OPTION_STRATEGIES = {
    'bull_put_spread': {
        'legs': 2,
        'types': ['PUT', 'PUT'],
        'actions': ['SELL_TO_OPEN', 'BUY_TO_OPEN'],
        'display_name': 'Bull Put Spread'
    },
    'bear_call_spread': {
        'legs': 2,
        'types': ['CALL', 'CALL'],
        'actions': ['SELL_TO_OPEN', 'BUY_TO_OPEN'],
        'display_name': 'Bear Call Spread'
    },
    'bull_call_spread': {
        'legs': 2,
        'types': ['CALL', 'CALL'],
        'actions': ['BUY_TO_OPEN', 'SELL_TO_OPEN'],
        'display_name': 'Bull Call Spread'
    },
    'bear_put_spread': {
        'legs': 2,
        'types': ['PUT', 'PUT'],
        'actions': ['BUY_TO_OPEN', 'SELL_TO_OPEN'],
        'display_name': 'Bear Put Spread'
    },
    'iron_condor': {
        'legs': 4,
        'types': ['PUT', 'PUT', 'CALL', 'CALL'],
        'display_name': 'Iron Condor'
    },
    'csp': {
        'legs': 1,
        'types': ['PUT'],
        'actions': ['SELL_TO_OPEN'],
        'display_name': 'CSP'
    },
    'covered_call': {
        'legs': 1,
        'types': ['CALL'],
        'actions': ['SELL_TO_OPEN'],
        'display_name': 'Covered Call'
    }
}

# Position ID Settings
POSITION_ID_PREFIX = 'POS'
POSITION_ID_DATE_FORMAT = '%Y%m%d'
