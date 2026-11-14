"""Decide if a refreshed 360Giving sample is safe to publish."""


def validate_sample(rows, reported_total, skipped_invalid=0, skipped_duplicates=0):
    if not isinstance(rows, list):
        raise ValueError("Award rows must be a list")
    if reported_total is not None and (type(reported_total) is not int or reported_total < 0):
        raise ValueError("Invalid reported award count")
    if reported_total is not None and len(rows) > reported_total:
        raise ValueError("Stored awards exceed source-reported total")
    if type(skipped_invalid) is not int or skipped_invalid < 0:
        raise ValueError("Invalid rejected-row count")
    if type(skipped_duplicates) is not int or skipped_duplicates < 0:
        raise ValueError("Invalid duplicate-row count")
    if reported_total and not rows:
        raise ValueError("Source reported awards but no valid records were collected")
    return True
