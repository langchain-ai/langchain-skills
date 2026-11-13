# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Check that every `langsmith ...` command in the skills exists in the CLI.

Scans Markdown under skills/ for command lines in shell code fences and
inline code spans, then checks each command path and flag against the
`--help` output of the installed `langsmith` binary. Hand-written commands
print cobra help and commands generated from the API spec print urfave/cli
help; both layouts are read. Flags that do not appear
in `--help` (unknown or hidden) fail the check, except the few listed in
ALLOWED_HIDDEN_FLAGS. Positional arguments are not checked.

Commands are taken from:
  - lines in ```bash/sh/shell/zsh/console (or untagged) fences, joining
    trailing-backslash continuations and splitting on |, &&, ;, and $(...)
  - inline code spans such as `langsmith traces list --limit 5`
Placeholders like `langsmith <command>` or `langsmith ...` are skipped.
Singular aliases (`langsmith trace`) fail with the listed name to use.

Usage:
    uv run --no-project scripts/check_cli_commands.py [paths...]

Set LANGSMITH_BIN to use a binary other than `langsmith` on PATH.
Exits 1 if any command fails.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATHS = [ROOT / "skills"]
BIN = os.environ.get("LANGSMITH_BIN", "langsmith")

# Hidden in --help but intentionally documented: the CLI's own auth error
# tells users to "pass --api-key".
ALLOWED_HIDDEN_FLAGS = {"--api-key"}

# Generated commands accept langsmith's global auth and routing flags even
# though their --help does not list them (the CLI strips them before the
# generated parser runs). Each takes a value.
GENERATED_GLOBAL_FLAGS = {"--api-url", "--profile", "--workspace", "--workspace-id"}

SHELL_LANGS = {"", "bash", "sh", "shell", "zsh", "console"}
FENCE = re.compile(r"^\s*```([A-Za-z0-9_+-]*)")
INLINE_CODE = re.compile(r"`([^`\n]+)`")
SHELL_OPERATOR = re.compile(r"^[|&;()<>]+$")
# "  -p, --project string   description" or "      --full   description"
FLAG_LINE = re.compile(r"^\s+(?:-(\w), )?--([\w-]+)(?: (\S+))?(?:\s{2,}|\s*$)")
# urfave/cli: "   --kind string   description", "   --raw-output, -r   description",
# "   --id string [ --id string ]   description"
URFAVE_FLAG_LINE = re.compile(
    r"^\s+--([\w.-]+)(?:, -(\w))?(?: (\w+))?(?: \[ [^]]* \])?(?:\s{2,}|\s*$)"
)
# Section names in either layout, mapped to cobra's.
SECTIONS = {
    "USAGE": "Usage",
    "COMMANDS": "Available Commands",
    "OPTIONS": "Flags",
    "GLOBAL OPTIONS": "Global Flags",
}


@dataclass
class Help:
    subcommands: set[str] = field(default_factory=set)
    # True if the command runs on its own, not only through a subcommand
    runnable: bool = False
    # flag name (with dashes) -> takes a value
    flags: dict[str, bool] = field(default_factory=dict)


@dataclass
class Command:
    path: Path
    line: int
    argv: list[str]

    @property
    def text(self) -> str:
        return shlex.join(self.argv)


def extract(path: Path) -> list[Command]:
    """Return langsmith invocations in shell fences and inline code spans."""
    commands: list[Command] = []
    lang: str | None = None
    pending = ""
    pending_line = 0
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        fence = FENCE.match(raw)
        if fence:
            lang = None if lang is not None else fence.group(1).lower()
            pending = ""
            continue
        if lang is None:
            for span in INLINE_CODE.findall(raw):
                commands += [Command(path, lineno, c) for c in invocations(span)]
            continue
        if lang not in SHELL_LANGS:
            continue
        line = raw.strip()
        if pending:
            line = pending + " " + line
        else:
            pending_line = lineno
        if line.endswith("\\"):
            pending = line[:-1].strip()
            continue
        pending = ""
        commands += [Command(path, pending_line, c) for c in invocations(line)]
    return commands


def invocations(line: str) -> list[list[str]]:
    """Split a shell line on operators and return each `langsmith ...` argv.

    Skips placeholders such as `langsmith ...` or `langsmith <command>`.
    """
    lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    found: list[list[str]] = []
    segment: list[str] = []
    for token in [*tokens, ";"]:
        if not SHELL_OPERATOR.match(token):
            segment.append(token)
            continue
        while segment and (segment[0] in ("$", "sudo") or "=" in segment[0]):
            segment.pop(0)  # prompt, $(...) prefix, or ENV=value
        if (
            len(segment) > 1
            and segment[0] == "langsmith"
            and not segment[1].startswith(("<", "..."))
        ):
            found.append(segment)
        segment = []
    return found


@cache
def get_help(command_path: tuple[str, ...]) -> Help:
    result = subprocess.run(
        [BIN, *command_path, "--help"], capture_output=True, text=True, check=False
    )
    help_ = Help()
    section = ""
    urfave = False
    for line in result.stdout.splitlines():
        if line and not line[0].isspace():
            # Section headers end with ":"; other unindented lines are wrapped
            # descriptions.
            if line.endswith(":"):
                section = SECTIONS.get(line[:-1], line[:-1])
                urfave = urfave or line[:-1] in SECTIONS
            continue
        if (
            section == "Usage"
            and line.strip()
            and not line.endswith(("[command]", "[command [command options]]"))
        ):
            help_.runnable = True
        if section == "Available Commands":
            # Subcommands start at a fixed indent; wrapped urfave descriptions
            # are indented further.
            match = re.match(r"^ {2,3}([a-z][\w:-]*)(?:\s|$)", line)
            if match:
                help_.subcommands.add(match.group(1))
        elif section in ("Flags", "Global Flags"):
            match = FLAG_LINE.match(line)
            if match:
                short, name, value = match.groups()
            else:
                match = URFAVE_FLAG_LINE.match(line)
                if not match:
                    continue
                name, short, value = match.groups()
            help_.flags["--" + name] = bool(value)
            if short:
                help_.flags["-" + short] = bool(value)
    if urfave:
        help_.flags.update(dict.fromkeys(GENERATED_GLOBAL_FLAGS, True))
    if result.returncode != 0 and not help_.flags:
        raise RuntimeError(f"`{BIN} {' '.join(command_path)} --help` failed")
    return help_


def canonical_name(command_path: tuple[str, ...], name: str) -> str | None:
    """Return the listed name if `name` is an alias (e.g. `trace` -> `traces`)."""
    out = subprocess.run(
        [BIN, *command_path, name, "--help"], capture_output=True, text=True, check=False
    ).stdout
    match = re.search(r"^Usage:\n\s+langsmith (.*?) \[command\]", out, re.M)
    if match and len(match.group(1).split()) == len(command_path) + 1:
        return match.group(1).split()[-1]
    return None


def check(command: Command) -> list[str]:
    tokens = command.argv[1:]  # drop "langsmith"
    path: tuple[str, ...] = ()
    errors: list[str] = []
    positional_seen = False
    i = 0
    while i < len(tokens):
        token = tokens[i]
        help_ = get_help(path)
        if token in ("-h", "--help"):
            i += 1
            continue
        if token.startswith("-") and token != "-":
            name, has_inline_value = token.split("=", 1)[0], "=" in token
            if name in ALLOWED_HIDDEN_FLAGS:
                i += 1 if has_inline_value else 2
                continue
            if name not in help_.flags:
                where = " ".join(("langsmith", *path))
                errors.append(f"unknown or hidden flag {name} for `{where}`")
                return errors  # can't tell if it takes a value, so stop here
            takes_value = help_.flags[name]
            i += 1 if has_inline_value or not takes_value else 2
            continue
        if not positional_seen and token in help_.subcommands:
            path = (*path, token)
        elif not positional_seen and help_.subcommands and not help_.runnable:
            where = " ".join(("langsmith", *path, token))
            listed = canonical_name(path, token)
            if not listed:
                errors.append(f"unknown command `{where}`")
                return errors
            errors.append(f"`{where}` uses an alias; use `{listed}`")
            path = (*path, listed)
        else:
            positional_seen = True
        i += 1
    return errors


def main(argv: list[str]) -> int:
    roots = [Path(p) for p in argv] or DEFAULT_PATHS
    files = sorted(
        f for root in roots for f in ([root] if root.is_file() else root.rglob("*.md"))
    )
    failures = 0
    total = 0
    for file in files:
        for command in extract(file):
            total += 1
            for error in check(command):
                failures += 1
                rel = os.path.relpath(command.path, ROOT)
                print(f"{rel}:{command.line}: {error}\n    {command.text}")
    version = subprocess.run([BIN, "--version"], capture_output=True, text=True).stdout
    print(f"\nChecked {total} commands against {version.strip()}: {failures} problem(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
