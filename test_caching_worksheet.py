"""
Tests for the worksheet wrapper that keeps a sync inside the Sheets read quota.

Every matching pass re-reads the whole grid and a sync does several per trade,
so a full lookback window ran to a few hundred reads. On 2026-10-15 a
production run went over the per-minute read quota part-way through: some
trades were written, some were not, and the run never reached its own Sync Log
row. Reads are now served from one copy per worksheet, dropped whenever a call
could have changed the grid, and whatever still hits the quota waits instead of
dying.
"""
from types import SimpleNamespace

import gspread
import pytest

from spreadsheet_logger import _CachingWorksheet


class FakeWorksheet:
    """Counts reads, and can be told to hit the quota a few times first."""

    def __init__(self, rows=None, quota_failures=0):
        self.rows = rows if rows is not None else [['a', 'b']]
        self.reads = 0
        self.quota_failures = quota_failures
        self.writes = []
        self.id = 7
        self.title = 'Fake'

    def _maybe_quota(self):
        if self.quota_failures:
            self.quota_failures -= 1
            raise quota_error()

    def get_all_values(self, value_render_option=None):
        self._maybe_quota()
        self.reads += 1
        return [list(r) for r in self.rows]

    def update_acell(self, cell, value):
        self.writes.append(('update_acell', cell, value))

    def append_row(self, values):
        self.writes.append(('append_row', values))
        self.rows.append(list(values))

    def format(self, *args, **kwargs):
        self.writes.append(('format',))


def quota_error():
    """An APIError shaped the way Sheets reports being over quota."""
    response = SimpleNamespace(
        status_code=429,
        text='quota exceeded',
        json=lambda: {'error': {'code': 429, 'status': 'RESOURCE_EXHAUSTED',
                                'message': 'Quota exceeded'}},
    )
    return gspread.exceptions.APIError(response)


def not_found_error():
    """A different APIError, which must not be retried."""
    response = SimpleNamespace(
        status_code=404,
        text='not found',
        json=lambda: {'error': {'code': 404, 'status': 'NOT_FOUND',
                                'message': 'Not found'}},
    )
    return gspread.exceptions.APIError(response)


def test_the_grid_is_read_once():
    inner = FakeWorksheet()
    ws = _CachingWorksheet(inner)

    for _ in range(5):
        ws.get_all_values()

    assert inner.reads == 1


def test_a_write_drops_the_cached_grid():
    inner = FakeWorksheet()
    ws = _CachingWorksheet(inner)

    ws.get_all_values()
    ws.update_acell('A1', 'changed')
    ws.get_all_values()

    assert inner.reads == 2, 'served a stale grid after a write'


def test_an_appended_row_is_visible_immediately():
    """The dangerous staleness: a row written and then read back."""
    inner = FakeWorksheet(rows=[['one']])
    ws = _CachingWorksheet(inner)

    assert ws.get_all_values() == [['one']]
    ws.append_row(['two'])
    assert ws.get_all_values() == [['one'], ['two']]


def test_formatting_does_not_drop_the_cache():
    """Formatting changes how cells look, not what they say."""
    inner = FakeWorksheet()
    ws = _CachingWorksheet(inner)

    ws.get_all_values()
    ws.format('A1:B1', {'textFormat': {'bold': True}})
    ws.get_all_values()

    assert inner.reads == 1


def test_reads_with_arguments_are_never_cached():
    """A different render option is a different question - answer it freshly."""
    inner = FakeWorksheet()
    ws = _CachingWorksheet(inner)

    ws.get_all_values(value_render_option='FORMULA')
    ws.get_all_values(value_render_option='FORMULA')

    assert inner.reads == 2


def test_hitting_the_quota_waits_and_retries(monkeypatch):
    slept = []
    monkeypatch.setattr('spreadsheet_logger.time.sleep', slept.append)

    inner = FakeWorksheet(quota_failures=2)
    ws = _CachingWorksheet(inner, attempts=4, delay=20)

    assert ws.get_all_values() == [['a', 'b']]
    assert slept == [20, 40], 'expected a lengthening wait between attempts'
    assert inner.reads == 1


def test_giving_up_raises_rather_than_returning_nothing(monkeypatch):
    """A caller that got None back would read it as an empty sheet."""
    monkeypatch.setattr('spreadsheet_logger.time.sleep', lambda _: None)

    inner = FakeWorksheet(quota_failures=99)
    ws = _CachingWorksheet(inner, attempts=3, delay=1)

    with pytest.raises(gspread.exceptions.APIError):
        ws.get_all_values()


def test_other_api_errors_are_not_retried(monkeypatch):
    monkeypatch.setattr('spreadsheet_logger.time.sleep', lambda _: None)

    inner = FakeWorksheet()
    inner.get_all_values = lambda *a, **k: (_ for _ in ()).throw(not_found_error())
    ws = _CachingWorksheet(inner, attempts=4, delay=1)

    with pytest.raises(gspread.exceptions.APIError) as caught:
        ws.get_all_values()
    assert caught.value.response.status_code == 404


def test_plain_attributes_pass_through():
    ws = _CachingWorksheet(FakeWorksheet())
    assert ws.id == 7
    assert ws.title == 'Fake'


def test_the_cache_is_not_shared_between_worksheets():
    first, second = FakeWorksheet(rows=[['x']]), FakeWorksheet(rows=[['y']])

    assert _CachingWorksheet(first).get_all_values() == [['x']]
    assert _CachingWorksheet(second).get_all_values() == [['y']]
