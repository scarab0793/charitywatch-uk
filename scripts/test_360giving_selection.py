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
    chosen = select_organisations(path, limit=12)
    assert len(chosen) == 12, chosen
    assert chosen[:3] == list(CORE_ORG_IDS), chosen
    assert len(set(chosen)) == len(chosen), "Duplicate charity selected"
    assert "GB-CHC-100024" in chosen, "Largest valid grantmaker not selected"
    assert "GB-CHC-bad-registration" not in chosen
    assert select_organisations(path, limit=12) == chosen, "Selection is nondeterministic"
    fallback = select_organisations(Path(folder) / "missing.json")
    assert fallback == list(CORE_ORG_IDS), fallback
print("PASS: bounded, deterministic, deduplicated 360Giving cache selection with safe source fallback")
