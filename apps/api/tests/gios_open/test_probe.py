"""The operator's probe: pure over the client, so its conclusions are testable (ADR-032, B-6)."""

from app.gios_open.client import Page
from app.gios_open.errors import GiosOpenSourceError
from app.gios_open.paging import PAGE_PARAM, SIZE_PARAM
from app.gios_open.probe import FAR_PAGE, _parse_params, run_probe


def _page(records, count=None):
    raw = (
        {"dane": {"strona": records, "liczbaRekordow": len(records) if count is None else count}}
        if records
        else {"dane": {"liczbaRekordow": 0}}
    )
    return Page(
        records=records,
        reported_count=len(records) if count is None else count,
        empty_observed=not records,
        event_id=None,
        raw=raw,
    )


class FakeServer:
    """A well-behaved source with `total` records, ordered by id."""

    service = "halas"

    def __init__(self, total, *, far_error=False):
        self.data = [{"id": i} for i in range(total)]
        self.far_error = far_error
        self.calls = []

    def get_page(self, path, params):
        self.calls.append(params)
        n, size = params[PAGE_PARAM], params[SIZE_PARAM]
        if n == FAR_PAGE and self.far_error:
            raise GiosOpenSourceError("400", "numerStrony poza zakresem")
        return _page(self.data[n * size : (n + 1) * size])


def test_a_sane_source_is_reported_as_stable_and_reported_count_is_the_page_length():
    report = run_probe(FakeServer(120), "/op", {"kategoria": "Droga"}, small=3, walk_pages=10)
    obs = report["observations"]
    assert obs["same_page_is_stable"] is True
    assert obs["page1_repeats_page0"] is False and obs["page1_overlaps_page0"] is False
    assert obs["order_is_consistent_across_page_sizes"] is True
    assert obs["reported_count_equals_page_length"] is True  # not a total: 50 of 120
    assert obs["reported_count_exceeds_page_length"] is False
    walk = report["walk"]
    assert walk["completed"] is True and walk["total_records"] == 120
    assert walk["page_lengths"] == [50, 50, 20] and walk["last_page_short"] is True
    assert report["steps"]["page_far_beyond_end"]["empty_observed"] is True
    assert report["steps"]["first_record_sample"] == {"id": 0}


def test_a_pager_that_repeats_is_reported():
    class Repeating(FakeServer):
        def get_page(self, path, params):
            return _page(self.data[:3])

    report = run_probe(Repeating(10), "/op", {}, small=3, walk_pages=5)
    assert report["observations"]["page1_repeats_page0"] is True
    assert report["walk"]["completed"] is False and "PageLoop" in report["walk"]["stopped_by"]


def test_a_failing_step_is_evidence_not_a_crash():
    report = run_probe(FakeServer(5, far_error=True), "/op", {}, small=2)
    assert "GiosOpenSourceError" in report["steps"]["page_far_beyond_end"]["error"]
    assert report["steps"]["page0_small"]["records"] == 2


def test_unstable_order_across_sizes_is_detected():
    class Shuffling(FakeServer):
        def get_page(self, path, params):
            page = super().get_page(path, params)
            if params[SIZE_PARAM] == 50:
                return _page(list(reversed(page.records)))
            return page

    report = run_probe(Shuffling(10), "/op", {}, small=3)
    assert report["observations"]["order_is_consistent_across_page_sizes"] is False


def test_params_parsing():
    assert _parse_params(["a=1", "b=x=y"]) == {"a": "1", "b": "x=y"}
