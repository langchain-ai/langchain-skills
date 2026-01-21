#!/usr/bin/env python3
"""
Autonomous test for SQL agent creation using langgraph-code skill.

This test:
1. Defines a complete, specific prompt
2. Runs deepagents via scaffold/runner.py
3. Validates output against expected patterns
4. Reports results

Run:
    python tests/langgraph-code/test_sql_agent_autonomous.py
    python tests/langgraph-code/test_sql_agent_autonomous.py --work-dir /path/to/test/env
    python tests/langgraph-code/test_sql_agent_autonomous.py --use-temp
"""

import sys
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.fixtures import (
    setup_test_environment,
    cleanup_test_environment,
    run_deepagents_test,
    extract_summary_path,
    copy_test_data
)
from validators import LangGraphCodeValidator


def get_prompt() -> str:
    """Return the test prompt.

    This prompt is designed to:
    - Be specific and complete (no follow-up questions needed)
    - Test skill consultation
    - Require modern patterns
    - Avoid legacy patterns
    - Generate traces to LangSmith
    """
    return """Create a Python text-to-SQL agent using LangChain that can query a SQLite database.

Requirements:
- Use the chinook.db database (assume it exists in current directory)
- Use the @tool decorator from langchain_core.tools for database operations
- Use ChatAnthropic with claude-sonnet-4-5 model
- Use create_agent from langchain.agents (NOT the legacy create_sql_agent)
- Include a simple @tool function that executes SELECT queries only
- Add basic error handling for invalid queries

Save the complete agent code to a file called sql_agent.py.

After creating the agent, run it with 2-3 test queries to generate traces to LangSmith:
- "What are the top 5 albums?"
- "How many customers are there?"
- "List the first 3 tracks"

The agent will automatically trace to the LangSmith project specified in LANGSMITH_PROJECT environment variable.

Do not ask any clarifying questions - implement this specific design."""


def run_test(work_dir: Path = None, use_temp: bool = False):
    """Run the autonomous test.

    Args:
        work_dir: Working directory for test (or None for default)
        use_temp: If True, create temporary directory
    """
    print("=" * 70)
    print("AUTONOMOUS TEST: SQL Agent Creation")
    print("=" * 70)
    print()

    # Get prompt
    prompt = get_prompt()
    print("PROMPT:")
    print("-" * 70)
    print(prompt)
    print("-" * 70)
    print()

    # Set up test environment
    try:
        if work_dir:
            test_dir = setup_test_environment(work_dir, use_temp=use_temp)
        else:
            test_dir = setup_test_environment(use_temp=use_temp)
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

    print("Running deepagents (this may take 60-120 seconds)...")
    print()

    try:
        returncode, stdout, stderr = run_deepagents_test(
            agent_name="langchain_agent",
            prompt=prompt,
            test_dir=test_dir,
            runner_path=runner,
            timeout=180
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
    validator.check_skill("langgraph-code", summary_content)
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

    # Cleanup if using temp directory
    if use_temp:
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
    parser.add_argument(
        "--use-temp",
        action="store_true",
        help="Create temporary directory for isolated test"
    )

    args = parser.parse_args()

    return run_test(work_dir=args.work_dir, use_temp=args.use_temp)


if __name__ == "__main__":
    sys.exit(main())
