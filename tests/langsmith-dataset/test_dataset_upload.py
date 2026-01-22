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
"""

import sys
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.setup import setup_test_environment, cleanup_test_environment
from scaffold.runner import run_autonomous_test, make_autonomous_prompt
from validators import DatasetUploadValidator


def get_prompt() -> str:
    """Return the test prompt."""
    import os
    project = os.environ.get("LANGSMITH_PROJECT", "skills")
    return f"""Generate a small test dataset (3 examples) of type "trajectory" from the LangSmith project "{project}".

Upload to LangSmith with name: "Test Dataset - DELETE ME"

Replace any existing dataset with the same name.

Store the dataset name in test_dataset_upload_name.txt in the current directory.

IMPORTANT: Actually perform the upload - don't just create a script, execute it and verify the dataset is uploaded to LangSmith.

Do not ask clarifying questions."""


def validate(summary_content: str, test_dir: Path) -> tuple[list[str], list[str]]:
    """Validate test results using DatasetUploadValidator."""
    validator = DatasetUploadValidator()
    validator.check_skill("langsmith-dataset", summary_content)
    validator.check_dataset_uploaded(test_dir, "Test Dataset - DELETE ME")
    validator.check_dataset_in_langsmith("Test Dataset - DELETE ME")
    return validator.results()


def run_test(work_dir: Path = None):
    """Run the autonomous test."""
    try:
        test_dir = setup_test_environment(work_dir)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    runner = skills_root / "scaffold" / "runner.py"

    result = run_autonomous_test(
        test_name="LangSmith Dataset Upload",
        prompt=make_autonomous_prompt(get_prompt()),
        test_dir=test_dir,
        runner_path=runner,
        validate_func=validate
    )

    if result == 0:
        print("\n⚠️  CLEANUP REQUIRED:")
        print("   - Delete dataset: 'Test Dataset - DELETE ME'")

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

    args = parser.parse_args()

    return run_test(work_dir=args.work_dir)


if __name__ == "__main__":
    sys.exit(main())
