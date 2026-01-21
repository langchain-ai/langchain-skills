#!/usr/bin/env python3
"""
Autonomous test for LangSmith trace querying.

This test verifies that the agent can:
1. Use langsmith-trace skill to query recent traces
2. Extract trace details
3. Save trace ID for validation

Run:
    python tests/langsmith-trace/test_trace_query.py
    python tests/langsmith-trace/test_trace_query.py --work-dir /path/to/test/env
    python tests/langsmith-trace/test_trace_query.py --use-temp
"""

import sys
import re
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.fixtures import (
    setup_test_environment,
    cleanup_test_environment,
    run_autonomous_test
)
from scaffold.validators import TestValidator


def get_prompt() -> str:
    """Return the test prompt."""
    import os
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    return f"""Use the langsmith-trace skill to list the 5 most recent traces from the LangSmith project "{project}".

Then, get details about the first trace (most recent one).

Save the trace ID to a file called test_trace_id.txt in the current directory.

Do not ask any clarifying questions - implement this specific design."""


def validate(summary_content: str, test_dir: Path) -> tuple[list[str], list[str]]:
    """Validate test results using TestValidator."""
    validator = TestValidator()
    validator.check_skill("langsmith-trace", summary_content)
    validator.check_file_exists("test_trace_id.txt", test_dir, "trace ID file")
    validator.check_uuid_format("test_trace_id.txt", test_dir)
    return validator.results()


def run_test(work_dir: Path = None, use_temp: bool = False):
    """Run the autonomous test."""
    # Set up test environment
    try:
        if work_dir:
            test_dir = setup_test_environment(work_dir, use_temp=use_temp)
        else:
            test_dir = setup_test_environment(use_temp=use_temp)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    runner = skills_root / "scaffold" / "runner.py"

    # Run test using helper
    result = run_autonomous_test(
        test_name="LangSmith Trace Query",
        prompt=get_prompt(),
        test_dir=test_dir,
        runner_path=runner,
        validate_func=validate,
        timeout=180
    )

    # Cleanup if using temp directory
    if use_temp:
        cleanup_test_environment(test_dir)

    return result


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Autonomous test for LangSmith trace querying"
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
