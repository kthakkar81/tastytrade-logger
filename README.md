# Tastytrade Trade Logger

Automated trade logging system that syncs Tastytrade transactions to Google Sheets.

## Features

- ✅ Fetches transactions from Tastytrade API
- ✅ Classifies option strategies (spreads, CSPs, covered calls, iron
  condors, superbulls)
- ✅ Detects and links rolls (including multi-leg spread rolls)
- ✅ Matches closing trades to open positions
- ✅ Handles partial closes
- ✅ Logs share purchases and sales to the Stock Log (FIFO lot matching)
- ✅ Calculates P&L automatically
- ✅ Syncs to Google Sheets with pending review workflow

## Setup

### 1. Install Dependencies

```bash
cd tastytrade-logger
pip install -r requirements.txt
```

### 2. Configure Credentials

Edit `.env` file and add your Tastytrade credentials:

```
TASTYTRADE_USERNAME=your_username
TASTYTRADE_PASSWORD=your_password
```

### 3. Test API Connection

```bash
python tastytrade_client.py
```

You should see:
```
✓ Authenticated as your_username
✓ Fetched X transactions...
✓ Fetched X open positions...
```

### 4. Set Up Google Sheets OAuth

(Instructions coming in Phase 4)

## Usage

### Manual Sync

```bash
python main.py
```

### Scheduled Auto-Run

Runs via launchd (`~/Library/LaunchAgents/com.kevin.tastytrade-logger.plist`) at
14:03, 18:03 and 21:03 PT, Monday–Friday. The entry point is `run_sync.sh`,
which wraps `run_today_prod.py` and reports crashes the job can't report itself.

```bash
launchctl print gui/$(id -u)/com.kevin.tastytrade-logger   # status
launchctl kickstart -p gui/$(id -u)/com.kevin.tastytrade-logger  # run now
tail -f ~/Library/Logs/tastytrade-logger/{out,err}.log     # logs
```

**This repo must stay outside `~/Documents` and `~/Desktop`.** Those are
iCloud-synced, and under disk pressure macOS evicts files there to cloud stubs
that a background launchd job cannot materialize — reads fail with `EDEADLK`
and the sync dies at import. That caused silent outages on 2026-07-16 and
2026-07-23; `run_sync.sh` now refuses to run from such a path.

## Google Sheets Structure

Worksheets the logger reads or writes:

| Worksheet | Written by logger | Contents |
|---|---|---|
| `Options Log` | yes | Option trades, one row per position, open and closed |
| `Stock Log` | yes | Share lots, one row per lot, open and closed |
| `Import Errors` | yes | Anything that couldn't be matched or classified |
| `Sync Log` | yes | One heartbeat row per run |
| `Options Analysis`, `Stock Analysis` | no | Kevin's own dashboards |

### Stock Log

`Entry Date | Exit Date | Ticker | Status | Qty | Entry | Current/Exit | Total P/L`

One row per **lot**. While a lot is open, `Current/Exit` holds
`=IF(D{r}="OPEN", GOOGLEFINANCE(C{r}), "ENTER PRICE")`; closing it replaces that
with the literal exit price. `Total P/L` is always `=(G{r}-F{r})*E{r}`.

- **Buys** append a new lot. `Entry` is the raw share-weighted execution price —
  the sheet has no fee column, so fees are dropped, matching the rows entered by
  hand. Multiple fills of one order are consolidated into a single lot.
- **Sales** close lots **FIFO** (oldest entry date first). If the sale doesn't
  consume the last lot whole, that row is split: the sold shares are closed in
  place and the remainder is re-inserted directly below as a still-open lot.
- **Assignment/exercise** (`Receive Deliver`) delivers or removes shares and is
  logged at the strike. ACAT transfers and dividends are deliberately ignored.
- **Long only.** Short stock (`Sell to Open` / `Buy to Close` equity) goes to
  Import Errors rather than being guessed at, because `=(G-F)*E` assumes a long.
- Re-running is idempotent: a buy is a duplicate if a lot with the same ticker,
  entry date and entry price already exists (including rows entered by hand); a
  sale is a duplicate if closed rows at that ticker, exit date and exit price
  already total the sale.

### Options Log — four-leg positions (iron condors, superbulls)

Both strategies pair a call vertical with a put vertical and are held as one
position, so they occupy **one row** with all four strikes in Notes — the sheet
has room for a single short/long pair. What separates them is the call side:

| | Call side | Put side | Opens for |
|---|---|---|---|
| `IC` | Bear call spread (short below long) | Bull put spread | a credit |
| `Superbull` | Bull call spread (long below short) | Bull put spread | either sign |

A superbull's call debit and put credit net out to a credit or a debit
depending on the strikes, so its Opening Net Price can be negative. P&L is
`open + close` either way, so nothing downstream cares about the sign.

**Exiting one side.** Either spread can be closed on its own, leaving the other
running. Those fills arrive as a plain 2-leg close with no open row to match, so
the logger converts the row instead:

1. The four-leg row is closed at the real side close price **plus** the
   surviving side's opening price, so it realises exactly the closed side's P&L.
2. The surviving vertical is appended as an ordinary spread row (keeping the
   four-leg row's entry date) holding the opening price carried out of it, so
   its own eventual close matches with no special handling.

The two rows always sum to the real total. This only works because each side's
opening price is recorded in Notes when the position is opened — it can't be
re-derived from the closing fills. Rows predating that, and closes that cover
only part of a side, go to Import Errors rather than being guessed at;
`backfill_ic_side_credits.py` fills in the older rows from their opening orders.

## Project Structure

```
tastytrade-logger/
├── config.py                 # Settings and strategy definitions
├── tastytrade_client.py      # API wrapper
├── transaction_processor.py  # Parse & classify transactions
├── position_matcher.py       # Match closes to opens
├── sheets_manager.py         # Google Sheets integration
├── main.py                   # Daily sync orchestrator
└── requirements.txt          # Dependencies
```

## Development Status

- [x] Phase 1: Core API Client
- [ ] Phase 2: Transaction Processing
- [ ] Phase 3: Position Matching
- [ ] Phase 4: Google Sheets Integration
- [ ] Phase 5: Roll Detection & Linking
- [ ] Phase 6: Scheduling & Polish
