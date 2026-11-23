#!/usr/bin/env python3
"""Keep every published skill name installable.

Docs, quickstarts, and skills.sh install skills by name, so a skill name that
exists on the base commit must still exist, either as a skill in skills/ or as
a redirect stub in skills/.legacy/. Renaming or retiring a skill means adding
a stub that points to its replacement, not deleting the folder.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = re.compile(r"skills/(?:\.legacy/)?([^/]+)/SKILL\.md\Z")
SHA_RE = re.compile(r"[0-9a-fA-F]{40,64}\Z")


def skill_names(paths: Iterable[str]) -> set[str]:
    return {match.group(1) for path in paths if (match := SKILL_PATH.fullmatch(path))}


def base_names(base: str) -> set[str]:
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", base, "--", "skills"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    return skill_names(listing.stdout.splitlines())


def head_names() -> set[str]:
    return skill_names(
        path.relative_to(ROOT).as_posix() for path in (ROOT / "skills").glob("**/SKILL.md")
    )


def check(base: str | None) -> None:
    if base is None or set(base) == {"0"}:
        print("No base commit; skipping the skill name check.")
        return
    if not SHA_RE.fullmatch(base):
        raise ValueError("--base must be a full Git commit SHA")
    missing = sorted(base_names(base) - head_names())
    if missing:
        raise ValueError(
            "these skill names would stop installing: "
            + ", ".join(missing)
            + ". Keep them as redirect stubs in skills/.legacy/<name>/SKILL.md "
            "that point to the replacement skill."
        )
    print("Every skill name on the base commit is still installable.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="full PR base commit SHA")
    args = parser.parse_args()
    try:
        check(args.base)
    except (ValueError, subprocess.CalledProcessError) as error:
        print(f"Skill name check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
