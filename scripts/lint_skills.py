# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Lint the skills in config/skills against the Agent Skills guidelines.

Layers the first-party `claude plugin validate` and `claude plugin details`
reports with house rules the validator does not cover. Exits 1 on BLOCK.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

LINE_WARN = 500
LINE_BLOCK = 600
ON_INVOKE_TOKEN_WARN = 6000
LANGUAGE_SPLIT_WARN = 150

ALLOWED_MODELS = {
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-fable-5-1",
    "claude-haiku-4-5-20251001",
    "gpt-5.5",
}

MODEL_PATTERN = re.compile(
    r"\b(claude-[a-z0-9.\-]*\d[a-z0-9.\-]*|gpt-[0-9][a-z0-9.\-]*)"
)
PIPE_TO_SHELL = re.compile(r"curl[^\n|]*\|\s*(?:sudo\s+)?(?:sh|bash)\b")
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```([A-Za-z0-9_+-]*)\s*$")
TOKEN_ROW = re.compile(r"^\s*(\S+)\s+~([\d.]+k?)\s+~([\d.]+k?)\s*$")

PYTHON_LANGS = {"python", "py"}
TS_LANGS = {"typescript", "ts", "javascript", "js", "tsx", "jsx"}

BLOCK = "BLOCK"
WARN = "WARN"


@dataclass
class Finding:
    severity: str
    rule: str
    path: Path
    line: int
    message: str


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fields: dict[str, str] = {}
    for raw in text[3:end].splitlines():
        if raw.startswith((" ", "\t")) or ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        fields[key.strip()] = value.strip().strip("\"'")
    return fields


def parse_tokens(value: str) -> int:
    return int(float(value[:-1]) * 1000) if value.endswith("k") else int(float(value))


def run_claude(args: list[str], root: Path) -> subprocess.CompletedProcess[str] | None:
    claude = shutil.which("claude")
    if claude is None:
        return None
    return subprocess.run(
        [claude, *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )


def within(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def check_plugin_validate(root: Path, skills_dir: Path) -> list[Finding]:
    result = run_claude(
        ["plugin", "validate", str(skills_dir.relative_to(root)), "--strict", "--json"],
        root,
    )
    if result is None:
        return [
            Finding(WARN, "validate", skills_dir, 1, "claude CLI not on PATH; stage skipped")
        ]
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return [
            Finding(
                WARN,
                "validate",
                skills_dir,
                1,
                f"unreadable validator output: {detail[0] if detail else 'no output'}",
            )
        ]

    findings = []
    for entry in report.get("contents", []):
        target = Path(entry.get("file", str(skills_dir)))
        for problem in entry.get("errors", []) + entry.get("warnings", []):
            label = problem.get("path") or "manifest"
            findings.append(
                Finding(BLOCK, "validate", target, 1, f"{label}: {problem.get('message', '')}")
            )
    return findings


def check_token_cost(root: Path, plugin_name: str, skills: list[Path]) -> list[Finding]:
    result = run_claude(
        ["--plugin-dir", ".", "plugin", "details", plugin_name], root
    )
    if result is None or result.returncode != 0:
        return []

    by_name = {skill.parent.name: skill for skill in skills}
    findings = []
    in_table = False
    for raw in result.stdout.splitlines():
        if raw.strip().startswith("component"):
            in_table = True
            continue
        if not in_table:
            continue
        match = TOKEN_ROW.match(raw)
        if match is None:
            continue
        name, _, on_invoke = match.groups()
        cost = parse_tokens(on_invoke)
        if cost > ON_INVOKE_TOKEN_WARN and name in by_name:
            findings.append(
                Finding(
                    WARN,
                    "token-cost",
                    by_name[name],
                    1,
                    f"~{cost:,} on-invoke tokens exceeds the ~{ON_INVOKE_TOKEN_WARN:,} budget",
                )
            )
    return findings


def check_skill(root: Path, skill: Path) -> list[Finding]:
    text = skill.read_text(encoding="utf-8")
    lines = text.splitlines()
    findings = []

    count = len(lines)
    if count > LINE_BLOCK:
        findings.append(
            Finding(BLOCK, "size", skill, 1, f"{count} lines exceeds the hard cap of {LINE_BLOCK}")
        )
    elif count > LINE_WARN:
        findings.append(
            Finding(WARN, "size", skill, 1, f"{count} lines exceeds the target of {LINE_WARN}")
        )

    declared = parse_frontmatter(text).get("name")
    if declared and declared != skill.parent.name:
        findings.append(
            Finding(
                BLOCK,
                "name",
                skill,
                2,
                f"frontmatter name '{declared}' does not match directory '{skill.parent.name}'",
            )
        )

    per_language: dict[str, int] = {}
    language = None
    for number, line in enumerate(lines, start=1):
        fence = FENCE.match(line)
        if fence is not None:
            language = None if language is not None else (fence.group(1).lower() or "text")
            continue
        if language is not None:
            bucket = (
                "python" if language in PYTHON_LANGS
                else "typescript" if language in TS_LANGS
                else None
            )
            if bucket:
                per_language[bucket] = per_language.get(bucket, 0) + 1

    has_references = (skill.parent / "references").is_dir()
    for bucket, total in sorted(per_language.items()):
        if total > LANGUAGE_SPLIT_WARN and not has_references:
            findings.append(
                Finding(
                    WARN,
                    "language-split",
                    skill,
                    1,
                    f"{total} lines of {bucket} inline with no references/ split",
                )
            )
    return findings


def check_document(root: Path, path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8")
    findings = []

    stale: dict[str, tuple[int, int]] = {}
    for number, line in enumerate(text.splitlines(), start=1):
        if PIPE_TO_SHELL.search(line):
            findings.append(
                Finding(WARN, "pipe-to-shell", path, number, "pipes a remote script into a shell")
            )
        for model in MODEL_PATTERN.findall(line):
            if model not in ALLOWED_MODELS:
                first, count = stale.get(model, (number, 0))
                stale[model] = (first, count + 1)

    for model, (first, count) in sorted(stale.items()):
        occurrences = f"{count} occurrence{'s' if count > 1 else ''}"
        findings.append(
            Finding(
                WARN,
                "model-id",
                path,
                first,
                f"'{model}' is not in the allowlist ({occurrences})",
            )
        )

    if path.suffix == ".md":
        for number, line in enumerate(text.splitlines(), start=1):
            for target in MARKDOWN_LINK.findall(line):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                resolved = (path.parent / target.split("#", 1)[0]).resolve()
                if not within(root, resolved) or not resolved.exists():
                    findings.append(
                        Finding(WARN, "dead-link", path, number, f"'{target}' does not resolve")
                    )
    return findings


def annotate(finding: Finding, root: Path) -> None:
    level = "error" if finding.severity == BLOCK else "warning"
    try:
        location = finding.path.resolve().relative_to(root.resolve())
    except ValueError:
        location = finding.path
    print(
        f"::{level} file={location},line={finding.line},title={finding.rule}::{finding.message}"
    )


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    skills_dir = root / "config" / "skills"
    if not skills_dir.is_dir():
        print(f"no skills directory at {skills_dir}", file=sys.stderr)
        return 1

    manifest = root / ".claude-plugin" / "plugin.json"
    plugin_name = json.loads(manifest.read_text())["name"] if manifest.is_file() else root.name

    skills = sorted(skills_dir.glob("*/SKILL.md"))
    documents = sorted(
        {
            *skills,
            *(p for p in (root / "config").rglob("*.md")),
            *(p for p in [root / "README.md", root / "install.sh"] if p.is_file()),
        }
    )

    findings = check_plugin_validate(root, skills_dir)
    findings += check_token_cost(root, plugin_name, skills)
    for skill in skills:
        findings += check_skill(root, skill)
    for document in documents:
        findings += check_document(root, document)

    blocking = [f for f in findings if f.severity == BLOCK]
    warnings = [f for f in findings if f.severity == WARN]

    if os.environ.get("GITHUB_ACTIONS") == "true":
        for finding in blocking + warnings:
            annotate(finding, root)

    print(f"\n{plugin_name}: {len(skills)} skills, {len(documents)} documents scanned\n")
    for finding in blocking + warnings:
        try:
            location = finding.path.resolve().relative_to(root.resolve())
        except ValueError:
            location = finding.path
        print(f"  {finding.severity:<5} {finding.rule:<15} {location}:{finding.line}")
        print(f"        {finding.message}")

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding.rule] = counts.get(finding.rule, 0) + 1
    if counts:
        print("\n  by rule: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"\n{len(blocking)} blocking, {len(warnings)} warnings")

    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
