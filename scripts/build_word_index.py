#!/usr/bin/env python3
"""Build a lightweight word-prefix index from existing charity name shards.

This is intentionally separate from the detailed financial JSON files. It
contains public charity names and registration numbers only, allowing typeahead
matches on any word without fetching every full charity record.
"""
import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


def normalize(value):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize(
        "NFKD", str(value)).encode("ascii", "ignore").decode().lower())


def build(data, region):
    source = data / region
    manifest_file = data / ("manifest-" + region + ".json")
    if not manifest_file.exists():
        raise ValueError("Missing region manifest")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    expected = manifest.get("count", 0)
    if expected < 1000:
        raise ValueError("Insufficient dataset for word index")
    buckets = defaultdict(dict)
    seen = set()
    for path in source.glob("*.json"):
        for row in json.loads(path.read_text(encoding="utf-8")):
            number = str(row.get("number", ""))
            name = row.get("name", "")
            if not number or not name:
                continue
            seen.add(number)
            words = set(normalize(w) for w in re.findall(r"[\w]+", name, flags=re.UNICODE))
            for word in words:
                if len(word) < 3:
                    continue
                # Two characters are enough for a reasonably sized static
                # shard; filter the full query in the browser.
                buckets[word[:2]][number] = {"name": name, "number": number}
    if len(seen) < expected * 0.95:
        raise ValueError(f"Name shard coverage too low: {len(seen)} / {expected}")
    target = data / "words" / region
    target.mkdir(parents=True, exist_ok=True)
    for existing in target.glob("*.json"):
        existing.unlink()
    for prefix, by_number in buckets.items():
        rows = sorted(by_number.values(), key=lambda r: (r["name"].casefold(), r["number"]))
        (target / (prefix + ".json")).write_text(
            json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
    manifest["word_shards"] = sorted(buckets)
    manifest["word_search_mode"] = "word_prefix_v1"
    manifest["word_index_records"] = len(seen)
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("Word search index:", len(seen), "charities,", len(buckets), "shards")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data"))
    p.add_argument("--region", default="ew")
    a = p.parse_args()
    build(a.data, a.region)
