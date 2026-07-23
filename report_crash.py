"""
Write a FAILED row to the Sync Log when run_today_prod.py dies before it can
report on itself.

run_today_prod.py records its own OK/FAILED heartbeat, but only once its
imports succeed. An import-time crash — an evicted/unreadable source file, a
missing dependency, a broken interpreter — kills it before SpreadsheetLogger
exists, so the run leaves no trace in the sheet and the failure goes unnoticed
until trades turn up missing. That is exactly how the 2026-07-16 and 2026-07-23
outages stayed silent.

This script is the fallback the wrapper calls in that case. It deliberately
imports nothing from this project: no config, no tastytrade_client, no
spreadsheet_logger. The sheet ID and credentials path are inlined so a crash in
any of those modules cannot also take down the reporting of that crash.

Usage: report_crash.py <exit_code> <log_excerpt_path>
"""
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID = '1plKfGr2mLUBt_-sgGMu42v5tImUozqEGSYokhQbeJbI'
CREDENTIALS_FILE = '/Users/Kevin/dev/tastytrade-logger/google-sheets-credentials.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']
SYNC_LOG_HEADER = ['Timestamp (PT)', 'Date Range', 'Status',
                   'Trades Logged', 'Details']
# Sheets truncates very long cells awkwardly; keep the excerpt readable.
MAX_DETAIL_CHARS = 900


def main():
    exit_code = sys.argv[1] if len(sys.argv) > 1 else '?'
    excerpt = ''
    if len(sys.argv) > 2:
        try:
            with open(sys.argv[2]) as f:
                # The last lines hold the exception; the head is just banner text.
                excerpt = ''.join(f.readlines()[-12:]).strip()
        except OSError as e:
            excerpt = f'(could not read error log: {e})'

    details = f'Job crashed before self-reporting (exit {exit_code}). {excerpt}'
    if len(details) > MAX_DETAIL_CHARS:
        details = details[:MAX_DETAIL_CHARS] + '…'

    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
    spreadsheet = gspread.authorize(creds).open_by_key(SPREADSHEET_ID)

    try:
        log_sheet = spreadsheet.worksheet('Sync Log')
    except gspread.exceptions.WorksheetNotFound:
        log_sheet = spreadsheet.add_worksheet(title='Sync Log', rows=1000, cols=5)
        log_sheet.append_row(SYNC_LOG_HEADER)

    timestamp = datetime.now(ZoneInfo('America/Los_Angeles')).strftime(
        '%Y-%m-%d %H:%M:%S')
    log_sheet.append_row([timestamp, '', 'FAILED', '0', details],
                         value_input_option='USER_ENTERED')
    print(f'✓ Sync Log updated: FAILED (crash, exit {exit_code})')


if __name__ == '__main__':
    sys.exit(main())
