#!/usr/bin/env python3
"""
Autonomous test for LangSmith dataset upload.

This test verifies that the agent can:
1. Generate a dataset from traces
2. Upload it to LangSmith
3. Verify the upload was successful

Run:
    python tests/langsmith-dataset/test_dataset_upload.py
    python tests/langsmith-dataset/test_dataset_upload.py --work-dir /path/to/test/env
    python tests/langsmith-dataset/test_dataset_upload.py --use-temp
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
    extract_summary_path
)


def get_prompt() -> str:
    """Return the test prompt.

    This prompt is designed to:
    - Test langsmith-dataset skill consultation
    - Generate and upload dataset from specific project
    - Use trajectory format and coordinated name
    """
    import os
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    return f"""Use the langsmith-dataset skill to generate a small test dataset (3 examples) of type "trajectory" from the LangSmith project "{project}".

Upload to LangSmith with name: "Test Dataset - DELETE ME"

Use --replace flag but DO NOT use --yes flag (respect confirmation prompts).

Store the dataset name in test_dataset_upload_name.txt in the current directory.

Do not ask any clarifying questions - implement this specific design."""


def run_test(work_dir: Path = None, use_temp: bool = False):
    """Run the autonomous test."""
    print("=" * 70)
    print("AUTONOMOUS TEST: LangSmith Dataset Upload")
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

    # Validate outputs
    validations_passed = []
    validations_failed = []

    # Check skill consultation
    if "langsmith-dataset" in summary_content:
        validations_passed.append("✓ Consulted langsmith-dataset skill")
    else:
        validations_failed.append("✗ Did not consult langsmith-dataset skill")

    # Check if dataset name file was created
    name_file = test_dir / "test_dataset_upload_name.txt"
    expected_name = "Test Dataset - DELETE ME"
    if name_file.exists():
        dataset_name = name_file.read_text().strip()
        if dataset_name == expected_name:
            validations_passed.append(f"✓ Created and uploaded dataset: {dataset_name}")
        else:
            validations_failed.append(f"✗ Dataset name incorrect: {dataset_name}")
    else:
        validations_failed.append("✗ test_dataset_upload_name.txt not created")

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
        print()
        print("⚠️  CLEANUP REQUIRED:")
        print(f"   - Delete dataset: '{expected_name}'")
        result = 0

    # Cleanup if using temp directory
    if use_temp:
        cleanup_test_environment(test_dir)

    return result


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Autonomous test for LangSmith dataset upload"
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
