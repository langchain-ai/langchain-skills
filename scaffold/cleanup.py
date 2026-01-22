#!/usr/bin/env python3
"""
Cleanup utilities and CLI for test assets.

Library usage:
    from scaffold.cleanup import cleanup_test_files, cleanup_langsmith_assets
    cleanup_test_files(test_dir)
    cleanup_langsmith_assets()

CLI usage:
    uv run python scaffold/cleanup.py              # Clean both LangSmith and local files
    uv run python scaffold/cleanup.py --langsmith  # Clean only LangSmith
    uv run python scaffold/cleanup.py --local      # Clean only local files
"""

import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")


def cleanup_test_files(test_dir: Path):
    """Clean up test artifact files from test directory.

    Removes files like agent_summary.txt, test_*.txt, test_*.json, etc.
    Does not remove the directory itself or .venv.

    Args:
        test_dir: Test directory to clean
    """
    patterns = [
        "agent_summary.txt",
        "test_*.txt",
        "test_*.json",
        "test_*.py",
        "upload_dataset.py",
        "sql_agent.py",
        "create_upload_langsmith.py",
        "upload_evaluator_script.py"
    ]

    deleted_count = 0
    for pattern in patterns:
        for file in test_dir.glob(pattern):
            try:
                file.unlink()
                deleted_count += 1
                print(f"  ✓ Deleted: {file.name}")
            except Exception as e:
                print(f"  ⚠ Could not delete {file.name}: {e}")

    if deleted_count == 0:
        print("  (no test files found)")


def cleanup_langsmith_assets():
    """Clean up test datasets and evaluators from LangSmith.

    Deletes datasets with names ending in "DELETE ME".
    Requires LANGSMITH_API_KEY in environment.
    """
    try:
        from langsmith import Client
        client = Client()

        test_dataset_names = [
            "Test Dataset - DELETE ME",
            "Evaluator Test Dataset - DELETE ME"
        ]

        deleted_count = 0
        for dataset_name in test_dataset_names:
            try:
                datasets = list(client.list_datasets(dataset_name=dataset_name))
                for dataset in datasets:
                    client.delete_dataset(dataset_id=dataset.id)
                    deleted_count += 1
                    print(f"  ✓ Deleted dataset: {dataset.name}")
            except Exception as e:
                print(f"  ⚠ Could not delete dataset '{dataset_name}': {e}")

        if deleted_count == 0:
            print("  (no test datasets found)")

    except Exception as e:
        print(f"  ⚠ LangSmith cleanup failed: {e}")


def main():
    parser = argparse.ArgumentParser(description="Clean up test assets")
    parser.add_argument("--langsmith", action="store_true", help="Clean only LangSmith assets")
    parser.add_argument("--local", action="store_true", help="Clean only local test files")
    parser.add_argument("--test-dir", type=Path, default=Path.home() / "Desktop" / "Projects" / "test",
                        help="Test directory to clean (default: ~/Desktop/Projects/test)")

    args = parser.parse_args()

    # Default: clean both if no flags specified
    clean_langsmith = args.langsmith or not (args.langsmith or args.local)
    clean_local = args.local or not (args.langsmith or args.local)

    if clean_langsmith:
        print("Cleaning up LangSmith assets...")
        cleanup_langsmith_assets()
        print("✓ LangSmith cleanup complete\n")

    if clean_local:
        test_dir = args.test_dir
        if test_dir.exists():
            print(f"Cleaning up test files in: {test_dir}")
            cleanup_test_files(test_dir)
            print("✓ Local cleanup complete\n")
        else:
            print(f"⚠ Test directory not found: {test_dir}\n")

    print("✓ Cleanup complete")


if __name__ == "__main__":
    main()
