#!/usr/bin/env python3
"""
Backfill per-side opening prices into open four-leg rows (IC, superbull).

Four-leg rows are logged with all four strikes in Notes but, until now, without
any record of what each vertical was opened for. That split is needed the moment
one side is closed on its own: the surviving vertical has to carry its own share
of the opening price out to its own row, and it can't be re-derived from the
closing fills.

New four-leg positions record the split at open time. This backfills the rows
that predate that by re-fetching each row's opening order from Tastytrade and
re-deriving the split from the original legs. Rows whose opening order can't be
found are reported and left alone.

Every four-leg order used to be labelled 'IC'; re-deriving now tells an iron
condor from a superbull, so a mislabelled row's Strategy cell is corrected
alongside its Notes.

Usage:
    python backfill_ic_side_credits.py [--apply]

Without --apply it is a dry run and writes nothing.
"""
import argparse
import sys
from datetime import datetime, timedelta

import config
from spreadsheet_logger import SpreadsheetLogger
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor


def norm(date_str):
    return SpreadsheetLogger._norm_date(date_str)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='write the notes (default: dry run)')
    args = ap.parse_args()

    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        return 1

    targets = []
    for i, row in enumerate(logger.sheet.get_all_values(), start=1):
        if (len(row) < 16 or row[3] not in config.FOUR_LEG_STRATEGIES
                or row[4] != 'Open'):
            continue
        if logger._parse_side_notes(row[15]):
            continue  # already recorded
        targets.append((i, row))

    if not targets:
        print('✓ Every open four-leg row already records its per-side prices')
        return 0

    client = TastytradeClient()
    if not client.authenticate():
        return 1

    updated = 0
    for row_num, row in targets:
        underlying, opened, expiration = row[2], row[0], row[5]
        print(f"\nrow {row_num}: {underlying} opened {opened} exp {expiration}")

        # The opening order is on the row's opening date; widen by a day either
        # side so a timezone-straddling fill is still found.
        day = datetime.strptime(norm(opened), '%m/%d/%Y')
        start = (day - timedelta(days=1)).strftime('%Y-%m-%d')
        end = (day + timedelta(days=1)).strftime('%Y-%m-%d')

        txns = client.get_transactions(start_date=start, end_date=end)
        processor = TransactionProcessor()
        processor.load_transactions(
            [t for t in txns if t.get('underlying-symbol') == underlying])

        match = None
        for trade in processor.process_orders():
            if (trade.get('action') == 'OPEN'
                    and trade.get('strategy') in config.FOUR_LEG_STRATEGIES
                    and norm(trade.get('expiration', '')) == norm(expiration)
                    and norm(trade.get('trade_date', '')) == norm(opened)
                    and f"Strikes: {trade.get('strikes')}" == row[15]):
                match = trade
                break

        if not match or not match.get('side_breakdown'):
            print('  ✗ opening order not found — leaving this row alone')
            continue

        notes = logger._four_leg_notes(match['strikes'], match['side_breakdown'])
        print(f"  → {notes}")

        relabel = match['strategy'] if match['strategy'] != row[3] else None
        if relabel:
            print(f"  → Strategy: {row[3]} → {relabel}")

        if args.apply:
            logger.sheet.update_acell(f'P{row_num}', notes)
            if relabel:
                logger.sheet.update_acell(f'D{row_num}', relabel)
            print('  ✓ written')
            updated += 1

    if not args.apply:
        print('\n(dry run — re-run with --apply to write)')
    else:
        print(f"\n✓ Backfilled {updated} four-leg row(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
