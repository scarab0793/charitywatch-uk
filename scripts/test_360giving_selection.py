#!/usr/bin/env python3
"""Offline tests for capped and sourced 360Giving cache organisation selection."""
import json
import tempfile
from pathlib import Path
from select_360giving_orgs import CORE_ORG_IDS, select_organisations

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "grant-makers.json"
    rows = [
        {"number": str(100000 + i), "grants_to_institutions": i * 1000}
        for i in range(1, 25)
    ]
    rows.extend([
        {"number": "802052", "grants_to_institutions": 9999999},
        {"number": "bad-registration", "grants_to_institutions": 9999999},
        {"number": "12345", "grants_to_institutions": None},
    ])
    path.write_text(json.dumps({"records": rows}), encoding="utf-8")
    empty_manifest = Path(folder) / "missing-manifest.json"
    chosen = select_organisations(path, limit=12, previous_manifest=empty_manifest)
    assert len(chosen) == 12, chosen
    assert chosen[:3] == list(CORE_ORG_IDS), chosen
    assert len(set(chosen)) == len(chosen), "Duplicate charity selected"
    assert "GB-CHC-100024" in chosen, "Largest valid grantmaker not selected"
    assert "GB-CHC-bad-registration" not in chosen
    assert select_organisations(path, limit=12, previous_manifest=empty_manifest) == chosen, "Selection is nondeterministic"
    fallback = select_organisations(Path(folder) / "missing.json", previous_manifest=empty_manifest)
    assert fallback == list(CORE_ORG_IDS), fallback
    manifest_path = Path(folder) / "manifest.json"
    previous = {
        "organisations": {
            "GB-CHC-100024:made": {"updated": False, "error": "HTTPError: HTTP Error 404: Not Found"},
            "GB-CHC-100023:received": {"updated": False, "error": "HTTPError: HTTP Error 404: Not Found"},
        }
    }
    manifest_path.write_text(json.dumps(previous), encoding="utf-8")
    result_a = select_organisations(path, 12, manifest_path, retry_index=0)
    result_b = select_organisations(path, 12, manifest_path, retry_index=1)
    assert len(result_a) == len(result_b) == 12
    assert "GB-CHC-100023" in result_a and "GB-CHC-100024" not in result_a
    assert "GB-CHC-100024" in result_b and "GB-CHC-100023" not in result_b
    assert result_a[:3] == list(CORE_ORG_IDS)
    assert len(set(result_a)) == len(result_a)
    assert select_organisations(path, 12, manifest_path, retry_index=0) == result_a
    assert select_organisations(path, 3, manifest_path, retry_index=0) == list(CORE_ORG_IDS)
    # A previously unavailable source survives a refresh where not selected.
    manifest_path.write_text(json.dumps({
        "unavailable_organisations": ["GB-CHC-100023", "GB-CHC-100024"],
        "organisations": {"GB-CHC-802052:made": {"updated": True}}
    }), encoding="utf-8")
    retained = select_organisations(path, 12, manifest_path, retry_index=0)
    assert retained == result_a, "Unavailable source rotation history was lost"

print("PASS: bounded, deterministic, deduplicated 360Giving cache selection with safe source fallback")
