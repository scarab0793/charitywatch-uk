#!/usr/bin/env python3
"""Offline coverage for paginated and legacy 360Giving award snapshots."""
import datetime
import json
import tempfile
from pathlib import Path
from verify_360giving_cache import validate

org = "GB-CHC-802052"
direction = "made"
key = org + ":" + direction
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    sample = [{"grant_id": f"grant-{i}", "data": {"id": f"grant-{i}"}} for i in range(23)]
    snapshot = {
        "organisation_id": org, "direction": direction, "retrieved_utc": now,
        "reported_count": 50, "records_cached": 23, "partial": True,
        "skipped_invalid": 0, "skipped_duplicates": 0,
        "page_size": 20,
        "pages": [f"{org}-{direction}-p1.json", f"{org}-{direction}-p2.json"],
    }
    manifest = {
        "max_records_per_org_direction": 100,
        "organisations": {key: {"updated": True, "records_cached": 23, "reported_count": 50}},
        "updated_directions": 1, "status": "ok",
    }
    metadata = root / f"{org}-{direction}.json"
    listing = root / "manifest.json"
    metadata.write_text(json.dumps(snapshot), encoding="utf-8")
    listing.write_text(json.dumps(manifest), encoding="utf-8")
    for index, rows in enumerate((sample[:20], sample[20:]), 1):
        (root / f"{org}-{direction}-p{index}.json").write_text(
            json.dumps({"results": rows}), encoding="utf-8")
    assert not validate(root), "Valid paginated snapshot rejected"
    second = root / f"{org}-{direction}-p2.json"
    second.unlink()
    assert any("missing/invalid page" in e for e in validate(root))
    second.write_text(json.dumps({"results": sample[20:]}), encoding="utf-8")
    snapshot["pages"] = ["../other.json"]
    metadata.write_text(json.dumps(snapshot), encoding="utf-8")
    assert any("invalid snapshot page references" in e for e in validate(root))
    snapshot.pop("pages")
    snapshot.pop("page_size")
    snapshot["results"] = sample
    metadata.write_text(json.dumps(snapshot), encoding="utf-8")
    assert not validate(root), "Legacy single-file snapshot rejected"
print("PASS: paged snapshots, absent pages, unsafe names and legacy snapshots")
