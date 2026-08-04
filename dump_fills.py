#!/usr/bin/env python3
"""
Dump raw Tastytrade transactions to JSON for eval datasets.

This is the INPUT side of an eval set: the exact payload the logger sees before
any processing. It reuses TastytradeClient.get_transactions() — the same call
run_today_prod.py makes — so the dump is byte-identical to production input.

Nothing is filtered, renamed, or normalized. What the API returned is what lands
in the file.

Usage:
    python dump_fills.py --start 2026-07-20 --end 2026-07-24
    python dump_fills.py --days 7
    python dump_fills.py --days 7 --out evals/inputs/week1.json
    python dump_fills.py --days 7 --split-by-day

Credentials come from .env via config.py — same as every other script here.
"""
import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from tastytrade_client import TastytradeClient


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--start', help='Start date YYYY-MM-DD')
    p.add_argument('--end', help='End date YYYY-MM-DD (default: today)')
    p.add_argument('--days', type=int,
                   help='Look back N days from today (alternative to --start)')
    p.add_argument('--out', default=None,
                   help='Output path (default: evals/inputs/fills_<start>_<end>.json)')
    p.add_argument('--split-by-day', action='store_true',
                   help='Also write one file per execution date, for per-day eval cases')
    return p.parse_args()


def resolve_dates(args):
    today = datetime.now().date()
    end = args.end or today.strftime('%Y-%m-%d')

    if args.start:
        start = args.start
    elif args.days:
        start = (today - timedelta(days=args.days)).strftime('%Y-%m-%d')
    else:
        sys.exit('✗ Provide either --start or --days')

    if start > end:
        sys.exit(f'✗ start ({start}) is after end ({end})')

    return start, end


def execution_date(txn):
    """YYYY-MM-DD from executed-at, falling back to transaction-date."""
    executed = txn.get('executed-at')
    if executed:
        return executed[:10]
    return txn.get('transaction-date', 'unknown')


def summarize(transactions):
    """Print a shape summary so you can sanity-check the pull before using it."""
    if not transactions:
        return

    by_type = defaultdict(int)
    by_day = defaultdict(int)
    symbols = set()

    for t in transactions:
        by_type[t.get('transaction-type', '?')] += 1
        by_day[execution_date(t)] += 1
        if t.get('underlying-symbol'):
            symbols.add(t['underlying-symbol'])

    print('\n--- Dump summary ---')
    print(f'Total transactions : {len(transactions)}')
    print(f'Underlyings        : {len(symbols)} ({", ".join(sorted(symbols))})')

    print('\nBy transaction-type:')
    for k, v in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f'  {v:>4}  {k}')

    print('\nBy execution date:')
    for k, v in sorted(by_day.items()):
        print(f'  {v:>4}  {k}')


def main():
    args = parse_args()
    start, end = resolve_dates(args)

    client = TastytradeClient()
    if not client.authenticate():
        sys.exit('✗ Authentication failed')

    transactions = client.get_transactions(start_date=start, end_date=end)

    if not transactions:
        print(f'✓ No transactions found for {start} to {end} — nothing written')
        return 0

    out_path = Path(args.out) if args.out else Path('evals/inputs') / f'fills_{start}_to_{end}.json'
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Raw and unmodified: a JSON array of the API's transaction objects, exactly
    # as returned. Provenance lives in the filename and the sidecar below, not in
    # a wrapper around the payload — so this file can be fed straight into the
    # processor without unwrapping.
    with out_path.open('w') as f:
        json.dump(transactions, f, indent=2)

    # Sidecar metadata, kept out of the payload on purpose.
    meta = {
        'fetched_at': datetime.now().isoformat(),
        'start_date': start,
        'end_date': end,
        'account_number': client.account_number,
        'api_url': client.api_url,
        'transaction_count': len(transactions),
        'source': 'TastytradeClient.get_transactions',
    }
    meta_path = out_path.with_suffix('.meta.json')
    with meta_path.open('w') as f:
        json.dump(meta, f, indent=2)

    print(f'\n✓ Wrote {len(transactions)} transactions → {out_path}')
    print(f'✓ Wrote metadata → {meta_path}')

    if args.split_by_day:
        day_dir = out_path.parent / 'by_day'
        day_dir.mkdir(parents=True, exist_ok=True)
        buckets = defaultdict(list)
        for t in transactions:
            buckets[execution_date(t)].append(t)
        for day, items in sorted(buckets.items()):
            day_path = day_dir / f'fills_{day}.json'
            with day_path.open('w') as f:
                json.dump(items, f, indent=2)
        print(f'✓ Wrote {len(buckets)} per-day files → {day_dir}/')

    summarize(transactions)
    return 0


if __name__ == '__main__':
    sys.exit(main())
