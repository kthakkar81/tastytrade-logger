"""
Tests for closing one side of an iron condor.

Buying back a single IC side is a routine adjustment, but it reaches the logger
as a plain 2-leg CLOSE with no OPEN row of its own to match. The conversion
that handles it rewrites a production trading log, so the arithmetic and the
refusal cases are pinned here.

The fixture is the real NOW 09/18/26 condor: opened 8/25/2026 for a $301.01 net
credit (150/145 calls + 115/110 puts, 2 contracts), with the call side bought
back on 8/31/2026 for a $520.52 debit.
"""
import json
from pathlib import Path

import pytest

from spreadsheet_logger import SpreadsheetLogger
from transaction_processor import TransactionProcessor

FIXTURE = Path(__file__).parent / 'evals' / 'inputs' / 'ic_side_close_now.json'

HEADER = ['Opening Date', 'Closing Date', 'Underlying', 'Strategy Type', 'Status',
          'Expiration', 'Short/CSP/CC Strike', 'Long Strike', 'Delta', 'Fees',
          'Opening Net Price', 'Closing Net Price (debit)', 'Contracts',
          'Total PnL ($)', 'ROC', 'Notes/Setup']

FOUR_STRIKES = '$150.00/$145.00/$115.00/$110.00'


class StubSheet:
    """Minimal stand-in for a gspread worksheet, recording what gets written."""

    def __init__(self, rows):
        self.rows = [list(r) + [''] * (16 - len(r)) for r in rows]

    def get_all_values(self):
        return [list(r) for r in self.rows]

    def row_values(self, n):
        return list(self.rows[n - 1])

    def batch_update(self, updates, value_input_option=None):
        for update in updates:
            cell = update['range']
            self.rows[int(cell[1:]) - 1][ord(cell[0]) - 65] = update['values'][0][0]

    def update(self, values=None, range_name=None, value_input_option=None):
        self.rows.append(list(values[0]) + [''] * (16 - len(values[0])))

    def update_acell(self, cell, value):
        self.rows[int(cell[1:]) - 1][ord(cell[0]) - 65] = value

    def format(self, *args, **kwargs):
        pass


@pytest.fixture(scope='module')
def trades():
    """The IC open and the call-side close, as the processor produces them."""
    processor = TransactionProcessor()
    processor.load_transactions(json.loads(FIXTURE.read_text()))
    processed = processor.process_orders()
    return (next(t for t in processed if t['action'] == 'OPEN'),
            next(t for t in processed if t['action'] == 'CLOSE'))


@pytest.fixture
def ic_notes(trades):
    """The Notes cell the logger writes when this IC is opened."""
    open_trade, _ = trades
    return SpreadsheetLogger('stub')._ic_notes(open_trade['strikes'],
                                               open_trade['side_breakdown'])


def make_logger(notes, contracts='2'):
    logger = SpreadsheetLogger('stub')
    logger.sheet = StubSheet([
        HEADER,
        ['8/25/2026', '', 'NOW', 'IC', 'Open', '9/18/2026', '', '', '',
         '$8.99', '$301.01', '', contracts, '', '', notes],
    ])
    logger.errors = []
    logger.log_error = lambda trade, msg: logger.errors.append(msg)
    return logger


def test_side_breakdown_sums_to_the_ic_credit(trades):
    open_trade, _ = trades
    sides = open_trade['side_breakdown']

    assert sides['C']['strikes'] == '$150.00/$145.00'
    assert sides['P']['strikes'] == '$115.00/$110.00'
    assert sides['C']['net_price'] + sides['P']['net_price'] == \
        pytest.approx(open_trade['net_price'])


def test_notes_round_trip(ic_notes):
    assert ic_notes.startswith(f"Strikes: {FOUR_STRIKES}")

    sides = SpreadsheetLogger._parse_ic_sides(ic_notes)
    assert sides['Call'] == {'strikes': '$150.00/$145.00', 'credit': 115.50}
    assert sides['Put'] == {'strikes': '$115.00/$110.00', 'credit': 185.50}


def test_closing_the_call_side_realises_only_that_side(trades, ic_notes):
    _, close = trades
    logger = make_logger(ic_notes)

    assert logger._convert_ic_side_close(close) == (True, True)

    ic_row = logger.sheet.rows[1]
    assert ic_row[4] == 'Closed'
    assert ic_row[1] == '8/31/2026'

    # The closing price carries the surviving put credit out alongside the real
    # call debit, so the row realises the call side's P&L and nothing else.
    assert float(ic_row[11]) == pytest.approx(-(520.52 + 185.50), abs=0.01)
    assert float(ic_row[13]) == pytest.approx(115.50 - 520.52, abs=0.02)


def test_surviving_side_becomes_an_ordinary_spread_row(trades, ic_notes):
    _, close = trades
    logger = make_logger(ic_notes)
    logger._convert_ic_side_close(close)

    survivor = logger.sheet.rows[2]
    assert survivor[2:8] == ['NOW', 'Bull Put Spread', 'Open', '9/18/2026',
                             '$115.00', '$110.00']
    # Keeps the condor's entry date - that is when the put risk went on.
    assert survivor[0] == '8/25/2026'
    assert float(survivor[10]) == pytest.approx(185.50, abs=0.01)
    assert survivor[12] == 2


def test_the_two_rows_sum_to_the_real_total(trades, ic_notes):
    open_trade, close = trades
    logger = make_logger(ic_notes)
    logger._convert_ic_side_close(close)

    realised = float(logger.sheet.rows[1][13])
    carried = float(logger.sheet.rows[2][10])
    assert realised + carried == pytest.approx(
        open_trade['net_price'] + close['net_price'], abs=0.02)


def test_rerun_does_not_convert_twice(trades, ic_notes):
    _, close = trades
    logger = make_logger(ic_notes)
    logger._convert_ic_side_close(close)

    assert logger._convert_ic_side_close(close) == (True, True)
    assert len(logger.sheet.rows) == 3, 'appended a second survivor row'


def test_unrelated_close_is_left_to_the_normal_path(trades, ic_notes):
    _, close = trades
    logger = make_logger(ic_notes)

    other = dict(close, strikes='$200.00/$195.00')
    assert logger._convert_ic_side_close(other) == (False, False)
    assert logger.errors == []


def test_partial_side_close_refuses_rather_than_guessing(trades, ic_notes):
    """Closing 1 of 2 leaves part of the call spread open - unrepresentable."""
    _, close = trades
    logger = make_logger(ic_notes)

    assert logger._convert_ic_side_close(dict(close, quantity=1)) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert len(logger.sheet.rows) == 2
    assert 'Partial IC side close' in logger.errors[0]


def test_ic_row_without_recorded_credits_refuses(trades):
    """Rows predating per-side tracking can't be split - say so, don't guess."""
    _, close = trades
    logger = make_logger(f"Strikes: {FOUR_STRIKES}")

    assert logger._convert_ic_side_close(close) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert 'no per-side credit' in logger.errors[0]
