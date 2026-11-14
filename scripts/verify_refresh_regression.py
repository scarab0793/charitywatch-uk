#!/usr/bin/env python3
"""Refuse publication when an official refresh unexpectedly loses large coverage.

The previous verified manifest is saved before the import overwrites it.
Thresholds are conservative: a drop of more than 10% needs investigation,
not silent publication. No external dependencies or network requests.
"""
import argparse
import json
import sys
from pathlib import Path

METRICS = (
    "count",
    "financial_records",
    "annual_return_part_a_records",
    "annual_return_part_b_records",
    "salary_band_reporting_charities",
    "word_index_records",
)
MAX_DROP = 0.10


def validate(before, after, max_drop=MAX_DROP):
    errors = []
    report = {}
    for key in METRICS:
        previous = before.get(key)
        current = after.get(key)
        if not isinstance(previous, int) or previous <= 0:
            errors.append(f"{key}: missing or invalid previous verified count")
            continue
        if not isinstance(current, int) or current < 0:
            errors.append(f"{key}: missing or invalid updated count")
            continue
        ratio = current / previous
        report[key] = {"previous": previous, "updated": current, "retained": round(ratio * 100, 2)}
        if ratio < 1 - max_drop:
            errors.append(f"{key}: dropped {100*(1-ratio):.2f}% ({previous:,} -> {current:,})")
    if after.get("word_index_records") != after.get("count"):
        errors.append("word search coverage does not equal total charity count")
    return errors, report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--max-drop", type=float, default=MAX_DROP)
    args = parser.parse_args()
    if not 0 <= args.max_drop < 1:
        parser.error("--max-drop must be in [0,1)")
    before = json.loads(args.before.read_text(encoding="utf-8"))
    after = json.loads(args.after.read_text(encoding="utf-8"))
    errors, report = validate(before, after, args.max_drop)
    for key, record in report.items():
        print(f"{key}: {record['previous']:,} -> {record['updated']:,} ({record['retained']:.2f}% retained)")
    if errors:
        print("FAIL: refusing publication due to apparent data loss", file=sys.stderr)
        for error in errors:
            print("  " + error, file=sys.stderr)
        return 1
    print("PASS: no major coverage regression after official charity refresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
