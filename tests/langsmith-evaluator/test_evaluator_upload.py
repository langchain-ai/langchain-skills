#!/usr/bin/env python3
"""
Autonomous test for LangSmith evaluator creation and upload.

This test verifies that the agent can:
1. Create a temporary dataset for testing
2. Create a valid evaluator function
3. Upload the evaluator using langsmith-evaluator skill

Run:
    python tests/langsmith-evaluator/test_evaluator_upload.py
    python tests/langsmith-evaluator/test_evaluator_upload.py --work-dir /path/to/test/env
"""

import sys
import ast
import argparse
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.setup import setup_test_environment, cleanup_test_environment
from scaffold.runner import run_autonomous_test, make_autonomous_prompt
from validators import EvaluatorValidator


def get_prompt() -> str:
    """Return the test prompt."""
    return """Create and upload a test evaluator to LangSmith.

Steps:
1. Verify the dataset "Test Dataset - DELETE ME" exists in LangSmith.
   - Store dataset name in test_evaluator_dataset_name.txt

2. Create a simple evaluator function in test_evaluator.py with:
   - Function name: test_length_check
   - Purpose: Check if output length is > 10 characters
   - Return format: {{"key": "length_check", "score": 1 if len > 10 else 0, "comment": "..."}}
   - Use (run, example) signature for LangSmith

3. Upload the evaluator to LangSmith (do not just run an experiment):
   - Use the upload script at: ~/.deepagents/langchain_agent/skills/langsmith-evaluator/scripts/upload_evaluators.py
   - Evaluator name: "Test Length Check - DELETE ME"
   - Attach to dataset: "Test Dataset - DELETE ME"
   - This creates a PERSISTENT evaluator, not a one-time experiment
   - Verify the upload succeeded

4. Store the evaluator name in test_evaluator_name.txt

Do not ask clarifying questions."""


def validate(summary_content: str, test_dir: Path) -> tuple[list[str], list[str]]:
    """Validate test results using EvaluatorValidator."""
    validator = EvaluatorValidator()
    validator.check_skill("langsmith-evaluator", summary_content)
    validator.check_dataset_verified(test_dir, "Test Dataset - DELETE ME")
    validator.check_dataset_in_langsmith("Test Dataset - DELETE ME")
    validator.check_evaluator_function(test_dir)
    validator.check_evaluator_recorded(test_dir, "Test Length Check - DELETE ME")
    validator.check_evaluator_in_langsmith("Test Length Check - DELETE ME")
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
        test_name="LangSmith Evaluator Upload",
        prompt=make_autonomous_prompt(get_prompt()),
        test_dir=test_dir,
        runner_path=runner,
        validate_func=validate
    )

    if result == 0:
        print("\n⚠️  CLEANUP REQUIRED:")
        print("   - Delete evaluator: 'Test Length Check - DELETE ME'")
        print("   - Delete dataset: 'Test Dataset - DELETE ME'")

    cleanup_test_environment(test_dir)
    return result


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Autonomous test for LangSmith evaluator upload"
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
