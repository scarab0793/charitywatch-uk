#!/usr/bin/env python3
"""Fail early when one of the official Charity Commission extract ZIPs has changed.

Reads only the first TXT header and checks the schema expected by the actual
importers. Does not alter the published directory or log individual charities.
"""
import argparse
import csv
import io
import zipfile
from pathlib import Path

def columns(path: Path) -> set[str]:
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist()
                 if name.lower().endswith(".txt") and not name.startswith("__MACOSX")]
        if len(names) != 1:
            raise ValueError(f"{path.name}: expected exactly one TXT table, found {len(names)}")
        member = archive.getinfo(names[0])
        if member.file_size <= 0:
            raise ValueError(f"{path.name}: empty TXT table")
        with archive.open(names[0]) as raw:
            reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8-sig",
                                                 errors="replace", newline=""),
                                delimiter="\t")
            header = next(reader, [])
    if len(header) < 4:
        raise ValueError(f"{path.name}: missing or implausibly short TSV header")
    if len(header) != len(set(header)):
        raise ValueError(f"{path.name}: duplicate column headings")
    return {name.strip().lower() for name in header}

def any_of(header, choices, label):
    if not any(name in header for name in choices):
        raise ValueError(f"{label}: expected one of {', '.join(choices)}")

def check(charity, history, part_a, part_b):
    main = columns(charity)
    any_of(main, ("reg_charity_number", "reg_charity_no", "registered_charity_number",
                  "charity_number"), "Charity register ID")
    any_of(main, ("charity_name", "name"), "Charity register name")
    any_of(main, ("registered_charity_number", "reg_charity_number"), "Organisation mapping")
    any_of(main, ("organisation_number",), "Organisation mapping")

    returns = columns(history)
    for label, choices in [
        ("Annual return organisation", ("organisation_number",)),
        ("Annual gross income", ("total_gross_income", "gross_income", "total_income")),
        ("Annual gross expenditure", ("total_gross_expenditure", "gross_expenditure", "total_expenditure")),
        ("Annual financial period", ("fin_period_end_date", "financial_period_end_date",
                                     "financial_period_end", "financial_year_end_date", "financial_year_end")),
    ]:
        any_of(returns, choices, label)

    salary = columns(part_a)
    expected_a = {"registered_charity_number", "fin_period_end_date",
                  "count_salary_band_60001_70000", "count_salary_band_over_500000"}
    missing_a = expected_a - salary
    if missing_a:
        raise ValueError("Part A: missing required fields: " + ", ".join(sorted(missing_a)))

    spending = columns(part_b)
    expected_b = {"registered_charity_number", "fin_period_end_date",
                  "expenditure_raising_funds", "expenditure_charitable_expenditure",
                  "expenditure_grants_institution", "expenditure_support_costs",
                  "expenditure_governance", "expenditure_total", "reserves"}
    missing_b = expected_b - spending
    if missing_b:
        raise ValueError("Part B: missing required fields: " + ", ".join(sorted(missing_b)))
    print("PASS: all four official ZIP archives contain the required importer columns")
    print(f"Column counts — registry {len(main)}, history {len(returns)}, "
          f"Part A {len(salary)}, Part B {len(spending)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--charity", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--part-a", type=Path, required=True)
    parser.add_argument("--part-b", type=Path, required=True)
    args = parser.parse_args()
    check(args.charity, args.history, args.part_a, args.part_b)
