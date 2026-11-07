#!/usr/bin/env python3
"""Require a new plugin version whenever distributable plugin files change."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILES = (
    "plugin.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    "pyproject.toml",
)
PAYLOAD_PATHS = (
    "skills",
    "plugin.json",
    ".claude-plugin/marketplace.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".mcp.json",
    "mcp.json",
)
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+\Z")
SHA_RE = re.compile(r"[0-9a-fA-F]{40,64}\Z")


def version_from_bytes(path: str, content: bytes) -> str:
    if path.endswith(".toml"):
        value = tomllib.loads(content.decode("utf-8"))["project"]["version"]
    else:
        value = json.loads(content)["version"]
    if not isinstance(value, str) or not VERSION_RE.fullmatch(value):
        raise ValueError(f"{path}: expected a version in major.minor.patch form")
    return value


def current_version() -> str:
    versions = {
        path: version_from_bytes(path, (ROOT / path).read_bytes())
        for path in VERSION_FILES
    }
    if len(set(versions.values())) != 1:
        raise ValueError(f"plugin versions differ: {versions}")
    return next(iter(versions.values()))


def git(*args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, check=True, shell=False
    )


def version_tuple(value: str) -> tuple[int, int, int]:
    major, minor, patch = value.split(".")
    return int(major), int(minor), int(patch)


def check(base: str | None) -> None:
    current = current_version()
    if base is None:
        print(f"Plugin manifests agree on version {current}.")
        return
    if not SHA_RE.fullmatch(base):
        raise ValueError("--base must be a full Git commit SHA")
    if set(base) == {"0"}:
        print(f"First push has no base commit; version {current} is consistent.")
        return

    changed = git("diff", "--name-only", base, "HEAD", "--", *PAYLOAD_PATHS)
    if not changed.stdout.strip():
        print(f"No plugin payload changes; version {current} is consistent.")
        return

    try:
        previous = git("show", f"{base}:plugin.json").stdout
    except subprocess.CalledProcessError as error:
        if b"does not exist" in error.stderr or b"exists on disk, but not in" in error.stderr:
            print(f"First plugin publication; version {current} is consistent.")
            return
        raise
    old_version = version_from_bytes("plugin.json", previous)
    if version_tuple(current) <= version_tuple(old_version):
        raise ValueError(
            f"plugin payload changed but version {current} did not increase "
            f"from {old_version}; bump all four version files"
        )
    print(f"Plugin payload changed; version increased from {old_version} to {current}.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="full PR base commit SHA")
    args = parser.parse_args()
    try:
        check(args.base)
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Plugin release check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
