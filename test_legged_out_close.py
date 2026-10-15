"""
Tests for a four-leg position legged out of rather than exited a side at a time.

Closing one whole side is already handled (see test_ic_side_close.py). This is
the messier case: the legs come off in whatever groups the orders happened to
fill in, so the close covers three of the four legs and the fourth is left
running on its own. Before this was handled, the 3-leg order couldn't be
classified at all and the lone leg had no row to match, so one closed position
produced two import errors and stayed Open in the log.

The fixture is the real IREN 10/30/26 superbull: opened 10/12/2026 for a $90.05
net credit (46/45 calls + 33/32 puts, 4 contracts), then unwound on 10/14/2026
across two orders - 46C/45C/33P together for a $1,193.48 debit, and the long 32P
on its own for a $1,299.49 credit. True total: +$196.06.
"""
import json
from pathlib import Path

import pytest

from spreadsheet_logger import SpreadsheetLogger
from transaction_processor import TransactionProcessor

FIXTURE = Path(__file__).parent / 'evals' / 'inputs' / 'legged_out_iren.json'

HEADER = ['Opening Date', 'Closing Date', 'Underlying', 'Strategy Type', 'Status',
          'Expiration', 'Short/CSP/CC Strike', 'Long Strike', 'Delta', 'Fees',
          'Opening Net Price', 'Closing Net Price (debit)', 'Contracts',
          'Total PnL ($)', 'ROC', 'Notes/Setup']

FOUR_STRIKES = '$46.00/$45.00/$33.00/$32.00'


class StubSheet:
    """
    Minimal stand-in for a gspread worksheet, recording what gets written.

    Reads come back as strings, the way the real API hands back every cell
    whatever was written into it - the logger parses its own numbers back out
    of them, so a stub that returned live floats would hide that work.
    `rows` keeps the raw written values for assertions.
    """

    def __init__(self, rows):
        self.rows = [list(r) + [''] * (16 - len(r)) for r in rows]

    def get_all_values(self):
        return [[str(c) for c in r] for r in self.rows]

    def row_values(self, n):
        return [str(c) for c in self.rows[n - 1]]

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

    def batch_format(self, *args, **kwargs):
        pass


@pytest.fixture(scope='module')
def trades():
    """The open, the 3-leg close and the lone-leg close, in that order."""
    processor = TransactionProcessor()
    processor.load_transactions(json.loads(FIXTURE.read_text()))
    processed = processor.process_orders()

    open_trade = next(t for t in processed if t['action'] == 'OPEN')
    three_leg = next(t for t in processed if t['action'] == 'CLOSE'
                     and len(t['leg_breakdown']) == 3)
    lone_leg = next(t for t in processed if t['action'] == 'CLOSE'
                    and len(t['leg_breakdown']) == 1)
    return open_trade, three_leg, lone_leg


@pytest.fixture
def notes(trades):
    """The Notes cell the logger writes when this superbull is opened."""
    open_trade, _, _ = trades
    return SpreadsheetLogger('stub')._four_leg_notes(open_trade['strikes'],
                                                     open_trade['side_breakdown'])


def make_logger(notes, contracts='4'):
    logger = SpreadsheetLogger('stub')
    logger.sheet = StubSheet([
        HEADER,
        ['10/12/2026', '', 'IREN', 'Super Bull', 'Open', '10/30/2026', '', '', '',
         '$17.95', '$90.05', '', contracts, '', '', notes],
    ])
    logger.errors = []
    logger.log_error = lambda trade, msg: logger.errors.append(msg)
    return logger


def test_three_leg_close_is_classified_not_abandoned(trades):
    """It used to land in Import Errors as 'Unknown' and stop there."""
    _, three_leg, _ = trades

    assert three_leg['strategy'] == 'Super Bull'
    assert three_leg['strikes'] == '$46.00/$45.00/$33.00'
    assert three_leg['net_price'] == pytest.approx(-1193.48, abs=0.01)


def test_per_leg_prices_round_trip_through_notes(trades, notes):
    open_trade, _, _ = trades

    legs = SpreadsheetLogger._parse_leg_notes(notes)
    assert legs == {
        (45.0, 'C'): -108.48,
        (46.0, 'C'): 75.51,
        (32.0, 'P'): -364.48,
        (33.0, 'P'): 487.50,
    }
    # The four legs are the position: they must account for all of its price.
    assert sum(legs.values()) == pytest.approx(open_trade['net_price'], abs=0.01)


def test_closing_three_legs_realises_only_those_legs(trades, notes):
    _, three_leg, _ = trades
    logger = make_logger(notes)

    assert logger._convert_four_leg_orphan_close(three_leg) == (True, True)

    parent = logger.sheet.rows[1]
    assert parent[4] == 'Closed'
    assert parent[1] == '10/14/2026'
    # The real 3-leg debit less the long put's opening price, which leaves with it.
    assert float(parent[11]) == pytest.approx(-829.00, abs=0.01)
    assert float(parent[13]) == pytest.approx(-738.95, abs=0.02)


def test_orphan_leg_becomes_an_ordinary_long_put_row(trades, notes):
    _, three_leg, _ = trades
    logger = make_logger(notes)
    logger._convert_four_leg_orphan_close(three_leg)

    orphan = logger.sheet.rows[2]
    # A bought leg is a long Put, so its strike belongs in the long column.
    assert orphan[2:8] == ['IREN', 'Put', 'Open', '10/30/2026', '', '$32.00']
    # Keeps the superbull's entry date - that is when the risk went on.
    assert orphan[0] == '10/12/2026'
    assert float(orphan[10]) == pytest.approx(-364.48, abs=0.01)
    assert orphan[12] == 4


def test_the_two_rows_sum_to_the_real_total(trades, notes):
    open_trade, three_leg, lone_leg = trades
    logger = make_logger(notes)
    logger._convert_four_leg_orphan_close(three_leg)

    realised = float(logger.sheet.rows[1][13])
    carried = float(logger.sheet.rows[2][10])
    assert realised + carried == pytest.approx(
        open_trade['net_price'] + three_leg['net_price'], abs=0.02)

    # And once the orphan's own close lands, the pair realise the whole trade.
    assert realised + carried + lone_leg['net_price'] == pytest.approx(196.06, abs=0.02)


def test_orphan_row_closes_through_the_ordinary_path(trades, notes):
    """The point of carrying it out: no special handling for its own close."""
    _, three_leg, lone_leg = trades
    logger = make_logger(notes)
    logger._convert_four_leg_orphan_close(three_leg)

    status, detail = logger._close_matching_open_rows(lone_leg)
    assert status == 'closed'

    orphan = logger.sheet.rows[2]
    assert orphan[4] == 'Closed'
    assert float(orphan[13]) == pytest.approx(935.01, abs=0.02)


def test_rerun_does_not_convert_twice(trades, notes):
    _, three_leg, _ = trades
    logger = make_logger(notes)
    logger._convert_four_leg_orphan_close(three_leg)

    assert logger._convert_four_leg_orphan_close(three_leg) == (True, True)
    assert len(logger.sheet.rows) == 3, 'appended a second orphan row'


def test_three_leg_close_does_not_match_the_row_as_a_whole_close(trades, notes):
    """
    The three strikes are a prefix of the row's four, so a substring match would
    read this as a complete close and book it at the wrong price.
    """
    _, three_leg, _ = trades
    logger = make_logger(notes)

    assert logger._close_matching_open_rows(three_leg)[0] == 'no_match'
    assert logger.sheet.rows[1][4] == 'Open'


def test_unrelated_close_is_left_to_the_normal_path(trades, notes):
    _, three_leg, _ = trades
    logger = make_logger(notes)

    other = dict(three_leg, underlying='SPX')
    assert logger._convert_four_leg_orphan_close(other) == (False, False)
    assert logger.errors == []


def test_partial_quantity_refuses_rather_than_guessing(trades, notes):
    """Closing 2 of 4 leaves part of every leg open - unrepresentable."""
    _, three_leg, _ = trades
    logger = make_logger(notes)

    assert logger._convert_four_leg_orphan_close(
        dict(three_leg, quantity=2)) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert len(logger.sheet.rows) == 2
    assert 'Partial legged-out close' in logger.errors[0]


def test_hand_repaired_row_is_recognised_without_leg_prices(trades):
    """
    An old row split by hand carries the marker but never had per-leg prices.
    The next sync still sees these closing orders in its lookback window, and
    must recognise the repair rather than file the same errors again.
    """
    _, three_leg, _ = trades
    logger = make_logger(f"Strikes: {FOUR_STRIKES} | legged out 10/14/2026 -> row 9")

    assert logger._convert_four_leg_orphan_close(three_leg) == (True, True)
    assert logger.errors == []
    assert len(logger.sheet.rows) == 2, 'appended a row for an existing repair'


def test_row_without_recorded_leg_prices_refuses(trades):
    """Rows predating per-leg tracking can't be split - say so, don't guess."""
    _, three_leg, _ = trades
    logger = make_logger(f"Strikes: {FOUR_STRIKES}")

    assert logger._convert_four_leg_orphan_close(three_leg) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert 'no per-leg prices' in logger.errors[0]
