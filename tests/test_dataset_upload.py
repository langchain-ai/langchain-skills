#!/usr/bin/env python3
"""
Test: Verify Claude Code can upload datasets to LangSmith

TASK FOR CLAUDE CODE:
====================
1. Use langsmith-dataset skill to generate a small test dataset (3 examples)
2. Dataset type: "trajectory"
3. From any available project with recent traces
4. Upload to LangSmith with name: "Test Dataset - DELETE ME"
5. Use --replace flag but DO NOT use --yes flag (respect confirmation prompts)
6. Store the dataset name in /tmp/test_dataset_upload_name.txt

IMPORTANT: The dataset will be named "Test Dataset - DELETE ME" so it can be
easily identified and cleaned up later.

VALIDATION:
===========
This script checks:
- The dataset name file was created
- The dataset exists in LangSmith
- The dataset has at least 1 example
- The dataset has correct structure (trajectory format)
"""

import os
import sys
from pathlib import Path
from langsmith import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    print("=" * 60)
    print("LangSmith Dataset Upload Test - Validation")
    print("=" * 60)

    # Check if name file exists
    name_file = Path("/tmp/test_dataset_upload_name.txt")
    if not name_file.exists():
        print("❌ FAILED: /tmp/test_dataset_upload_name.txt not found")
        print("   Claude Code should have created this file with dataset name")
        sys.exit(1)

    print("✓ Dataset name file exists")

    # Read dataset name
    dataset_name = name_file.read_text().strip()
    expected_name = "Test Dataset - DELETE ME"

    if dataset_name != expected_name:
        print(f"❌ FAILED: Expected dataset name '{expected_name}'")
        print(f"   Found: '{dataset_name}'")
        sys.exit(1)

    print(f"✓ Dataset name is correct: {dataset_name}")

    # Check if dataset exists in LangSmith
    try:
        client = Client()
        dataset = client.read_dataset(dataset_name=dataset_name)
    except Exception as e:
        print(f"❌ FAILED: Could not retrieve dataset from LangSmith")
        print(f"   Error: {e}")
        print("\n   Make sure:")
        print("   - The upload completed successfully")
        print("   - LANGSMITH_API_KEY is set correctly")
        sys.exit(1)

    print(f"✓ Dataset exists in LangSmith")
    print(f"  ID: {dataset.id}")
    print(f"  Name: {dataset.name}")

    # Get examples from dataset
    examples = list(client.list_examples(dataset_id=dataset.id))

    if len(examples) == 0:
        print("❌ FAILED: Dataset has no examples")
        sys.exit(1)

    print(f"✓ Dataset has {len(examples)} example(s)")

    # Validate first example structure (trajectory format)
    example = examples[0]

    # Check for required fields
    if not hasattr(example, 'inputs') or not hasattr(example, 'outputs'):
        print("❌ FAILED: Example missing inputs or outputs")
        sys.exit(1)

    print("✓ Example has required fields: inputs, outputs")

    # Check for trajectory in outputs
    if "expected_trajectory" not in example.outputs:
        print("❌ FAILED: Example outputs missing 'expected_trajectory' field")
        print(f"   Found output fields: {list(example.outputs.keys())}")
        sys.exit(1)

    print("✓ Example has 'expected_trajectory' in outputs")

    # Display sample
    print("\n" + "-" * 60)
    print("Sample from first example:")
    print(f"  Inputs keys: {list(example.inputs.keys())}")
    print(f"  Outputs keys: {list(example.outputs.keys())}")
    trajectory = example.outputs["expected_trajectory"]
    print(f"  Trajectory length: {len(trajectory)}")
    print(f"  Trajectory: {trajectory[:5]}..." if len(trajectory) > 5 else f"  Trajectory: {trajectory}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nClaude Code successfully:")
    print("- Used langsmith-dataset skill to generate a trajectory dataset")
    print("- Uploaded the dataset to LangSmith")
    print(f"- Dataset has {len(examples)} example(s) in LangSmith")
    print(f"\n⚠️  CLEANUP: Delete test dataset '{dataset_name}' when done")

if __name__ == "__main__":
    main()
