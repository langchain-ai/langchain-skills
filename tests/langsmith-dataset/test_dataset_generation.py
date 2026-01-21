#!/usr/bin/env python3
"""
Autonomous test for LangSmith dataset generation.

This test verifies that the agent can:
1. Use langsmith-dataset skill to list existing datasets
2. Generate a dataset from traces
3. Save it without uploading to LangSmith

Run:
    python tests/langsmith-dataset/test_dataset_generation.py
    python tests/langsmith-dataset/test_dataset_generation.py --work-dir /path/to/test/env
    python tests/langsmith-dataset/test_dataset_generation.py --use-temp
"""

import sys
import json
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.fixtures import (
    setup_test_environment,
    cleanup_test_environment,
    run_deepagents_test,
    extract_summary_path
)
from validators import DatasetGenerationValidator


def get_prompt() -> str:
    """Return the test prompt.

    This prompt is designed to:
    - Test langsmith-dataset skill consultation
    - Generate dataset from specific project
    - Save without uploading
    """
    import os
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    return f"""Use the langsmith-dataset skill to generate a small test dataset (5 examples) of type "final_response" from the LangSmith project "{project}".

Save the dataset to test_dataset.json in the current directory (do NOT upload to LangSmith).

Also create a file called test_dataset_info.txt with the project name and example count.

Do not ask any clarifying questions - implement this specific design."""


def run_test(work_dir: Path = None, use_temp: bool = False):
    """Run the autonomous test."""
    print("=" * 70)
    print("AUTONOMOUS TEST: LangSmith Dataset Generation")
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

    print("VALIDATION:")
    print("-" * 70)

    # Validate using DatasetGenerationValidator
    validator = DatasetGenerationValidator()
    validator.check_skill("langsmith-dataset", summary_content)
    validator.check_dataset_json(test_dir)
    validator.check_info_file(test_dir)
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
        description="Autonomous test for LangSmith dataset generation"
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
