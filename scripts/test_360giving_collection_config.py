#!/usr/bin/env python3
"""Offline regression test for the bounded 360Giving collection settings."""
import ast
from pathlib import Path

source = Path("scripts/cache_360giving.py").read_text(encoding="utf-8")
tree = ast.parse(source)
settings = {}
for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in {"PER_PAGE", "MAX_PAGES"}:
                settings[target.id] = ast.literal_eval(node.value)

assert settings["PER_PAGE"] == 20, "Page size changed; review API behaviour"
assert 1 <= settings["MAX_PAGES"] <= 5, "Collection must remain bounded at five pages"
assert settings["PER_PAGE"] * settings["MAX_PAGES"] == 100, "Expected one hundred awards per direction"
print("PASS: 360Giving collector is bounded to 100 awards per organisation and direction")
