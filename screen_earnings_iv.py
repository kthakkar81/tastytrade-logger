"""
One-off screener: S&P 500 names with market cap > $5B, earnings 21-45 days
out, and IV rank > 50. Read-only use of the tastytrade market-metrics
endpoint via the existing TastytradeClient OAuth setup.
"""
import sys
import json
from datetime import date, timedelta
from tastytrade_client import TastytradeClient

TODAY = date(2026, 8, 4)
MIN_DAYS = 21
MAX_DAYS = 45
MIN_MCAP = 5_000_000_000
MIN_IVR = 50

def batched(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def main():
    import os
    if os.path.exists('market_metrics_raw.json') and '--refresh' not in sys.argv:
        with open('market_metrics_raw.json') as f:
            all_items = json.load(f)
        print(f"Loaded {len(all_items)} cached items (pass --refresh to re-fetch)")
    else:
        with open('sp500_universe.txt') as f:
            symbols = [s.strip() for s in f if s.strip()]

        client = TastytradeClient()
        if not client.authenticate():
            print("AUTH FAILED")
            sys.exit(1)

        client._ensure_authenticated()

        all_items = []
        for i, batch in enumerate(batched(symbols, 100)):
            url = f"{client.api_url}/market-metrics"
            params = {"symbols": ",".join(batch)}
            resp = client.session.get(url, params=params, timeout=(10, 30))
            if resp.status_code != 200:
                print(f"batch {i} FAILED: {resp.status_code} {resp.text[:300]}")
                continue
            data = resp.json()
            items = data.get('data', {}).get('items', [])
            all_items.extend(items)
            print(f"batch {i}: {len(batch)} symbols -> {len(items)} items")

        # dump raw for inspection
        with open('market_metrics_raw.json', 'w') as f:
            json.dump(all_items, f, indent=2)

    print(f"\nTotal items collected: {len(all_items)}")

    window_start = TODAY + timedelta(days=MIN_DAYS)
    window_end = TODAY + timedelta(days=MAX_DAYS)

    results = []
    for it in all_items:
        symbol = it.get('symbol')
        mcap_raw = it.get('market-cap')
        ivr_raw = it.get('implied-volatility-index-rank')
        earnings = it.get('earnings')

        if not mcap_raw or not ivr_raw or not earnings:
            continue

        mcap = float(mcap_raw)
        ivr = float(ivr_raw) * 100  # fraction -> percent

        if mcap <= MIN_MCAP:
            continue
        if ivr <= MIN_IVR:
            continue

        exp_date_str = earnings.get('expected-report-date')
        if not exp_date_str:
            continue
        exp_date = date.fromisoformat(exp_date_str)
        quarter_end_str = earnings.get('quarter-end-date')

        estimated = False
        next_date = exp_date

        if exp_date < TODAY:
            # expected-report-date is stale (points at the last completed
            # report). Estimate the *next* one using the historical
            # reporting lag (expected - quarter_end) applied to the next
            # quarter end (~91 days later).
            if not quarter_end_str:
                continue
            quarter_end = date.fromisoformat(quarter_end_str)
            lag_days = (exp_date - quarter_end).days
            next_quarter_end = quarter_end + timedelta(days=91)
            next_date = next_quarter_end + timedelta(days=lag_days)
            estimated = True

        if not (window_start <= next_date <= window_end):
            continue

        days_out = (next_date - TODAY).days

        results.append({
            'symbol': symbol,
            'market_cap_b': round(mcap / 1e9, 1),
            'iv_rank': round(ivr, 1),
            'earnings_date': next_date.isoformat(),
            'days_out': days_out,
            'estimated': estimated,
            'sector': it.get('sector'),
        })

    results.sort(key=lambda r: -r['iv_rank'])

    with open('screen_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{len(results)} matches (mcap > $5B, earnings {MIN_DAYS}-{MAX_DAYS}d out, IV rank > {MIN_IVR}):\n")
    print(f"{'Symbol':<8}{'MCap($B)':<10}{'IVR':<7}{'Earnings':<12}{'DaysOut':<9}{'Est?':<6}Sector")
    for r in results:
        print(f"{r['symbol']:<8}{r['market_cap_b']:<10}{r['iv_rank']:<7}{r['earnings_date']:<12}{r['days_out']:<9}{'Y' if r['estimated'] else 'N':<6}{r['sector']}")

if __name__ == "__main__":
    main()
