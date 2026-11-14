#!/usr/bin/env python3
"""Exercise the production name/number index checker on tiny realistic fixtures."""
import json
import tempfile
from pathlib import Path
from verify_search_indexes import check, shard


def write(folder, prefix, records):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (prefix + ".json")).write_text(json.dumps(records), encoding="utf-8")


with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    data = root / "data"
    records = [
        {"number": "802052", "name": "BBC CHILDREN IN NEED"},
        {"number": "123456", "name": "A SAMPLE CHARITY"},
        {"number": "765432", "name": "A SECOND CHARITY"},
    ]
    names = {}
    numbers = {}
    for record in records:
        names.setdefault(shard(record["name"]), []).append(record)
        numbers.setdefault(shard(record["number"]), []).append(record)
    for key, rows in names.items():
        write(data / "ew", key, rows)
    for key, rows in numbers.items():
        write(data / "ew" / "numbers", key, rows)
    (data / "manifest-ew.json").write_text(json.dumps({
        "count": len(records),
        "shards": sorted(names),
        "number_shards": sorted(numbers),
    }), encoding="utf-8")
    check(data, minimum=1)
    broken = dict(records[0], name="CHANGED CHARITY NAME")
    number_shard = shard(records[0]["number"])
    original = numbers[number_shard]
    write(data / "ew" / "numbers", number_shard,
          [broken if row["number"] == broken["number"] else row for row in original])
    try:
        check(data, minimum=1)
    except ValueError as error:
        assert "Name mismatch" in str(error), str(error)
    else:
        raise AssertionError("Mismatched charity name was not detected")
print("PASS: registration/name shard parity and mismatches are detected")
