"""
Tests for the superbull: a bull call spread and a bull put spread held together.

Like an iron condor it is four legs on one row, but its call side is a debit
spread rather than a credit one, so the position can open for either a net
credit or a net debit and each side has to be tracked with its own sign. Either
spread can also be taken off on its own, leaving the other running.

The fixture is a NOW 09/18/26 superbull, 2 contracts, opened 8/25/2026 for a
$198.96 net debit (145/150 calls bought for $374.48, 115/110 puts sold for
$175.52), with three alternative exits on 8/31/2026: the call spread alone
(+$495.52), the put spread alone (-$44.48), and all four legs at once
(+$451.04).
"""
import json
from pathlib import Path

import pytest

from spreadsheet_logger import SpreadsheetLogger
from transaction_processor import TransactionProcessor
from test_ic_side_close import HEADER, StubSheet

FIXTURE = Path(__file__).parent / 'evals' / 'inputs' / 'superbull_now.json'

FOUR_STRIKES = '$150.00/$145.00/$115.00/$110.00'
CALL_STRIKES = '$150.00/$145.00'
PUT_STRIKES = '$115.00/$110.00'


@pytest.fixture(scope='module')
def trades():
    """The open and its three alternative exits, keyed by what they close."""
    processor = TransactionProcessor()
    processor.load_transactions(json.loads(FIXTURE.read_text()))
    processed = processor.process_orders()

    by_strikes = {t['strikes']: t for t in processed if t['action'] == 'CLOSE'}
    return {
        'open': next(t for t in processed if t['action'] == 'OPEN'),
        'call_exit': by_strikes[CALL_STRIKES],
        'put_exit': by_strikes[PUT_STRIKES],
        'full_exit': by_strikes[FOUR_STRIKES],
    }


@pytest.fixture
def notes(trades):
    """The Notes cell the logger writes when this superbull is opened."""
    return SpreadsheetLogger('stub')._four_leg_notes(
        trades['open']['strikes'], trades['open']['side_breakdown'])


def make_logger(notes, contracts='2'):
    logger = SpreadsheetLogger('stub')
    logger.sheet = StubSheet([
        HEADER,
        ['8/25/2026', '', 'NOW', 'Superbull', 'Open', '9/18/2026', '', '', '',
         '$8.96', '-$198.96', '', contracts, '', '', notes],
    ])
    logger.errors = []
    logger.log_error = lambda trade, msg: logger.errors.append(msg)
    return logger


def test_a_long_call_side_makes_it_a_superbull_not_a_condor(trades):
    """The call vertical is the whole difference: long below short, not short
    below long."""
    assert trades['open']['strategy'] == 'Superbull'
    assert trades['open']['strikes'] == FOUR_STRIKES


def test_it_can_open_for_a_net_debit(trades):
    """The call debit outweighs the put credit here, so the position is a debit."""
    assert trades['open']['net_price'] == pytest.approx(-198.96, abs=0.01)


def test_each_side_is_recorded_with_its_own_sign(trades):
    sides = trades['open']['side_breakdown']

    assert sides['C']['strikes'] == CALL_STRIKES
    assert sides['C']['net_price'] == pytest.approx(-374.48, abs=0.01)
    assert sides['P']['strikes'] == PUT_STRIKES
    assert sides['P']['net_price'] == pytest.approx(175.52, abs=0.01)
    assert sides['C']['net_price'] + sides['P']['net_price'] == \
        pytest.approx(trades['open']['net_price'])


def test_notes_round_trip_a_debit_side(notes):
    assert notes.startswith(f"Strikes: {FOUR_STRIKES}")
    assert 'Call side: $150.00/$145.00 debit $374.48' in notes

    sides = SpreadsheetLogger._parse_side_notes(notes)
    assert sides['Call'] == {'strikes': CALL_STRIKES, 'net_price': -374.48}
    assert sides['Put'] == {'strikes': PUT_STRIKES, 'net_price': 175.52}


def test_closing_all_four_legs_matches_the_open_row(trades, notes):
    """A whole exit is an ordinary CLOSE - it just matches on the strikes in
    Notes, the way four-leg rows always have."""
    full_exit = trades['full_exit']
    assert full_exit['strategy'] == 'Superbull'

    logger = make_logger(notes)
    assert logger.find_all_open_trades(full_exit) == [2]

    assert logger._close_matching_open_rows(full_exit) == ('closed', (1, 1))
    row = logger.sheet.rows[1]
    assert row[4] == 'Closed'
    assert float(row[13]) == pytest.approx(-198.96 + 451.04, abs=0.01)


def test_closing_the_call_spread_realises_only_that_spread(trades, notes):
    logger = make_logger(notes)
    assert logger._convert_four_leg_side_close(trades['call_exit']) == (True, True)

    row = logger.sheet.rows[1]
    assert row[4] == 'Closed'
    assert row[1] == '8/31/2026'

    # The put credit is carried out alongside the real call proceeds, so the
    # row realises the call spread's P&L and nothing else.
    assert float(row[11]) == pytest.approx(495.52 - 175.52, abs=0.01)
    assert float(row[13]) == pytest.approx(495.52 - 374.48, abs=0.02)


def test_closing_the_call_spread_leaves_a_bull_put_spread(trades, notes):
    logger = make_logger(notes)
    logger._convert_four_leg_side_close(trades['call_exit'])

    survivor = logger.sheet.rows[2]
    assert survivor[2:8] == ['NOW', 'Bull Put Spread', 'Open', '9/18/2026',
                             '$115.00', '$110.00']
    assert survivor[0] == '8/25/2026'
    assert float(survivor[10]) == pytest.approx(175.52, abs=0.01)
    assert survivor[12] == 2


def test_closing_the_put_spread_realises_only_that_spread(trades, notes):
    logger = make_logger(notes)
    assert logger._convert_four_leg_side_close(trades['put_exit']) == (True, True)

    row = logger.sheet.rows[1]
    assert row[4] == 'Closed'
    # The call side left as a debit, so carrying it out ADDS to the closing
    # price rather than subtracting from it.
    assert float(row[11]) == pytest.approx(-44.48 + 374.48, abs=0.01)
    assert float(row[13]) == pytest.approx(175.52 - 44.48, abs=0.02)


def test_closing_the_put_spread_leaves_a_bull_call_spread(trades, notes):
    """The survivor is a debit spread, and opens holding what it cost."""
    logger = make_logger(notes)
    logger._convert_four_leg_side_close(trades['put_exit'])

    survivor = logger.sheet.rows[2]
    assert survivor[2:8] == ['NOW', 'Bull Call Spread', 'Open', '9/18/2026',
                             '$150.00', '$145.00']
    assert float(survivor[10]) == pytest.approx(-374.48, abs=0.01)


@pytest.mark.parametrize('exit_side', ['call_exit', 'put_exit'])
def test_the_two_rows_sum_to_the_real_total(trades, notes, exit_side):
    logger = make_logger(notes)
    logger._convert_four_leg_side_close(trades[exit_side])

    realised = float(logger.sheet.rows[1][13])
    carried = float(logger.sheet.rows[2][10])
    assert realised + carried == pytest.approx(
        trades['open']['net_price'] + trades[exit_side]['net_price'], abs=0.02)


def test_rerun_does_not_convert_twice(trades, notes):
    logger = make_logger(notes)
    logger._convert_four_leg_side_close(trades['call_exit'])

    assert logger._convert_four_leg_side_close(trades['call_exit']) == (True, True)
    assert len(logger.sheet.rows) == 3, 'appended a second survivor row'


def test_partial_side_close_refuses_rather_than_guessing(trades, notes):
    logger = make_logger(notes)
    partial = dict(trades['call_exit'], quantity=1)

    assert logger._convert_four_leg_side_close(partial) == (True, False)
    assert logger.sheet.rows[1][4] == 'Open'
    assert len(logger.sheet.rows) == 2
    assert 'Partial side close: Superbull' in logger.errors[0]


def test_the_open_row_keeps_all_four_strikes_in_notes(trades):
    """Four strikes don't fit two columns, so they live in Notes - and the
    opening net price carries the debit's sign into the P&L column."""
    row = SpreadsheetLogger('stub').format_trade_row(trades['open'])

    assert row[3] == 'Superbull'
    assert (row[6], row[7]) == ('', '')
    assert row[10] == pytest.approx(-198.96, abs=0.01)
    assert row[15].startswith(f"Strikes: {FOUR_STRIKES}")
    assert 'Call side: $150.00/$145.00 debit $374.48' in row[15]


def test_a_rolled_superbull_still_records_its_strikes(trades):
    """A roll leaves the row holding the new position, which must stay
    matchable - whole or one side at a time."""
    roll = {
        'action': 'ROLL',
        'underlying': 'NOW',
        'new_strategy': 'Superbull',
        'new_expiration': '10/16/2026',
        'new_strikes': trades['open']['strikes'],
        'side_breakdown': trades['open']['side_breakdown'],
        'trade_date': '9/5/2026',
        'quantity': 2,
        'fees': 8.96,
        'open_net_price': -198.96,
        'roll_credit': 25.0,
    }
    row = SpreadsheetLogger('stub').format_trade_row(roll)

    assert (row[6], row[7]) == ('', '')
    assert row[15].startswith(f"Strikes: {FOUR_STRIKES}")
    assert 'Put side: $115.00/$110.00 credit $175.52' in row[15]
    assert 'Roll credit: $25.00' in row[15]


def test_append_trade_routes_a_side_exit_through_the_conversion(trades, notes):
    """End to end: a 2-leg exit with no open row of its own is a conversion,
    not an import error."""
    logger = make_logger(notes)

    assert logger.append_trade(trades['put_exit']) is True
    assert logger.sheet.rows[1][4] == 'Closed'
    assert logger.sheet.rows[2][3] == 'Bull Call Spread'
    assert logger.errors == []


def test_a_whole_exit_is_never_mistaken_for_a_side_exit(trades):
    """A four-leg close that fails to match is an ordinary import error - not a
    side close of a row that merely lists those four strikes."""
    logger = make_logger(f"Strikes: {FOUR_STRIKES}")  # legacy row, no side data

    assert logger._convert_four_leg_side_close(trades['full_exit']) == (False, False)
    assert logger.errors == []
