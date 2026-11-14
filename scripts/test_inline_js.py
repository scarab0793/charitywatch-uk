#!/usr/bin/env python3
"""Check JavaScript embedded in the landing page using Node.js.

External <script src=...> tags are checked separately by the CI workflow.
"""
import re
import subprocess
import sys
from pathlib import Path

html = Path("index.html").read_text(encoding="utf-8")
scripts = re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", html, flags=re.I | re.S)
inline = [
    body for attrs, body in scripts
    if not re.search(r"\bsrc\s*=", attrs, flags=re.I)
    and not re.search(r"\btype\s*=\s*['\"](?:application/json|application/ld\+json)['\"]", attrs, flags=re.I)
]
if not inline:
    print("FAIL: no inline script blocks found", file=sys.stderr)
    sys.exit(1)
for i, source in enumerate(inline, 1):
    result = subprocess.run(
        ["node", "--check", "-"], input=source, text=True, capture_output=True
    )
    if result.returncode:
        print(f"FAIL: inline script {i} has JavaScript syntax errors", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
print(f"PASS: {len(inline)} inline JavaScript block(s) passed Node.js syntax checking")
