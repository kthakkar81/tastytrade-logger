#!/usr/bin/env python3
"""
Snapshot every worksheet's contents to a local file, so a change can be undone.

Cells are read as formulas, not as their displayed values, so the sheet's own
arithmetic (`=(K284+L284)`, `=22.56+2.53`) comes back as arithmetic rather than
as a frozen number. Restoring from a values-only snapshot would quietly turn
every formula in the log into a literal.

This is the safety net for anything that rewrites rows in place or inserts
them - an insert shifts every row below it, so "put it back" means restoring
the whole grid, not the rows that were touched.

Usage:
    python snapshot_sheet.py                  # snapshot the production log
    python snapshot_sheet.py --out mine.json

Restore with restore_sheet.py.
"""
import argparse
import json
import sys
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ['https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive']


def open_spreadsheet(sheet_id):
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SHEETS_CREDENTIALS_FILE, scopes=SCOPES)
    return gspread.authorize(creds).open_by_key(sheet_id)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sheet-id', default=config.TRADE_LOG_SPREADSHEET_ID)
    ap.add_argument('--out', default=None,
                    help='output path (default: sheet_snapshot_<stamp>.json)')
    args = ap.parse_args()

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    out = args.out or f'sheet_snapshot_{stamp}.json'

    ss = open_spreadsheet(args.sheet_id)
    print(f"✓ Connected to {ss.title}")

    snapshot = {
        'taken_at': datetime.now().isoformat(timespec='seconds'),
        'spreadsheet_id': args.sheet_id,
        'spreadsheet_title': ss.title,
        'worksheets': {},
    }

    for ws in ss.worksheets():
        values = ws.get_all_values(value_render_option='FORMULA')
        snapshot['worksheets'][ws.title] = {
            'sheet_id': ws.id,
            'row_count': ws.row_count,
            'col_count': ws.col_count,
            'values': values,
        }
        widest = max((len(r) for r in values), default=0)
        print(f"  {ws.title:<20} {len(values):>4} rows x {widest} cols")

    with open(out, 'w') as fh:
        json.dump(snapshot, fh, indent=1)

    print(f"\n✓ Wrote {out}")
    print(f"  Restore with: python restore_sheet.py {out}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
