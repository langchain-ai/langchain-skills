#!/usr/bin/env python3
"""
Unified test suite for LangChain agent skills.

Runs all tests sequentially in dependency order:
1. langchain-agents - Creates and runs SQL agent (generates traces)
2. langsmith-trace - Queries traces from test project
3. langsmith-dataset generation - Generates dataset from traces
4. langsmith-dataset upload - Uploads dataset with test name
5. langsmith-evaluator - Creates evaluator attached to test dataset

Each test uses an isolated temporary directory for safety.
LangSmith artifacts are cleaned up at the end automatically.

Usage:
    uv run python tests/run_test_suite.py
    uv run python tests/run_test_suite.py --work-dir /path/to/test/env
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent.parent / ".env")

# Skills root
skills_root = Path(__file__).parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.cleanup import cleanup_langsmith_assets


def run_test_script(test_path: Path, work_dir: Path = None) -> int:
    """Run a test script as a subprocess."""
    cmd = ["uv", "run", "python", str(test_path)]
    if work_dir:
        cmd.extend(["--work-dir", str(work_dir)])

    result = subprocess.run(cmd, cwd=str(skills_root))

    # Clean up local files after each test (temp dirs handle their own cleanup)
    print("Cleaning up local test files...")
    cleanup_cmd = ["uv", "run", "python", "scaffold/cleanup.py", "--local"]
    subprocess.run(cleanup_cmd, cwd=str(skills_root), capture_output=True)

    return result.returncode


def run_suite(work_dir: Path = None):
    """Run the complete test suite.

    Args:
        work_dir: Base environment with deepagents installed (or None for default)
    """

    start_time = datetime.now()

    print("=" * 80)
    print("LANGCHAIN AGENT SKILLS - TEST SUITE")
    print("=" * 80)
    print()
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Each test runs in an isolated temporary directory.")
    print()

    # Define test suite in dependency order
    tests = [
        {
            "name": "LangGraph Code",
            "description": "Create SQL agent using modern patterns",
            "path": skills_root / "tests" / "langchain-agents" / "test_create_agent.py"
        },
        {
            "name": "LangSmith Trace Query",
            "description": "Query and extract recent traces",
            "path": skills_root / "tests" / "langsmith-trace" / "test_trace_query.py"
        },
        {
            "name": "LangSmith Dataset Generation",
            "description": "Generate dataset from traces (no upload)",
            "path": skills_root / "tests" / "langsmith-dataset" / "test_dataset_generation.py"
        },
        {
            "name": "LangSmith Dataset Upload",
            "description": "Generate and upload dataset",
            "path": skills_root / "tests" / "langsmith-dataset" / "test_dataset_upload.py"
        },
        {
            "name": "LangSmith Evaluator Upload",
            "description": "Create and upload evaluator",
            "path": skills_root / "tests" / "langsmith-evaluator" / "test_evaluator_upload.py"
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
            result = run_test_script(test["path"], work_dir)
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
        final_result = 0

    # Cleanup LangSmith assets
    print()
    print("Cleaning up LangSmith test assets...")
    cleanup_langsmith_assets()

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

    args = parser.parse_args()

    return run_suite(work_dir=args.work_dir)


if __name__ == "__main__":
    sys.exit(main())
