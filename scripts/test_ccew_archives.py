#!/usr/bin/env python3
"""Small synthetic fixtures for CCEW official ZIP schema preflight."""
import csv
import io
import tempfile
import zipfile
from pathlib import Path
from check_ccew_archives import check

def make_zip(base, name, fields):
    path = base / (name + ".zip")
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(fields)
    writer.writerow(["sample"] * len(fields))
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name + ".txt", buffer.getvalue())
    return path

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    main = make_zip(root, "charity", [
        "organisation_number", "registered_charity_number", "charity_name", "other_field"
    ])
    history = make_zip(root, "history", [
        "organisation_number", "fin_period_end_date", "total_gross_income",
        "total_gross_expenditure"
    ])
    part_a = make_zip(root, "parta", [
        "registered_charity_number", "fin_period_end_date",
        "count_salary_band_60001_70000", "count_salary_band_over_500000"
    ])
    part_b = make_zip(root, "partb", [
        "registered_charity_number", "fin_period_end_date", "expenditure_raising_funds",
        "expenditure_charitable_expenditure", "expenditure_grants_institution",
        "expenditure_support_costs", "expenditure_governance",
        "expenditure_total", "reserves"
    ])
    check(main, history, part_a, part_b)
    broken = make_zip(root, "broken_parta", [
        "registered_charity_number", "fin_period_end_date", "other", "not_salary_bands"
    ])
    try:
        check(main, history, broken, part_b)
    except ValueError as exc:
        assert "Part A" in str(exc), str(exc)
    else:
        raise AssertionError("Malformed Part A archive unexpectedly passed")
print("PASS: CCEW extract schema preflight accepts valid data and rejects malformed extracts")
