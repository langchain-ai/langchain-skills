#!/usr/bin/env python3
"""
Unified test suite for LangChain agent skills.

This suite runs all tests in dependency order with a shared LangSmith project:
1. langgraph-code - Creates and runs SQL agent (generates traces to test project)
2. langsmith-trace - Queries traces from test project
3. langsmith-dataset generation - Generates dataset from test project traces
4. langsmith-dataset upload - Uploads dataset with test name
5. langsmith-evaluator - Creates evaluator attached to test dataset

Environment variables:
- LANGSMITH_PROJECT: Set to "Skills Test - DELETE ME" for all tests
- Test artifacts use "DELETE ME" suffix for easy cleanup

All tests use a single shared environment. If any test fails, the suite exits.

Usage:
    python tests/run_test_suite.py
    python tests/run_test_suite.py --work-dir /path/to/test/env
    python tests/run_test_suite.py --use-temp
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime

# Skills root
skills_root = Path(__file__).parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.fixtures import (
    setup_test_environment,
    cleanup_test_environment
)

# Test project name for LangSmith
TEST_PROJECT = "Skills Test - DELETE ME"
TEST_DATASET_NAME = "Test Dataset - DELETE ME"
TEST_EVALUATOR_DATASET_NAME = "Evaluator Test Dataset - DELETE ME"
TEST_EVALUATOR_NAME = "Test Length Check - DELETE ME"

# Import test modules
sys.path.insert(0, str(skills_root / "tests" / "langgraph-code"))
sys.path.insert(0, str(skills_root / "tests" / "langsmith-trace"))
sys.path.insert(0, str(skills_root / "tests" / "langsmith-dataset"))
sys.path.insert(0, str(skills_root / "tests" / "langsmith-evaluator"))

from test_sql_agent_autonomous import run_test as run_langgraph_test
from test_trace_query import run_test as run_trace_test
from test_dataset_generation import run_test as run_dataset_gen_test
from test_dataset_upload import run_test as run_dataset_upload_test
from test_evaluator_upload import run_test as run_evaluator_test


def run_suite(work_dir: Path = None, use_temp: bool = False):
    """Run the complete test suite."""

    start_time = datetime.now()

    print("=" * 80)
    print("LANGCHAIN AGENT SKILLS - TEST SUITE")
    print("=" * 80)
    print()
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Set up shared test environment
    print("Setting up test environment...")
    try:
        if work_dir:
            test_dir = setup_test_environment(work_dir, use_temp=use_temp)
        else:
            test_dir = setup_test_environment(use_temp=use_temp)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    print(f"✓ Test environment ready: {test_dir}")
    print()

    # Set up environment variables for all tests
    print("Configuring LangSmith environment...")
    os.environ["LANGSMITH_PROJECT"] = TEST_PROJECT
    print(f"✓ LANGSMITH_PROJECT = {TEST_PROJECT}")
    print()

    # Define test suite in dependency order
    tests = [
        {
            "name": "LangGraph Code",
            "description": "Create SQL agent using modern patterns",
            "function": run_langgraph_test
        },
        {
            "name": "LangSmith Trace Query",
            "description": "Query and extract recent traces",
            "function": run_trace_test
        },
        {
            "name": "LangSmith Dataset Generation",
            "description": "Generate dataset from traces (no upload)",
            "function": run_dataset_gen_test
        },
        {
            "name": "LangSmith Dataset Upload",
            "description": "Generate and upload dataset",
            "function": run_dataset_upload_test
        },
        {
            "name": "LangSmith Evaluator Upload",
            "description": "Create and upload evaluator",
            "function": run_evaluator_test
        }
    ]

    results = []
    failed_test = None

    # Run tests in order
    for i, test in enumerate(tests, 1):
        print("=" * 80)
        print(f"TEST {i}/{len(tests)}: {test['name']}")
        print(f"Description: {test['description']}")
        print("=" * 80)
        print()

        try:
            # Pass work_dir but not use_temp (we already set up the environment)
            result = test["function"](work_dir=test_dir, use_temp=False)
            results.append((test["name"], result))

            if result != 0:
                failed_test = test["name"]
                print()
                print(f"✗ TEST FAILED: {test['name']}")
                print()
                print("Aborting test suite due to failure.")
                print("Later tests depend on earlier tests passing.")
                break
            else:
                print()
                print(f"✓ TEST PASSED: {test['name']}")
                print()

        except Exception as e:
            print()
            print(f"✗ TEST ERROR: {test['name']}")
            print(f"Exception: {e}")
            results.append((test["name"], 1))
            failed_test = test["name"]
            break

    # Print summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print()
    print("=" * 80)
    print("TEST SUITE SUMMARY")
    print("=" * 80)
    print()
    print(f"Duration: {duration:.1f}s")
    print(f"Tests run: {len(results)}/{len(tests)}")
    print()

    passed = sum(1 for _, result in results if result == 0)
    failed = sum(1 for _, result in results if result != 0)

    print("Results:")
    for name, result in results:
        status = "✓ PASS" if result == 0 else "✗ FAIL"
        print(f"  {status} - {name}")

    if failed_test:
        print()
        print("=" * 80)
        print(f"SUITE FAILED at: {failed_test}")
        print("=" * 80)
        final_result = 1
    else:
        print()
        print("=" * 80)
        print("ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("⚠️  CLEANUP REQUIRED:")
        print("   - Delete evaluator: 'Test Length Check - DELETE ME'")
        print("   - Delete dataset: 'Evaluator Test Dataset - DELETE ME'")
        print("   - Delete dataset: 'Test Dataset - DELETE ME'")
        final_result = 0

    # Cleanup if using temp directory
    if use_temp:
        print()
        print("Cleaning up temporary test environment...")
        cleanup_test_environment(test_dir)

    return final_result


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Run complete test suite for LangChain agent skills"
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

    return run_suite(work_dir=args.work_dir, use_temp=args.use_temp)


if __name__ == "__main__":
    sys.exit(main())
