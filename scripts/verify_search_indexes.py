#!/usr/bin/env python3
"""Verify registry search indexes contain the same official charity records.

Name and registration-number shards are independently generated from the
Charity Commission extract. A mismatched or missing shard can make valid
charities disappear from search despite a successful import.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path


def normalized(value):
    ascii_text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.sub("[^a-z0-9]", "", ascii_text.lower())


def shard(value):
    return (normalized(value) + "__")[:2]


def read_groups(folder, prefixes, kind):
    seen = {}
    for prefix in prefixes:
        path = folder / (prefix + ".json")
        if not path.is_file():
            raise ValueError(f"{kind}: missing shard {prefix}")
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list) or not records:
            raise ValueError(f"{kind}: empty or invalid shard {prefix}")
        for row in records:
            number = str(row.get("number") or "")
            name = row.get("name")
            if not number or not isinstance(name, str) or not name:
                raise ValueError(f"{kind}: missing registration or name in {prefix}")
            match = shard(name if kind == "name" else number)
            if match != prefix:
                raise ValueError(f"{kind}: {number} stored in {prefix}, expected {match}")
            if number in seen:
                raise ValueError(f"{kind}: duplicate registration {number}")
            # Compare complete published profiles, not only displayed names.
            # The importer must write identical financial/Part B details into
            # both the name and registration-number lookup shards.
            canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(\",\", \":\"))
            seen[number] = hashlib.sha256(canonical.encode(\"utf-8\")).hexdigest()
    return seen


def check(root, minimum=100000):
    manifest = json.loads((root / "manifest-ew.json").read_text(encoding="utf-8"))
    expected = manifest.get("count", 0)
    if expected < minimum:
        raise ValueError("Implausibly low charity count")
    names = read_groups(root / "ew", manifest.get("shards", []), "name")
    numbers = read_groups(root / "ew" / "numbers", manifest.get("number_shards", []), "number")
    if len(names) != expected or len(numbers) != expected:
        raise ValueError(f"Registry mismatch: manifest {expected}, name index {len(names)}, number index {len(numbers)}")
    if names != numbers:
        missing = names.keys() ^ numbers.keys()
        if missing:
            raise ValueError(f"Index mismatch: {len(missing)} registrations missing in one index")
        different = sum(names[k] != numbers[k] for k in names)
        raise ValueError(f"Profile mismatch for {different} registrations between indexes")
    print(f"PASS: {expected:,} complete charity profiles are identical in name and registration search indexes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("data"))
    args = parser.parse_args()
    try:
        check(args.data)
    except (ValueError, KeyError, TypeError, FileNotFoundError, json.JSONDecodeError) as error:
        print("FAIL:", str(error), file=sys.stderr)
        sys.exit(1)
