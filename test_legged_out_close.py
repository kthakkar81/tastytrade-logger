"""
Tests for a position legged out of - closed a leg or two at a time, across
several orders, rather than as a whole structure or one whole side.

Closing one whole side of a four-legger is handled separately (see
test_ic_side_close.py). This is the messier case: the legs come off in whatever
groups the orders happened to fill in, so no single order matches the row.
Each closing order is reconciled against just the legs it covers - the row is
rewritten to hold those legs alone, and every surviving leg is split out to a
row of its own. Both price columns of every row then hold figures that actually
traded, which is what makes them reconcilable against a broker statement.

Two real positions, both unwound this way:

IREN 10/30/26 superbull, opened 10/12/2026 for a $90.05 net credit (46/45 calls
+ 33/32 puts, 4 contracts). Unwound 10/14 across two orders - 46C/45C/33P
together for a $1,193.48 debit, then the long 32P alone for a $1,299.49 credit.
True total +$196.06.

DRAM 11/20/26 55/54 bull put spread, opened 10/8/2026 for a $347.54 net credit
(10 contracts). The short 55P was bought back on 10/14 for a $6,001.20 debit
and the long 54P sold on 10/15 for an $8,498.62 credit - the long leg ran on
alone in between, and rescued the trade. True total +$2,844.96.
"""
import json
from pathlib import Path

import pytest

from spreadsheet_logger import SpreadsheetLogger
from transaction_processor import TransactionProcessor

INPUTS = Path(__file__).parent / 'evals' / 'inputs'

HEADER = ['Opening Date', 'Closing Date', 'Underlying', 'Strategy Type', 'Status',
          'Expiration', 'Short/CSP/CC Strike', 'Long Strike', 'Delta', 'Fees',
          'Opening Net Price', 'Closing Net Price (debit)', 'Contracts',
          'Total PnL ($)', 'ROC', 'Notes/Setup', 'Legs']

FOUR_STRIKES = '$46.00/$45.00/$33.00/$32.00'


class StubSheet:
    """
    Minimal stand-in for a gspread worksheet, recording what gets written.

    Reads come back as strings, the way the real API hands back every cell
    whatever was written into it - the logger parses its own numbers back out
    of them, so a stub that returned live floats would hide that work.
    `rows` keeps the raw written values for assertions.
    """

    WIDTH = 17

    def __init__(self, rows):
        self.rows = [self._pad(r) for r in rows]

    def _pad(self, row):
        return list(row) + [''] * (self.WIDTH - len(row))

    def get_all_values(self):
        return [[str(c) for c in r] for r in self.rows]

    def row_values(self, n):
        return [str(c) for c in self.rows[n - 1]]

    def batch_update(self, updates, value_input_option=None):
        for update in updates:
            cell = update['range']
            self.rows[int(cell[1:]) - 1][ord(cell[0]) - 65] = update['values'][0][0]

    def update(self, values=None, range_name=None, value_input_option=None):
        self.rows.append(self._pad(values[0]))

    def insert_row(self, values, index, value_input_option=None):
        self.rows.insert(index - 1, self._pad(values))

    def update_acell(self, cell, value):
        self.rows[int(cell[1:]) - 1][ord(cell[0]) - 65] = value

    def format(self, *args, **kwargs):
        pass

    def batch_format(self, *args, **kwargs):
        pass


def load(name, *leg_groups):
    """
    A fixture's open trade, plus the closing order covering each strike group.

    Orders are picked by the strikes they cover rather than by leg count: a
    legged-out position can produce several one-leg orders - DRAM's two closes
    are both single legs, and telling them apart is the whole point.
    """
    processor = TransactionProcessor()
    processor.load_transactions(json.loads((INPUTS / f'{name}.json').read_text()))
    processed = processor.process_orders()

    closes = [t for t in processed if t['action'] == 'CLOSE']
    picked = [next(t for t in closes
                   if {leg['strike'] for leg in t['leg_breakdown']} == set(group))
              for group in leg_groups]
    return (next(t for t in processed if t['action'] == 'OPEN'), *picked)


def make_logger(open_trade, **overrides):
    """
    A sheet holding just this position's open row.

    The row is built with the logger's own format_trade_row, so the per-leg
    column under test is the one the logger would really have written.
    """
    logger = SpreadsheetLogger('stub')
    row = logger.format_trade_row(open_trade)
    for col, value in overrides.items():
        row['ABCDEFGHIJKLMNOPQ'.index(col)] = value
    logger.sheet = StubSheet([HEADER, row])
    logger.errors = []
    logger.log_error = lambda trade, msg: logger.errors.append(msg)
    return logger


@pytest.fixture(scope='module')
def iren():
    """(open, the 46C/45C/33P close, the lone long 32P close)"""
    return load('legged_out_iren', (46.0, 45.0, 33.0), (32.0,))


@pytest.fixture(scope='module')
def dram():
    """(open, the short 55P close, the long 54P close)"""
    return load('legged_out_dram', (55.0,), (54.0,))


# --- the per-leg column -----------------------------------------------------

def test_leg_column_accounts_for_the_whole_position(iren):
    open_trade, _, _ = iren
    row = SpreadsheetLogger('stub').format_trade_row(open_trade)

    legs = SpreadsheetLogger._parse_leg_cell(row[16])
    assert set(legs) == {(45.0, 'C'), (46.0, 'C'), (33.0, 'P'), (32.0, 'P')}
    # The legs are the position: they must account for all of its price and fees.
    assert sum(l['net_price'] for l in legs.values()) == pytest.approx(
        open_trade['net_price'], abs=0.01)
    assert sum(l['fees'] for l in legs.values()) == pytest.approx(
        open_trade['fees'], abs=0.01)


def test_leg_prices_stay_out_of_notes(iren):
    """Notes/Setup is Kevin's; logger per-leg bookkeeping lives in its own column."""
    open_trade, _, _ = iren
    row = SpreadsheetLogger('stub').format_trade_row(open_trade)

    assert ' fee $' not in row[15]
    assert ' fee $' in row[16]


def test_single_leg_position_carries_no_leg_column():
    """A one-leg position has nothing to split, so nothing to record."""
    row = SpreadsheetLogger('stub').format_trade_row({
        'action': 'OPEN', 'underlying': 'DELL', 'strategy': 'CSP',
        'trade_date': '10/13/2026', 'expiration': '11/20/2026',
        'strikes': '$120.00P', 'quantity': 1, 'net_price': 250.0, 'fees': 1.15,
    })
    assert len(row) == 16


# --- IREN: three legs closed, one left running ------------------------------

def test_three_leg_close_is_classified_not_abandoned(iren):
    """It used to land in Import Errors as 'Unknown' and stop there."""
    _, three_leg, _ = iren
    assert three_leg['strategy'] == 'Super Bull'
    assert three_leg['strikes'] == '$46.00/$45.00/$33.00'
    assert three_leg['net_price'] == pytest.approx(-1193.48, abs=0.01)


def test_row_is_rewritten_to_hold_just_the_closed_legs(iren):
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade)

    assert logger._convert_legged_out_close(three_leg) == (True, True)

    parent = logger.sheet.rows[1]
    assert parent[4] == 'Closed'
    assert parent[1] == '10/14/2026'
    # Both figures are real: the three legs' own opening credit, and the debit
    # the closing order actually paid.
    assert float(parent[10]) == pytest.approx(454.53, abs=0.01)
    assert float(parent[11]) == pytest.approx(-1193.48, abs=0.01)
    assert float(parent[13]) == pytest.approx(-738.95, abs=0.02)
    # Three legs have no name of their own in the log, so the label stands.
    assert parent[3] == 'Super Bull'


def test_surviving_leg_is_split_out_directly_below(iren):
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade)
    logger._convert_legged_out_close(three_leg)

    survivor = logger.sheet.rows[2]
    # A bought leg is a long Put, so its strike belongs in the long column.
    assert survivor[2:8] == ['IREN', 'Put', 'Open', '10/30/2026', '', '$32.00']
    # Keeps the superbull's entry date - that is when the risk went on.
    assert survivor[0] == '10/12/2026'
    assert float(survivor[10]) == pytest.approx(-364.48, abs=0.01)
    assert survivor[12] == 4


def test_iren_rows_sum_to_the_real_total(iren):
    open_trade, three_leg, lone_put = iren
    logger = make_logger(open_trade)
    logger._convert_legged_out_close(three_leg)

    realised = float(logger.sheet.rows[1][13])
    carried = float(logger.sheet.rows[2][10])
    assert realised + carried == pytest.approx(
        open_trade['net_price'] + three_leg['net_price'], abs=0.02)

    # And once the survivor's own close lands, the pair realise the whole trade.
    assert realised + carried + lone_put['net_price'] == pytest.approx(
        196.06, abs=0.02)


def test_survivor_closes_through_the_ordinary_path(iren):
    """The point of splitting it out: no special handling for its own close."""
    open_trade, three_leg, lone_put = iren
    logger = make_logger(open_trade)
    logger._convert_legged_out_close(three_leg)

    assert logger._close_matching_open_rows(lone_put)[0] == 'closed'

    survivor = logger.sheet.rows[2]
    assert survivor[4] == 'Closed'
    assert float(survivor[13]) == pytest.approx(935.01, abs=0.02)


# --- DRAM: one leg of a vertical closed, the other left running --------------

def test_vertical_with_one_leg_closed_is_renamed_for_that_leg(dram):
    """
    The case that used to be unreachable: one leg of a two-leg spread. Follows
    the hand split in fix_msft_bps_321.py - the row becomes the short put it
    now accounts for, and the long strike that left is cleared.
    """
    open_trade, short_close, _ = dram
    logger = make_logger(open_trade)

    assert logger._convert_legged_out_close(short_close) == (True, True)

    parent = logger.sheet.rows[1]
    assert parent[3] == 'CSP'
    assert parent[4] == 'Closed'
    assert parent[6] == '$55.00'
    assert parent[7] == ''
    assert float(parent[10]) == pytest.approx(2458.74, abs=0.01)
    assert float(parent[11]) == pytest.approx(-6001.20, abs=0.01)
    assert float(parent[13]) == pytest.approx(-3542.46, abs=0.02)


def test_dram_long_leg_runs_on_and_then_closes(dram):
    open_trade, short_close, long_close = dram
    logger = make_logger(open_trade)
    logger._convert_legged_out_close(short_close)

    survivor = logger.sheet.rows[2]
    assert survivor[2:8] == ['DRAM', 'Put', 'Open', '11/20/2026', '', '$54.00']
    assert float(survivor[10]) == pytest.approx(-2111.20, abs=0.01)

    # Sold the next day, through the ordinary single-leg path.
    assert logger._close_matching_open_rows(long_close)[0] == 'closed'

    assert float(logger.sheet.rows[2][13]) == pytest.approx(6387.42, abs=0.02)
    assert float(logger.sheet.rows[1][13]) + float(logger.sheet.rows[2][13]) == \
        pytest.approx(2844.96, abs=0.02)


# --- refusals and re-runs ---------------------------------------------------

def test_rerun_does_not_split_twice(iren):
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade)
    logger._convert_legged_out_close(three_leg)

    assert logger._convert_legged_out_close(three_leg) == (True, True)
    assert len(logger.sheet.rows) == 3, 'split a second time'


def test_partial_close_does_not_match_the_row_as_a_whole_close(iren):
    """
    The three strikes are a prefix of the row's four, so a substring match would
    read this as a complete close and book it at the wrong price.
    """
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade)

    assert logger._close_matching_open_rows(three_leg)[0] == 'no_match'
    assert logger.sheet.rows[1][4] == 'Open'


def test_unrelated_close_is_left_to_the_normal_path(iren):
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade)

    assert logger._convert_legged_out_close(
        dict(three_leg, underlying='SPX')) == (False, False)
    assert logger.errors == []


def test_partial_quantity_refuses_rather_than_guessing(iren):
    """Closing 2 of 4 leaves part of every leg open - unrepresentable."""
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade)

    assert logger._convert_legged_out_close(
        dict(three_leg, quantity=2)) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert len(logger.sheet.rows) == 2
    assert 'Partial legged-out close' in logger.errors[0]


def test_row_without_recorded_leg_prices_refuses(iren):
    """Rows predating the leg column can't be split - say so, don't guess."""
    open_trade, three_leg, _ = iren
    logger = make_logger(open_trade, Q='')

    assert logger._convert_legged_out_close(three_leg) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert 'no per-leg prices' in logger.errors[0]


def test_hand_repaired_row_is_recognised_without_leg_prices(iren):
    """
    An old row split by hand carries the marker but never had per-leg prices.
    The next sync still sees these closing orders in its lookback window, and
    must recognise the repair rather than file the same errors again.
    """
    open_trade, three_leg, _ = iren
    logger = make_logger(
        open_trade, Q='',
        P=f"Strikes: {FOUR_STRIKES} | legged out 10/14/2026 -> row 9")

    assert logger._convert_legged_out_close(three_leg) == (True, True)
    assert logger.errors == []
    assert len(logger.sheet.rows) == 2, 'split an already-repaired row'
