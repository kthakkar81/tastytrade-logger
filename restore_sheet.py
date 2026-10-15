#!/usr/bin/env python3
"""
Restore a spreadsheet from a snapshot_sheet.py snapshot.

Writes the whole grid back rather than just the rows that look changed,
because an inserted row shifts every row beneath it - the cells that need
putting back are not the ones that were written to.

Formulas are restored as formulas (the snapshot captured them as such and this
writes with USER_ENTERED), and any rows added since the snapshot are deleted so
the row count matches again. Cell *formatting* is not snapshotted and so is not
restored; it survives a value rewrite, but a row that was inserted and is now
deleted takes its formatting with it, which is the intended outcome.

Usage:
    python restore_sheet.py sheet_snapshot_20261015-093000.json
    python restore_sheet.py snap.json --worksheet 'Options Log'
    python restore_sheet.py snap.json --apply

Without --apply it reports what it would change and writes nothing.
"""
import argparse
import json
import sys

import gspread

from snapshot_sheet import open_spreadsheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('snapshot')
    ap.add_argument('--worksheet', action='append',
                    help='only this worksheet (repeatable; default: all)')
    ap.add_argument('--apply', action='store_true',
                    help='write the restore (default: dry run)')
    args = ap.parse_args()

    with open(args.snapshot) as fh:
        snapshot = json.load(fh)

    print(f"Snapshot of '{snapshot['spreadsheet_title']}' "
          f"taken {snapshot['taken_at']}")

    ss = open_spreadsheet(snapshot['spreadsheet_id'])
    print(f"✓ Connected to {ss.title}\n")

    for title, saved in snapshot['worksheets'].items():
        if args.worksheet and title not in args.worksheet:
            continue

        try:
            ws = ss.worksheet(title)
        except Exception:
            print(f"  ✗ '{title}' no longer exists — skipping")
            continue

        want = saved['values']
        have = ws.get_all_values(value_render_option='FORMULA')

        if have == want:
            print(f"  {title:<20} unchanged")
            continue

        differing = sum(1 for i in range(max(len(have), len(want)))
                        if (have[i] if i < len(have) else None)
                        != (want[i] if i < len(want) else None))
        print(f"  {title:<20} {len(have)} rows now vs {len(want)} in snapshot, "
              f"{differing} row(s) differ")

        if not args.apply:
            continue

        # Pad every row to the snapshot's widest, so a cell that gained a value
        # after the snapshot is cleared rather than left behind.
        width = max((len(r) for r in want), default=0)
        padded = [list(r) + [''] * (width - len(r)) for r in want]

        if padded:
            # Two passes, because the two input modes each get one thing wrong.
            # RAW would store a formula as its own text; USER_ENTERED reparses
            # anything that looks like a date, so a text timestamp such as
            # '2026-10-14 18:03:20' would come back as a date serial. So:
            # everything RAW, then the formula cells again as USER_ENTERED.
            ws.update(values=padded, range_name='A1',
                      value_input_option='RAW')

            formulas = [
                {'range': gspread.utils.rowcol_to_a1(r + 1, c + 1),
                 'values': [[cell]]}
                for r, row_vals in enumerate(padded)
                for c, cell in enumerate(row_vals)
                if isinstance(cell, str) and cell.startswith('=')
            ]
            if formulas:
                ws.batch_update(formulas, value_input_option='USER_ENTERED')
                print(f"    re-entered {len(formulas)} formula cell(s)")

        # Rows added since the snapshot shift everything below them, so the
        # grid is only truly back once the extra ones are gone.
        extra = len(have) - len(want)
        if extra > 0:
            ws.delete_rows(len(want) + 1, len(have))
            print(f"    deleted {extra} row(s) added since the snapshot")

        print(f"    ✓ restored {len(padded)} rows")

    if not args.apply:
        print('\n(dry run — re-run with --apply to restore)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
