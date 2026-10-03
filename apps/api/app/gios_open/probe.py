"""Operator's evidence probe for ONE operation of the new GIOŚ API (ADR-032, closes blocker B-6).

The agent environment cannot reach dane.gios.gov.pl, so the questions that block `APPROVED`
(does `liczbaRekordow` mean a total? what does a page past the end look like? is the order stable
across page sizes? does paging repeat or overlap?) are answered by running this on a machine
WITH network access (your computer or the VPS). It writes nothing to the database.

    docker compose exec api python -m app.gios_open.probe \\
        --service halas --path /v1/pomiar-halasu-w-srodowisku \\
        --param kategoria=Droga --param wojewodztwo=ŚLĄSKIE \\
        --param dataOd=2024-01-01 --param dataDo=2024-12-31 \\
        --walk-pages 40 --out /tmp/halas-probe.json

It sends about 5 requests plus at most `--walk-pages` more, one per GIOS_OPEN_MIN_INTERVAL_SECONDS
(default 5 s) - never in parallel. Paste the JSON (or the file) into the PR / Source Registry.
"""

import argparse
import json
import logging
import sys
from typing import Any

from app.gios_open.client import GiosOpenClient, Page
from app.gios_open.errors import GiosOpenError
from app.gios_open.paging import PAGE_PARAM, SIZE_PARAM, iter_pages, page_hash

FAR_PAGE = 99999  # the spec maximum of numerStrony
MAX_SIZE = 50


def _describe(page: Page) -> dict[str, Any]:
    return {
        "records": len(page.records),
        "reported_count": page.reported_count,
        "empty_observed": page.empty_observed,
        "has_strona_key": isinstance(page.raw.get("dane"), dict) and "strona" in page.raw["dane"],
        "hash": page_hash(page.records) if page.records else None,
    }


def _step(
    client: GiosOpenClient, path: str, params: dict, number: int, size: int
) -> tuple[dict, Page | None]:
    try:
        page = client.get_page(path, {**params, PAGE_PARAM: number, SIZE_PARAM: size})
    except GiosOpenError as exc:  # a failing step is evidence too, never a crash
        return {"error": f"{type(exc).__name__}: {exc}"}, None
    return _describe(page), page


def run_probe(
    client: GiosOpenClient,
    path: str,
    params: dict[str, Any],
    *,
    small: int = 3,
    walk_pages: int = 0,
) -> dict[str, Any]:
    """Pure over the client: returns the report dict (tests stub the client)."""
    report: dict[str, Any] = {
        "service": client.service,
        "path": path,
        "params": params,
        "small_size": small,
    }
    steps: dict[str, Any] = {}
    s0, p0 = _step(client, path, params, 0, small)
    s1, p1 = _step(client, path, params, 1, small)
    s0b, p0b = _step(client, path, params, 0, small)
    big, pbig = _step(client, path, params, 0, MAX_SIZE)
    far, _ = _step(client, path, params, FAR_PAGE, small)
    steps.update(
        {
            "page0_small": s0,
            "page1_small": s1,
            "page0_small_again": s0b,
            "page0_size_max": big,
            "page_far_beyond_end": far,
        }
    )
    if p0 is not None and p0.records:
        steps["first_record_sample"] = p0.records[0]
    report["steps"] = steps

    obs: dict[str, Any] = {}
    if p0 is not None and p0b is not None:
        obs["same_page_is_stable"] = page_hash(p0.records) == page_hash(p0b.records)
    if p0 is not None and p1 is not None and p0.records and p1.records:
        obs["page1_repeats_page0"] = page_hash(p0.records) == page_hash(p1.records)
        obs["page1_overlaps_page0"] = any(r in p0.records for r in p1.records)
    if p0 is not None and pbig is not None and p0.records:
        obs["order_is_consistent_across_page_sizes"] = pbig.records[: len(p0.records)] == p0.records
    if pbig is not None:
        obs["reported_count_equals_page_length"] = (
            pbig.reported_count == len(pbig.records) if pbig.reported_count is not None else None
        )
        obs["reported_count_exceeds_page_length"] = (
            pbig.reported_count > len(pbig.records) if pbig.reported_count is not None else None
        )
    report["observations"] = obs

    if walk_pages > 0:
        lengths: list[int] = []
        walk: dict[str, Any] = {"max_pages": walk_pages}
        try:
            for _n, page in iter_pages(
                client, path, params, page_size=MAX_SIZE, max_pages=walk_pages
            ):
                lengths.append(len(page.records))
            walk["completed"] = True  # a confirmed empty page ended the pass
        except GiosOpenError as exc:
            walk["completed"] = False
            walk["stopped_by"] = f"{type(exc).__name__}: {exc}"
        walk.update(
            {
                "page_lengths": lengths,
                "total_records": sum(lengths),
                "last_page_short": bool(lengths) and lengths[-1] < MAX_SIZE,
            }
        )
        report["walk"] = walk
    return report


def _parse_params(items: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--param must look like name=value, got {item!r}")
        name, value = item.split("=", 1)
        params[name] = value
    return params


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Evidence probe for one GIOŚ open-data operation.")
    parser.add_argument("--service", required=True, help="e.g. halas, prtr, powazne-awarie, nec")
    parser.add_argument("--path", required=True, help="e.g. /v1/pomiar-halasu-w-srodowisku")
    parser.add_argument("--param", action="append", default=[], help="name=value (repeatable)")
    parser.add_argument("--small", type=int, default=3, help="small page size for the comparisons")
    parser.add_argument("--walk-pages", type=int, default=0, help="walk up to N pages of 50")
    parser.add_argument("--out", help="also write the JSON report to this file")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    report = run_probe(
        GiosOpenClient(args.service),
        args.path,
        _parse_params(args.param),
        small=args.small,
        walk_pages=args.walk_pages,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    sys.exit(0)


if __name__ == "__main__":
    main()
