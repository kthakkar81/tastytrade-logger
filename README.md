# Tastytrade Trade Logger

Automated trade logging system that syncs Tastytrade transactions to Google Sheets.

## Features

- ✅ Fetches transactions from Tastytrade API
- ✅ Classifies option strategies (spreads, CSPs, covered calls)
- ✅ Detects and links rolls (including multi-leg spread rolls)
- ✅ Matches closing trades to open positions
- ✅ Handles partial closes
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

### Daily Auto-Run

```bash
# Add to crontab
0 7 * * * cd /Users/Kevin/Documents/claude/tastytrade-logger && python main.py
```

## Google Sheets Structure

### Tab 1: Trade Log
Closed trades with full P&L

### Tab 2: Open Positions
Currently open positions with unrealized P&L

### Tab 3: Pending Trades
Review queue - check boxes to confirm before moving to Trade Log

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
