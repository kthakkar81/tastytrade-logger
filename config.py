"""
Configuration settings for Tastytrade Logger
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Tastytrade API - OAuth
TASTYTRADE_CLIENT_ID = os.getenv('TASTYTRADE_CLIENT_ID')
TASTYTRADE_CLIENT_SECRET = os.getenv('TASTYTRADE_CLIENT_SECRET')
TASTYTRADE_REFRESH_TOKEN = os.getenv('TASTYTRADE_REFRESH_TOKEN')
TASTYTRADE_ACCOUNT_NUMBER = os.getenv('TASTYTRADE_ACCOUNT_NUMBER')
TASTYTRADE_API_URL = os.getenv('TASTYTRADE_API_URL', 'https://api.tastytrade.com')

# Google Sheets
TRADE_LOG_SPREADSHEET_ID = os.getenv('TRADE_LOG_SPREADSHEET_ID', '1plKfGr2mLUBt_-sgGMu42v5tImUozqEGSYokhQbeJbI')
TEST_SPREADSHEET_ID = os.getenv('TEST_SPREADSHEET_ID', '1dykZLMLgXwVU3PXmsu_i_jEHzyPGa-m24Kef8L71R8k')
GOOGLE_SHEETS_CREDENTIALS_FILE = os.getenv('GOOGLE_SHEETS_CREDENTIALS_FILE', 'google-sheets-credentials.json')

# Sheet Names
SHEET_TRADE_LOG = 'Trade Log'
SHEET_OPEN_POSITIONS = 'Open Positions'
SHEET_PENDING_TRADES = 'Pending Trades'

# Equity ("Stock Log") worksheet. Shares are logged one row per lot; a sale
# closes lots FIFO, splitting the last lot if the sale doesn't consume it whole.
SHEET_STOCK_LOG = 'Stock Log'
STOCK_LOG_HEADER = ['Entry Date', 'Exit Date', 'Ticker', 'Status', 'Qty',
                    'Entry', 'Current/Exit', 'Total P/L:']

# Non-Trade equity events that should still produce Stock Log rows. Option
# assignment/exercise delivers or removes shares, so it belongs in the log.
# ACAT transfers and dividends are deliberately excluded — the ACAT lots were
# already entered by hand, and there is nowhere to put a dividend.
EQUITY_RECEIVE_DELIVER_SUBTYPES = {'Assignment', 'Exercise'}

# Four-leg strategies: a call vertical and a put vertical held as one position
# and logged on one row, with all four strikes in Notes because the sheet has
# room for a single short/long pair.
#
# An iron condor's call side is a credit spread (short strike below long), so
# the whole position opens for a credit. A superbull's call side is a debit
# spread (long strike below short), so its bull put credit and bull call debit
# net out to either sign — the opening net price carries that sign, and the
# sheet's P&L (open + close) works out the same way regardless.
FOUR_LEG_STRATEGIES = ('IC', 'Superbull')

# What each side of a four-leg position is once it stands on its own, which is
# what a side-only exit leaves behind. Also the classifier's lookup, read
# backwards: the call vertical is what tells the two strategies apart.
FOUR_LEG_SIDE_STRATEGY = {
    'IC': {'Call': 'Bear Call Spread', 'Put': 'Bull Put Spread'},
    'Superbull': {'Call': 'Bull Call Spread', 'Put': 'Bull Put Spread'},
}

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
