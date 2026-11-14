#!/usr/bin/env python3
"""Fixture tests for the CCEW coverage regression gate."""
from verify_refresh_regression import METRICS, validate

baseline = {key: 100000 for key in METRICS}
baseline["count"] = 300000
baseline["word_index_records"] = 300000
updated = baseline.copy()
updated["count"] = 299000
updated["word_index_records"] = 299000
errors, report = validate(baseline, updated)
assert not errors, errors

broken = updated.copy()
broken["financial_records"] = 85000
errors, _ = validate(baseline, broken)
assert any("financial_records" in message for message in errors), errors

broken = updated.copy()
broken["word_index_records"] = 288000
errors, _ = validate(baseline, broken)
assert any("word search coverage" in message for message in errors), errors

broken = updated.copy()
del broken["annual_return_part_a_records"]
errors, _ = validate(baseline, broken)
assert any("annual_return_part_a_records" in message for message in errors), errors

print("PASS: valid minor changes accepted, major data loss, missing fields and inconsistent search indexes rejected")
