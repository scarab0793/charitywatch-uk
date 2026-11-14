#!/usr/bin/env python3
"""Network-free checks for paginated 360Giving API responses."""
from validate_360giving_api_page import validate_page


def response(count, rows, next_page=None):
    return {"count": count, "results": [{"data": {"id": str(i)}} for i in range(rows)], "next": next_page}


def fails(payload, page=0, previous=None, message=None):
    try:
        validate_page(payload, page, previous)
    except ValueError as exc:
        assert message in str(exc), str(exc)
    else:
        raise AssertionError("Invalid API page accepted")


assert validate_page(response(21, 20, "next-page"), 0, None) == 21
assert validate_page(response(21, 1), 1, 21) == 21
assert validate_page(response(0, 0), 0, None) == 0
fails(response(25, 20, "next"), page=1, previous=24, message="changed")
fails(response(True, 0), message="invalid total")
fails(response(-2, 0), message="invalid total")
fails(response(3, 0), message="empty page")
fails(response(30, 2, "next"), message="truncated")
fails({"results": "not a list", "count": 0}, message="schema")
print("PASS: 360Giving page validation rejects inconsistent, truncated or malformed responses")
