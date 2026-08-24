#!/usr/bin/env python3
"""Reverse check: prove the eval can go red, against a prediction made first.

For each seeded defect this script holds an EXPECTED-RED list written before
the defect was ever injected. It then injects the defect, runs the offline
tier, and compares. A check that was expected to go red but stayed green is a
FAKE TEST — it is asserting something the code does not actually depend on.

The source tree is restored with ``git checkout --`` afterwards and the script
verifies the working tree is clean again.

    uv run python _dong-goi/package/eval/reverse-check.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
EVAL = Path(__file__).with_name("eval-googlecast-mcp.py")

MUTATIONS = [
    {
        "id": "M1-all-includes-groups",
        "file": "src/googlecast_mcp/server.py",
        "find": '!= "group"',
        "replace": '== "group"',
        "why": "'all' would fan out to the group as well, double-streaming a speaker",
        "expected_red": [
            "'all' excludes the Cast group",
            "'all' hits each physical host exactly once",
            "each physical speaker received exactly one stream",
            "'all' = the two real speakers",
            "exactly two casts were issued",
        ],
    },
    {
        "id": "M2-no-bare-host-in-allowlist",
        "file": "src/googlecast_mcp/__main__.py",
        "find": 'for p in (h, f"{h}:*")',
        "replace": 'for p in (f"{h}:*",)',
        "why": "a reverse proxy on port 443 sends no ':port', so every request would 421",
        "expected_red": [
            "bare host with no :port is allowed",
            "loopback stays allowed",
            "an explicit bind host is allowed",
        ],
    },
    {
        "id": "M3-empty-text-not-refused",
        "file": "src/googlecast_mcp/tts.py",
        "find": "if not text or not text.strip():",
        "replace": "if False:",
        "why": "empty text would reach the TTS backend and produce a 0-byte mp3",
        "expected_red": [
            "blank text raises ValueError",
            "blank text never reaches the TTS backend",
        ],
    },
]


def clear_bytecode() -> None:
    """Drop cached .pyc files before every run.

    A mutation that keeps the file the same length can leave bytecode that
    Python happily reuses, so a "restored" tree keeps failing and a mutated
    one keeps passing. This bit us for real; do not remove it.
    """
    import shutil

    for d in (REPO / "src").rglob("__pyc" + "ache__"):
        shutil.rmtree(d, ignore_errors=True)


def run_eval() -> tuple[int, set[str]]:
    clear_bytecode()
    proc = subprocess.run(
        [sys.executable, str(EVAL), "--json"], cwd=REPO, capture_output=True, text=True
    )
    red: set[str] = set()
    match = re.search(r'^\{"passed".*\}$', proc.stdout, re.M)
    if match:
        red = set(json.loads(match.group(0))["failures"])
    else:
        red = {"<the eval crashed instead of reporting>"}
    return proc.returncode, red


def restore() -> None:
    subprocess.run(["git", "checkout", "--", "src"], cwd=REPO, check=True)


def main() -> int:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "src"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        print(f"refusing to run: src/ has uncommitted changes\n{dirty}")
        return 2

    code, red = run_eval()
    print(f"baseline: exit {code}, {len(red)} red")
    if code != 0:
        print("refusing to run: the eval is not green to begin with")
        return 2

    problems: list[str] = []
    for m in MUTATIONS:
        path = REPO / m["file"]
        source = path.read_text(encoding="utf-8")
        if m["find"] not in source:
            problems.append(f"{m['id']}: anchor not found in {m['file']}")
            continue
        path.write_text(source.replace(m["find"], m["replace"], 1), encoding="utf-8")
        try:
            code, red = run_eval()
        finally:
            restore()

        print(f"\n{m['id']}  ({m['why']})")
        print(f"  exit {code}, {len(red)} red")
        if code == 0:
            problems.append(f"{m['id']}: the eval stayed GREEN with a real defect injected")
        for expected in m["expected_red"]:
            hit = any(expected in r for r in red)
            print(f"  {'red as predicted' if hit else 'STAYED GREEN'}: {expected}")
            if not hit:
                problems.append(f"{m['id']}: FAKE TEST — expected red, stayed green: {expected}")
        for r in sorted(red):
            if not any(e in r for e in m["expected_red"]):
                print(f"  also red (not predicted): {r}")

    still_dirty = subprocess.run(
        ["git", "status", "--porcelain", "src"], cwd=REPO, capture_output=True, text=True
    ).stdout.strip()
    print(f"\nsource restored cleanly: {not still_dirty}")
    if still_dirty:
        problems.append(f"source not restored:\n{still_dirty}")

    code, red = run_eval()
    print(f"post-restore eval: exit {code}, {len(red)} red")
    if code != 0:
        problems.append("the eval is not green again after restoring")

    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nreverse check passed: every seeded defect turned the eval red as predicted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
