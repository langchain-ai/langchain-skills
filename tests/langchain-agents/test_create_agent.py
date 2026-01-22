#!/usr/bin/env python3
"""
Autonomous test for SQL agent creation using langchain-agents skill.

This test:
1. Defines a complete, specific prompt
2. Runs deepagents via scaffold/runner.py
3. Validates output against expected patterns
4. Reports results

Run:
    python tests/langchain-agents/test_sql_agent_autonomous.py
    python tests/langchain-agents/test_sql_agent_autonomous.py --work-dir /path/to/test/env
    python tests/langchain-agents/test_sql_agent_autonomous.py --use-temp
"""

import sys
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.setup import (
    setup_test_environment,
    cleanup_test_environment,
    copy_test_data
)
from scaffold.runner import (
    run_deepagents_subprocess,
    extract_summary_path,
    make_autonomous_prompt
)
from validators import LangGraphCodeValidator


def get_prompt() -> str:
    """Return the test prompt.

    This prompt tests whether the agent can:
    - Consult langchain-agents skill for modern patterns
    - Build a working SQL agent
    - Generate traces to LangSmith
    """
    return """Build a Python text-to-SQL agent using LangChain that can query the chinook.db SQLite database (in current directory).

The agent should:
- Use modern LangChain patterns
- Use ChatOpenAI with gpt-4o-mini
- Include proper error handling
- Only allow SELECT queries for safety

Save to sql_agent.py and run it with a few test queries to generate traces to LangSmith.

Do not ask clarifying questions."""


def run_test(work_dir: Path = None):
    """Run the autonomous test.

    Args:
        work_dir: Base working directory with deepagents installed (or None for default)
    """
    print("=" * 70)
    print("AUTONOMOUS TEST: SQL Agent Creation")
    print("=" * 70)
    print()

    # Get prompt and add summary requirement
    task_prompt = get_prompt()
    prompt = make_autonomous_prompt(task_prompt)
    print("PROMPT:")
    print("-" * 70)
    print(prompt)
    print("-" * 70)
    print()

    # Set up test environment (always creates temp directory)
    try:
        test_dir = setup_test_environment(work_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    print(f"Test directory: {test_dir}")
    print()

    # Copy chinook.db to test directory
    chinook_db = Path(__file__).parent / "chinook.db"
    copy_test_data(chinook_db, test_dir)
    print()

    runner = skills_root / "scaffold" / "runner.py"

    print("Running deepagents (this may take 60-300 seconds)...")
    print()

    try:
        returncode, stdout, stderr = run_deepagents_subprocess(
            agent_name="langchain_agent",
            prompt=prompt,
            test_dir=test_dir,
            runner_path=runner
            # timeout uses default (300s)
        )

        if stderr:
            print("STDERR:")
            print(stderr)
            print()

    except Exception as e:
        print(f"ERROR running test: {e}")
        if use_temp:
            cleanup_test_environment(test_dir)
        return 1

    # Find the output directory from stdout
    summary_file = extract_summary_path(stdout)
    if not summary_file or not summary_file.exists():
        print("ERROR: Could not find summary file")
        print("STDOUT:")
        print(stdout)
        if use_temp:
            cleanup_test_environment(test_dir)
        return 1

    print(f"✓ Output saved to: {summary_file}")
    print()

    # Read summary for display
    summary_content = summary_file.read_text()
    print("SESSION SUMMARY:")
    print("=" * 70)
    print(summary_content)
    print("=" * 70)
    print()

    # For validation, we need the raw output - read from parent directory
    log_dir = summary_file.parent
    # The runner doesn't save raw output anymore, so we'll work with the summary
    # For full validation, we'd need to parse the summary or run validations differently

    print("VALIDATION:")
    print("-" * 70)

    # Validate using LangGraphCodeValidator
    validator = LangGraphCodeValidator()
    validator.check_skill("langchain-agents", summary_content)
    validator.check_modern_patterns(summary_content)
    validator.check_legacy_patterns_avoided(summary_content)
    validator.check_agent_file(test_dir)
    validations_passed, validations_failed = validator.results()

    # Print results
    for v in validations_passed:
        print(v)
    for v in validations_failed:
        print(v)

    print("-" * 70)
    print()

    result = 0
    if validations_failed:
        print("RESULT: FAILED")
        print()
        print("Failed checks:")
        for v in validations_failed:
            print(f"  {v}")
        result = 1
    else:
        print("RESULT: PASSED")
        print(f"  All {len(validations_passed)} checks passed")
        result = 0

    # Always cleanup temp directory
    cleanup_test_environment(test_dir)

    return result


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Autonomous test for SQL agent creation"
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Working directory with deepagents installed (default: ~/Desktop/Projects/test)"
    )

    args = parser.parse_args()

    return run_test(work_dir=args.work_dir)


if __name__ == "__main__":
    sys.exit(main())
