"""Validate 360Giving API page consistency without making network requests."""


def validate_page(payload, page, previous_total, page_size=20):
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("360Giving returned an unexpected schema")
    total = payload.get("count")
    if total is not None and (type(total) is not int or total < 0):
        raise ValueError("360Giving returned an invalid total count")
    if previous_total is not None and total != previous_total:
        raise ValueError("360Giving total count changed during pagination")
    reported_total = total if previous_total is None else previous_total
    rows = payload["results"]
    if not rows and (payload.get("next") or (page == 0 and reported_total)):
        raise ValueError("360Giving returned an empty page despite reporting available awards")
    if payload.get("next") and len(rows) != page_size:
        raise ValueError("360Giving returned a truncated non-final API page")
    return reported_total
