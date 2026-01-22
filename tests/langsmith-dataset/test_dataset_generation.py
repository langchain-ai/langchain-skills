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
import json
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.setup import setup_test_environment, cleanup_test_environment
from scaffold.runner import run_autonomous_test, make_autonomous_prompt
from validators import DatasetGenerationValidator


def get_prompt() -> str:
    """Return the test prompt."""
    import os
    project = os.environ.get("LANGSMITH_PROJECT", "skills")
    return f"""We are aiming to set up evaluations. Generate a small test dataset (5 examples) of type "final_response" from the LangSmith project "{project}".

Save the dataset to test_dataset.json in the current directory (do NOT upload to LangSmith).

Also create a file called test_dataset_info.txt with the project name and example count.

Do not ask clarifying questions."""


def validate(summary_content: str, test_dir: Path) -> tuple[list[str], list[str]]:
    """Validate test results using DatasetGenerationValidator."""
    validator = DatasetGenerationValidator()
    validator.check_skill("langsmith-dataset", summary_content)
    validator.check_dataset_json(test_dir)
    validator.check_info_file(test_dir)
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
        test_name="LangSmith Dataset Generation",
        prompt=make_autonomous_prompt(get_prompt()),
        test_dir=test_dir,
        runner_path=runner,
        validate_func=validate
    )

    # Always cleanup temp directory
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

    args = parser.parse_args()

    return run_test(work_dir=args.work_dir)


if __name__ == "__main__":
    sys.exit(main())
