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
    python tests/langsmith-evaluator/test_evaluator_upload.py --use-temp
"""

import sys
import ast
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
    - Test langsmith-evaluator skill consultation
    - Create dataset and evaluator from specific project
    - Use coordinated names for cleanup
    """
    import os
    project = os.environ.get("LANGSMITH_PROJECT", "default")
    return f"""Create a test evaluator and upload it to LangSmith.

Steps:
1. First, create a temporary dataset for testing:
   - Generate 2 examples of type "final_response" from the LangSmith project "{project}"
   - Upload to LangSmith with name: "Evaluator Test Dataset - DELETE ME"
   - Store dataset name in test_evaluator_dataset_name.txt

2. Create a simple evaluator function in test_evaluator.py with:
   - Function name: test_length_check
   - Purpose: Check if output length is > 10 characters
   - Return format: {{"length_check": 1 if len > 10 else 0, "comment": "..."}}
   - Use (run, example) signature for LangSmith upload

3. Upload the evaluator using langsmith-evaluator skill:
   - Name: "Test Length Check - DELETE ME"
   - Attach to dataset: "Evaluator Test Dataset - DELETE ME"
   - Use --replace flag but DO NOT use --yes flag

4. Store the evaluator name in test_evaluator_name.txt

Do not ask any clarifying questions - implement this specific design."""


def validate_evaluator_function(file_path):
    """Validate evaluator function structure."""
    try:
        with open(file_path) as f:
            source = f.read()

        # Parse the Python code
        tree = ast.parse(source)

        # Find function definitions
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        if not functions:
            return False, "No functions found"

        # Find the test_length_check function
        func = next((f for f in functions if f.name == "test_length_check"), None)
        if not func:
            return False, "Function 'test_length_check' not found"

        # Check signature - should have 2 parameters (run, example)
        if len(func.args.args) != 2:
            return False, f"Function should have 2 parameters, found {len(func.args.args)}"

        param_names = [arg.arg for arg in func.args.args]
        expected_params = ["run", "example"]
        if param_names != expected_params:
            return False, f"Parameters should be (run, example), found {param_names}"

        return True, "Function structure is valid"
    except Exception as e:
        return False, f"Error validating function: {e}"


def run_test(work_dir: Path = None, use_temp: bool = False):
    """Run the autonomous test."""
    print("=" * 70)
    print("AUTONOMOUS TEST: LangSmith Evaluator Upload")
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

    print("Running deepagents (this may take 120-180 seconds due to uploads)...")
    print()

    try:
        returncode, stdout, stderr = run_deepagents_test(
            agent_name="langchain_agent",
            prompt=prompt,
            test_dir=test_dir,
            runner_path=runner,
            timeout=300  # Longer timeout for uploads
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
    if "langsmith-evaluator" in summary_content:
        validations_passed.append("✓ Consulted langsmith-evaluator skill")
    else:
        validations_failed.append("✗ Did not consult langsmith-evaluator skill")

    # Check dataset name file
    dataset_name_file = test_dir / "test_evaluator_dataset_name.txt"
    expected_dataset_name = "Evaluator Test Dataset - DELETE ME"
    if dataset_name_file.exists():
        dataset_name = dataset_name_file.read_text().strip()
        if dataset_name == expected_dataset_name:
            validations_passed.append(f"✓ Created dataset: {dataset_name}")
        else:
            validations_failed.append(f"✗ Dataset name incorrect: {dataset_name}")
    else:
        validations_failed.append("✗ test_evaluator_dataset_name.txt not created")

    # Check evaluator file
    evaluator_file = test_dir / "test_evaluator.py"
    if evaluator_file.exists():
        validations_passed.append("✓ Created test_evaluator.py")

        # Validate function structure
        valid, message = validate_evaluator_function(evaluator_file)
        if valid:
            validations_passed.append(f"✓ {message}")
        else:
            validations_failed.append(f"✗ {message}")
    else:
        validations_failed.append("✗ test_evaluator.py not created")

    # Check evaluator name file
    name_file = test_dir / "test_evaluator_name.txt"
    expected_name = "Test Length Check - DELETE ME"
    if name_file.exists():
        evaluator_name = name_file.read_text().strip()
        if evaluator_name == expected_name:
            validations_passed.append(f"✓ Created evaluator: {evaluator_name}")
        else:
            validations_failed.append(f"✗ Evaluator name incorrect: {evaluator_name}")
    else:
        validations_failed.append("✗ test_evaluator_name.txt not created")

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
        print(f"   - Delete evaluator: '{expected_name}'")
        print(f"   - Delete dataset: '{expected_dataset_name}'")
        result = 0

    # Cleanup if using temp directory
    if use_temp:
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
    parser.add_argument(
        "--use-temp",
        action="store_true",
        help="Create temporary directory for isolated test"
    )

    args = parser.parse_args()

    return run_test(work_dir=args.work_dir, use_temp=args.use_temp)


if __name__ == "__main__":
    sys.exit(main())
