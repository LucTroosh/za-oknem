"""Paging (ADR-032 pkt 9): a pass is complete only on a confirmed EMPTY page, and every way paging
can lie (repeat, overlap, no end) raises instead of yielding a partial result."""

from itertools import count

import pytest

from app.gios_open.client import Page
from app.gios_open.errors import (
    GiosOpenPageLimitError,
    GiosOpenPageLoopError,
    GiosOpenPageOverlapError,
    GiosOpenSourceError,
)
from app.gios_open.paging import PAGE_PARAM, SIZE_PARAM, iter_pages, page_hash


def _page(records):
    return Page(
        records=records,
        reported_count=len(records),
        empty_observed=not records,
        event_id=None,
        raw={},
    )


class FakeClient:
    """get_page(path, params) -> the page registered for params[numerStrony]; records the calls."""

    service = "halas"

    def __init__(self, pages, *, after=None):
        self.pages = pages  # list of record lists; beyond the end -> empty (unless `after`)
        self.after = after
        self.calls = []

    def get_page(self, path, params):
        self.calls.append((path, dict(params)))
        n = params[PAGE_PARAM]
        if n < len(self.pages):
            return _page(self.pages[n])
        if self.after is not None:
            return self.after(n)
        return _page([])


def recs(prefix, n):
    return [{"id": f"{prefix}{i}"} for i in range(n)]


def test_walks_until_a_confirmed_empty_page():
    c = FakeClient([recs("a", 3), recs("b", 3), recs("c", 1)])
    got = list(iter_pages(c, "/op", {"kategoria": "Droga"}, page_size=3))
    assert [n for n, _ in got] == [0, 1, 2]
    assert len(c.calls) == 4  # the final empty page was requested to confirm the end
    assert c.calls[0][1] == {"kategoria": "Droga", PAGE_PARAM: 0, SIZE_PARAM: 3}


def test_a_short_page_is_not_the_end():
    # "Short page = last page" is unconfirmed (B-6): we still ask for the next page.
    c = FakeClient([recs("a", 1), recs("b", 3)])
    assert [n for n, _ in iter_pages(c, "/op", page_size=3)] == [0, 1]
    assert len(c.calls) == 3


def test_empty_result_yields_nothing_and_is_complete():
    c = FakeClient([])
    assert list(iter_pages(c, "/op")) == []


def test_a_pager_that_does_not_advance_raises_instead_of_looping():
    c = FakeClient([], after=lambda n: _page(recs("a", 2)))  # every page is identical
    with pytest.raises(GiosOpenPageLoopError):
        list(iter_pages(c, "/op", max_pages=50))
    assert len(c.calls) == 2  # stopped at the first repeat


def test_overlapping_records_make_the_pass_inconsistent():
    c = FakeClient([[{"id": "x"}, {"id": "y"}], [{"id": "y"}, {"id": "z"}]])
    with pytest.raises(GiosOpenPageOverlapError):
        list(iter_pages(c, "/op", key_fn=lambda r: r["id"]))


def test_no_empty_page_within_max_pages_is_an_error_not_a_truncated_result():
    ids = count()
    c = FakeClient([], after=lambda n: _page([{"id": next(ids)}]))
    got = []
    with pytest.raises(GiosOpenPageLimitError):
        for item in iter_pages(c, "/op", max_pages=5):
            got.append(item)
    assert len(got) == 5  # callers see the pages, but the pass did NOT complete


def test_source_error_midway_propagates():
    def boom(n):
        raise GiosOpenSourceError("400", "x")

    c = FakeClient([recs("a", 2)], after=boom)
    it = iter_pages(c, "/op")
    next(it)
    with pytest.raises(GiosOpenSourceError):
        next(it)


def test_page_hash_is_order_and_content_sensitive_but_key_order_insensitive():
    assert page_hash([{"a": 1, "b": 2}]) == page_hash([{"b": 2, "a": 1}])
    assert page_hash([{"a": 1}, {"a": 2}]) != page_hash([{"a": 2}, {"a": 1}])
    assert page_hash([{"a": 1}]) != page_hash([{"a": 2}])
