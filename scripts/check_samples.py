"""Run the Python code samples in config/skills against the installed LangChain packages.

Every ```python block in the skill Markdown files is checked in its own process:

- run      Self-contained blocks run for real. Chat models and embeddings are faked and
           the network is off (see scripts/samples/prelude.py), so no API keys are needed.
- imports  Fragments (blocks that use names they don't define, or `...` placeholders) only
           have their import statements run, which catches moved or removed APIs.
- skip     Blocks marked with a skip comment are not run.

Example scripts (.py files under config/skills) are byte-compiled, and those with a CLI
get `--help` run.

To mark a block, put an HTML comment on the line right before its fence:

    <!-- sample-check: imports (needs a Postgres server) -->
    <!-- sample-check: skip (pseudo-code) -->

The reason in parentheses is required. Exits 1 if any block fails.

Usage: uv run --no-project --with-requirements scripts/samples/requirements.txt \
           scripts/check_samples.py [paths...] [-k SUBSTRING] [-v]
"""

from __future__ import annotations

import argparse
import ast
import importlib.metadata
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "config" / "skills"
PRELUDE_DIR = Path(__file__).resolve().parent / "samples"
TIMEOUT = 120

FENCE_OPEN = re.compile(r"^(\s*)```(python|py)\s*$")
FENCE_CLOSE = re.compile(r"^\s*```\s*$")
MARKER = re.compile(r"^\s*<!--\s*sample-check:\s*(\w+)\s*(?:\((.*)\))?\s*-->\s*$")
MODES = {"run", "imports", "skip"}
REPORTED_PACKAGES = ["langchain", "langchain-core", "langgraph", "deepagents", "langchain-openai",
                     "langchain-anthropic", "langchain-community"]


@dataclass
class Sample:
    path: Path
    line: int  # first line of code in the Markdown file
    code: str
    mode: str = "run"
    reason: str = ""

    @property
    def where(self) -> str:
        return f"{self.path.relative_to(ROOT)}:{self.line}"


@dataclass
class Result:
    sample: Sample
    mode: str
    ok: bool
    detail: str = ""


def extract(path: Path) -> list[Sample]:
    lines = path.read_text().splitlines()
    samples: list[Sample] = []
    i = 0
    while i < len(lines):
        if not FENCE_OPEN.match(lines[i]):
            i += 1
            continue
        start = i + 1
        end = start
        while end < len(lines) and not FENCE_CLOSE.match(lines[end]):
            end += 1
        indent = len(FENCE_OPEN.match(lines[i]).group(1))
        code = "\n".join(line[indent:] for line in lines[start:end]) + "\n"
        sample = Sample(path, start + 1, code)
        marker = MARKER.match(lines[i - 1]) if i > 0 else None
        if marker:
            sample.mode, sample.reason = marker.group(1), (marker.group(2) or "").strip()
        samples.append(sample)
        i = end + 1
    return samples


def undefined_names(tree: ast.Module, filename: str) -> list[str]:
    from pyflakes import checker, messages

    found = checker.Checker(tree, filename=filename)
    return sorted({m.message_args[0] for m in found.messages
                   if isinstance(m, messages.UndefinedName)})


def has_placeholder(tree: ast.Module) -> bool:
    """`...` used as a value (`[...]`, `f(...)`), not as a stub body."""
    stub_bodies = {id(n.value) for n in ast.walk(tree) if isinstance(n, ast.Expr)}
    return any(isinstance(n, ast.Constant) and n.value is Ellipsis and id(n) not in stub_bodies
               for n in ast.walk(tree))


def imports_only(tree: ast.Module) -> str:
    nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
    return "\n".join(ast.unparse(n) for n in nodes) + "\n"


def run_python(code: str, workdir: Path, *args: str, script: Path | None = None) -> tuple[bool, str]:
    if script is None:
        script = workdir / "sample.py"
        script.write_text(code)
    bootstrap = ("import sys, runpy; sys.path.insert(0, sys.argv.pop(1)); import prelude; "
                 "sys.argv = sys.argv[1:]; runpy.run_path(sys.argv[0], run_name='__main__')")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run([sys.executable, "-c", bootstrap, str(PRELUDE_DIR), str(script), *args],
                              cwd=workdir, capture_output=True, text=True, timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {TIMEOUT}s"
    return proc.returncode == 0, proc.stderr.strip()


def error_line(stderr: str) -> int | None:
    """Line in sample.py of the innermost frame that is in the sample."""
    hits = re.findall(r'File ".*sample\.py", line (\d+)', stderr)
    return int(hits[-1]) if hits else None


def last_line(stderr: str) -> str:
    lines = [line for line in stderr.splitlines() if line.strip()]
    return lines[-1] if lines else "failed with no output"


def check(sample: Sample) -> Result:
    if sample.mode not in MODES:
        return Result(sample, sample.mode, False, f"unknown sample-check mode {sample.mode!r}")
    if sample.mode != "run" and not sample.reason:
        return Result(sample, sample.mode, False, "sample-check marker needs a (reason)")
    if sample.mode == "skip":
        return Result(sample, "skip", True, sample.reason)
    try:
        tree = ast.parse(sample.code)
    except SyntaxError as e:
        return Result(sample, sample.mode, False,
                      f"line {sample.line + (e.lineno or 1) - 1}: SyntaxError: {e.msg}")

    mode, code, note = sample.mode, sample.code, sample.reason
    if mode == "run":
        missing = undefined_names(tree, sample.where)
        if missing:
            mode, note = "imports", "uses undefined " + ", ".join(missing)
        elif has_placeholder(tree):
            mode, note = "imports", "has ... placeholders"
    if mode == "imports":
        code = imports_only(tree)

    with tempfile.TemporaryDirectory(prefix="sample-") as tmp:
        ok, stderr = run_python(code, Path(tmp))
    if ok:
        return Result(sample, mode, True, note)
    line = error_line(stderr) if mode == "run" else None
    where = f"line {sample.line + line - 1}: " if line else ""
    return Result(sample, mode, False, where + last_line(stderr) + ("\n" + stderr if VERBOSE else ""))


def check_script(path: Path) -> Result:
    sample = Sample(path, 1, "")
    try:
        compile(path.read_text(), str(path), "exec")
    except SyntaxError as e:
        return Result(sample, "script", False, f"line {e.lineno}: SyntaxError: {e.msg}")
    text = path.read_text()
    if "__main__" in text and "argparse" in text:
        with tempfile.TemporaryDirectory(prefix="sample-") as tmp:
            ok, stderr = run_python("", Path(tmp), "--help", script=path)
        return Result(sample, "script", ok, "" if ok else last_line(stderr))
    return Result(sample, "script", True, "compiled")


VERBOSE = False


def main() -> int:
    global VERBOSE
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, help="Markdown/.py files or folders (default: config/skills)")
    parser.add_argument("-k", help="only check samples whose file:line contains this")
    parser.add_argument("-v", action="store_true", help="print full tracebacks and passing samples")
    parser.add_argument("-j", type=int, default=os.cpu_count() or 4, help="parallel processes")
    args = parser.parse_args()
    VERBOSE = args.v

    files: list[Path] = []
    for p in args.paths or [SKILLS]:
        p = p.resolve()
        files += sorted(p.rglob("*")) if p.is_dir() else [p]
    samples = [s for f in files if f.suffix == ".md" for s in extract(f)]
    scripts = [f for f in files if f.suffix == ".py"]
    if args.k:
        samples = [s for s in samples if args.k in s.where]
        scripts = [f for f in scripts if args.k in str(f.relative_to(ROOT))]

    versions = []
    for pkg in REPORTED_PACKAGES:
        try:
            versions.append(f"{pkg}=={importlib.metadata.version(pkg)}")
        except importlib.metadata.PackageNotFoundError:
            pass
    print("Checking against " + ", ".join(versions))

    with ThreadPoolExecutor(args.j) as pool:
        results = list(pool.map(check, samples)) + list(pool.map(check_script, scripts))

    failures = [r for r in results if not r.ok]
    for r in results:
        if not r.ok:
            print(f"FAIL {r.sample.where} [{r.mode}] {r.detail}")
        elif args.v:
            print(f"ok   {r.sample.where} [{r.mode}] {r.detail}")

    counts: dict[str, int] = {}
    for r in results:
        counts[r.mode] = counts.get(r.mode, 0) + 1
    summary = ", ".join(f"{n} {mode}" for mode, n in sorted(counts.items()))
    print(f"\n{len(results)} checked ({summary}): {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
