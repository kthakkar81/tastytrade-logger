#!/usr/bin/env python3
"""
Backfill per-leg opening prices into open multi-leg rows.

A position can be legged out of - closed a leg or two at a time, across several
orders - and each closing order is then reconciled against just the legs it
covers. That needs to know what each leg was opened for, which cannot be
re-derived from the closing fills.

New multi-leg positions record it at open time, in the column
config.OPTIONS_LOG_LEG_COL. This backfills the rows that predate that by
re-fetching each row's opening order from Tastytrade and re-deriving the split
from the original legs. The derived legs must account for the row's own opening
price and fees before anything is written, so a wrong order can't quietly
overwrite a row. Rows whose opening order can't be found are reported and left
alone.

This is the per-leg counterpart of backfill_ic_side_credits.py, which does the
same job one level coarser, for each side of a four-leg position.

Usage:
    python backfill_leg_prices.py [--apply] [--row N]

Without --apply it is a dry run and writes nothing.
"""
import argparse
import sys
from datetime import datetime, timedelta

import config
from spreadsheet_logger import SpreadsheetLogger
from tastytrade_client import TastytradeClient
from transaction_processor import TransactionProcessor

# How far either side of the row's opening date to look for its opening order,
# so a fill that straddles a timezone boundary is still found.
SEARCH_PAD_DAYS = 1

# Tolerance when checking the re-derived legs against the row's own figures.
PENNY = 0.011


def norm(date_str):
    return SpreadsheetLogger._norm_date(date_str)


def money(cell):
    return SpreadsheetLogger._parse_money(cell)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='write the leg column (default: dry run)')
    ap.add_argument('--row', type=int, action='append',
                    help='only this row number (repeatable)')
    args = ap.parse_args()

    logger = SpreadsheetLogger(config.TRADE_LOG_SPREADSHEET_ID)
    if not logger.authenticate():
        return 1

    leg_col = config.OPTIONS_LOG_LEG_COL
    leg_idx = config.OPTIONS_LOG_LEG_COL_INDEX

    targets = []
    for i, row in enumerate(logger.sheet.get_all_values(), start=1):
        if i == 1 or len(row) < 16 or row[4] != 'Open':
            continue
        if args.row and i not in args.row:
            continue
        # More than one strike means more than one leg, and so something to
        # split. Single-leg rows have nothing to record.
        if len(logger._row_strikes(row)) < 2:
            continue
        if len(row) > leg_idx and logger._parse_leg_cell(row[leg_idx]):
            continue  # already recorded
        targets.append((i, row))

    if not targets:
        print('✓ Every open multi-leg row already records its per-leg prices')
        return 0

    client = TastytradeClient()
    if not client.authenticate():
        return 1

    updated = 0
    for row_num, row in targets:
        underlying, opened, expiration = row[2], row[0], row[5]
        print(f"\nrow {row_num}: {underlying} {row[3]} opened {opened} "
              f"exp {expiration}")

        day = datetime.strptime(norm(opened), '%m/%d/%Y')
        start = (day - timedelta(days=SEARCH_PAD_DAYS)).strftime('%Y-%m-%d')
        end = (day + timedelta(days=SEARCH_PAD_DAYS)).strftime('%Y-%m-%d')

        txns = client.get_transactions(start_date=start, end_date=end)
        processor = TransactionProcessor()
        processor.load_transactions(
            [t for t in txns if t.get('underlying-symbol') == underlying])

        want_strikes = logger._row_strikes(row)
        match = None
        for trade in processor.process_orders():
            if not trade.get('leg_breakdown'):
                continue
            # A row can be opened outright or rolled into; a roll's new legs
            # are what its row goes on to hold, so either can be the source.
            if trade.get('action') == 'OPEN':
                exp = trade.get('expiration', '')
            elif trade.get('action') == 'ROLL':
                exp = trade.get('new_expiration', '')
            else:
                continue
            if (norm(exp) == norm(expiration)
                    and norm(trade.get('trade_date', '')) == norm(opened)
                    and {f"${leg['strike']:,.2f}"
                         for leg in trade['leg_breakdown']} == want_strikes):
                match = trade
                break

        if not match:
            print('  ✗ opening order not found — leaving this row alone')
            continue

        # The legs are the position: they have to account for the row's own
        # opening price, or this is not the row's opening order.
        legs = match['leg_breakdown']
        net = sum(leg['net_price'] for leg in legs)
        row_net = money(row[10])

        if abs(net - row_net) > PENNY:
            print(f"  ✗ legs total ${net:,.2f} but the row says "
                  f"${row_net:,.2f} — leaving this row alone")
            continue

        # Fees only reconcile for an outright open. A roll's fee cell covers
        # the legs it closed as well as the ones it opened, so there is
        # nothing to compare the opening legs' fees against.
        if match['action'] == 'OPEN':
            fees = sum(leg['fees'] for leg in legs)
            row_fees = money(row[9])
            if abs(fees - row_fees) > PENNY:
                print(f"  ⚠ legs' fees ${fees:,.2f} differ from the row's "
                      f"${row_fees:,.2f} — leaving this row alone")
                continue

        cell = logger.format_leg_cell(match.get('side_breakdown'), legs)
        print(f"  → {leg_col}{row_num} = {cell}")

        if args.apply:
            logger.sheet.update_acell(f'{leg_col}{row_num}', cell)
            print('  ✓ written')
            updated += 1

    if not args.apply:
        print('\n(dry run — re-run with --apply to write)')
    else:
        print(f"\n✓ Backfilled {updated} row(s)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
