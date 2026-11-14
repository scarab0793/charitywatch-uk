#!/usr/bin/env python3
"""Check that independently refreshed CharityWatch datasets agree before publishing.

Dependency-free and deterministic. Does not fetch live sources or modify files.
"""
import json
import sys
from pathlib import Path


def load(path):
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main():
    root = Path("data")
    manifest = load(root / "manifest-ew.json")
    expected = manifest.get("count", 0)
    assert expected >= 100000, "Official registry is incomplete"
    assert 100000 <= manifest.get("financial_records", 0) <= expected, "Invalid financial coverage"
    assert 10000 <= manifest.get("annual_return_part_a_records", 0) <= expected, "Part A missing"
    assert 10000 <= manifest.get("annual_return_part_b_records", 0) <= expected, "Part B missing"

    for field, directory in [
        ("shards", root / "ew"),
        ("number_shards", root / "ew" / "numbers"),
        ("salary_shards", root / "pay" / "ew"),
        ("word_shards", root / "words" / "ew"),
    ]:
        names = manifest.get(field)
        assert isinstance(names, list) and names, f"Missing manifest index: {field}"
        for prefix in names:
            assert isinstance(prefix, str) and prefix, f"Invalid shard name in {field}"
            assert (directory / f"{prefix}.json").is_file(), f"Missing {field} file: {prefix}"
        print(f"{field}: {len(names)} shard files verified")

    grants = load(root / "grant-makers-ew.json")
    meta = load(root / "grant-makers-meta-ew.json")
    records = grants.get("records", [])
    assert isinstance(records, list), "Invalid grant records"
    assert grants.get("record_count") == len(records), "Grant count does not match published list"
    assert meta.get("record_count") == len(records), "Grant metadata out of sync"
    assert len(records) >= 200, "Implausible grant data coverage"
    actual_total = 0
    years = {}
    seen = set()
    for item in records:
        reg = str(item.get("number", ""))
        value = item.get("grants_to_institutions")
        date = str(item.get("period_end", ""))
        assert reg and reg not in seen, f"Invalid or duplicate grantmaker: {reg}"
        assert type(value) in (int, float) and 0 < value < 1e14, f"Invalid grant value: {reg}"
        assert len(date) >= 10 and date[4] == "-", f"Invalid grant period: {reg}"
        seen.add(reg)
        actual_total += value
        year = date[:4]
        years[year] = years.get(year, 0) + 1
    assert years == meta.get("year_end_counts"), "Grant reporting-year counts disagree"
    reported_total = meta.get("total_reported_across_distinct_periods")
    assert type(reported_total) in (int, float) and abs(actual_total-reported_total) < 0.01, "Grant totals disagree"
    print(f"CCEW register: {expected:,} charity records, {manifest['financial_records']:,} with financials")
    print(f"Part A: {manifest['annual_return_part_a_records']:,} records; Part B: {manifest['annual_return_part_b_records']:,} records")
    print(f"Institutional grant makers: {len(records):,}; yearly metadata and totals agree")
    print("PASS: all published data indices, grant metadata and financial coverage are consistent")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, FileNotFoundError, ValueError, KeyError, TypeError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        sys.exit(1)
