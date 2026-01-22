#!/usr/bin/env python3
"""Test runner for DeepAgents CLI - execution functions and CLI."""

import sys
import os
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional
import pexpect
from dotenv import load_dotenv

# Add parent directory to path for scaffold imports when run as script
sys.path.insert(0, str(Path(__file__).parent.parent))

from scaffold.setup import get_deepagents_python

load_dotenv(Path(__file__).parent.parent / ".env")


def make_autonomous_prompt(task_prompt: str) -> str:
    """Add summary requirement to a task prompt for autonomous testing.

    Args:
        task_prompt: The core task prompt

    Returns:
        Complete prompt with summary requirement added
    """
    return f"""{task_prompt}

Finally, write a comprehensive summary to agent_summary.txt that includes:
- What you did
- Skills you consulted
- All code you generated (with code blocks)
- Any files you created
- Final status

Format the summary clearly for human review."""


def run_deepagents_subprocess(
    agent_name: str,
    prompt: str,
    test_dir: Path,
    runner_path: Path,
    timeout: int = 300,
    env: dict = None
) -> tuple[int, str, str]:
    """Run a deepagents test via this runner as subprocess. Default timeout: 5 minutes."""
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    result = subprocess.run(
        [str(get_deepagents_python(test_dir)), str(runner_path), agent_name, prompt,
         "--working-dir", str(test_dir)],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(test_dir),
        env=process_env
    )
    return result.returncode, result.stdout, result.stderr


def extract_summary_path(stdout: str) -> Optional[Path]:
    """Extract summary.txt path from runner stdout."""
    lines = stdout.split('\n')
    for i, line in enumerate(lines):
        if 'Review output:' in line and 'summary.txt' in line:
            return Path(line.split(':', 1)[1].strip())
        elif 'Review output:' in line and i + 1 < len(lines) and 'summary.txt' in lines[i + 1]:
            return Path(lines[i + 1].strip())
        elif 'summary.txt' in line and line.strip().startswith('/'):
            return Path(line.strip())
    return None


def run_autonomous_test(
    test_name: str,
    prompt: str,
    test_dir: Path,
    runner_path: Path,
    validate_func,
    timeout: int = 300
) -> int:
    """Run an autonomous test with standard flow. Default timeout: 5 minutes."""
    print(f"{'=' * 70}\nAUTONOMOUS TEST: {test_name}\n{'=' * 70}\n")
    print(f"PROMPT:\n{'-' * 70}\n{prompt}\n{'-' * 70}\n")
    print(f"Test directory: {test_dir}\n")
    print("Running deepagents (this may take 60-300 seconds)...\n")

    try:
        returncode, stdout, stderr = run_deepagents_subprocess(
            "langchain_agent", prompt, test_dir, runner_path, timeout)
        if stderr:
            print(f"STDERR:\n{stderr}\n")
    except Exception as e:
        print(f"ERROR running test: {e}")
        return 1

    summary_file = extract_summary_path(stdout)
    if not summary_file or not summary_file.exists():
        print(f"ERROR: Could not find summary file\nSTDOUT:\n{stdout}")
        return 1

    print(f"✓ Output saved to: {summary_file}\n")

    summary_content = summary_file.read_text()
    print(f"SESSION SUMMARY:\n{'=' * 70}\n{summary_content}\n{'=' * 70}\n")
    print(f"VALIDATION:\n{'-' * 70}")

    validations_passed, validations_failed = validate_func(summary_content, test_dir)
    for v in validations_passed + validations_failed:
        print(v)
    print(f"{'-' * 70}\n")

    if validations_failed:
        print(f"RESULT: FAILED\n\nFailed checks:")
        for v in validations_failed:
            print(f"  {v}")
        return 1

    print(f"RESULT: PASSED\n  All {len(validations_passed)} checks passed")
    return 0


# ============================================================================
# CLI Implementation (pexpect-based runner)
# ============================================================================

def run_deepagents_test(agent_name: str, prompt: str, output_dir: Path, working_dir: Path):
    """Run a DeepAgents test and generate reports."""
    print(f"\n{'='*70}\nTesting DeepAgents: {agent_name}\n{'='*70}\n")
    print(f"Prompt: {prompt}\n\nRunning agent (this may take 30-300 seconds)...")

    deepagents_path = working_dir / ".venv" / "bin" / "deepagents"
    if not deepagents_path.exists():
        print(f"Error: deepagents not found at {deepagents_path}")
        sys.exit(1)

    load_dotenv()
    summary_file = working_dir / "agent_summary.txt"

    process = pexpect.spawn(
        str(deepagents_path),
        ['--agent', agent_name, '--auto-approve', '-m', prompt],
        cwd=str(working_dir),
        timeout=None,
        encoding='utf-8',
        echo=False,
        env=os.environ.copy()
    )

    # Capture output with completion detection
    output_lines = []
    last_output_time = time.time()
    idle_threshold = 5

    while True:
        try:
            index = process.expect(['\r?\n', pexpect.EOF], timeout=1)
            if index == 1:
                break
            line = process.before + process.match.group(0)
            print(line, end='')
            output_lines.append(line)
            last_output_time = time.time()
        except pexpect.TIMEOUT:
            if summary_file.exists() and time.time() - last_output_time >= idle_threshold:
                print(f"\n✓ Agent completed (no output for {idle_threshold}s, summary exists)")
                process.terminate(force=True)
                break
        except:
            break

    process.close()

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "raw_output.txt").write_text(''.join(output_lines))

    if summary_file.exists():
        (output_dir / "summary.txt").write_text(summary_file.read_text())
        print("\n✓ Agent wrote summary")
    else:
        (output_dir / "summary.txt").write_text("No summary generated by agent")
        print("\n⚠ Agent did not write summary file")

    print(f"\n{'='*70}\nSession complete\n{'='*70}\n")
    print(f"Review output:\n  {output_dir / 'summary.txt'}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Test DeepAgents CLI")
    parser.add_argument("agent", help="Agent name")
    parser.add_argument("prompt", help="Prompt to test")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("--working-dir", default=".", help="Working directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir) if args.output_dir else \
        Path(__file__).parent.parent / "logs" / f"{args.agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return run_deepagents_test(args.agent, args.prompt, output_dir, Path(args.working_dir).resolve())


if __name__ == "__main__":
    sys.exit(main())
