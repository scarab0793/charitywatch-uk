#!/usr/bin/env python3
"""Regression checks for safe 360Giving snapshot replacement."""
from validate_360giving_sample import validate_sample


def rejects(rows, total, invalid=0, duplicate=0):
    try:
        validate_sample(rows, total, invalid, duplicate)
    except ValueError:
        return
    raise AssertionError("Unsafe award snapshot was accepted")


assert validate_sample([], 0)
assert validate_sample([{"grant_id": "a"}], 10)
assert validate_sample([{"grant_id": "a"}], None)
assert validate_sample([{"grant_id": "a"}], 1, 2, 1)
rejects([], 4, 4)
rejects([], 4)
rejects([1, 2], 1)
rejects([], True)
rejects([], -1)
rejects([], 0, -1)
rejects([], 0, 0, True)
rejects("not a list", 0)
print("PASS: unusable refreshed award samples cannot replace valid cached grants")
