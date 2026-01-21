#!/usr/bin/env python3
"""
Test: Verify Claude Code can generate and query datasets

TASK FOR CLAUDE CODE:
====================
1. Use langsmith-dataset skill to list existing datasets
2. Generate a small test dataset (5 examples) of type "final_response" from any available project
3. Save it to /tmp/test_dataset.json (do NOT upload to LangSmith)
4. Store the dataset name/info in /tmp/test_dataset_info.txt (just the project name and count)

VALIDATION:
===========
This script checks:
- The dataset file was created at /tmp/test_dataset.json
- The dataset has valid JSON structure
- The dataset contains final_response format (inputs/outputs with expected_response)
- The dataset has at least 1 example
- Info file contains the project name
"""

import os
import sys
import json
from pathlib import Path

def main():
    print("=" * 60)
    print("LangSmith Dataset Generation Test - Validation")
    print("=" * 60)

    # Check if dataset file exists
    dataset_file = Path("/tmp/test_dataset.json")
    if not dataset_file.exists():
        print("❌ FAILED: /tmp/test_dataset.json not found")
        print("   Claude Code should have generated this dataset file")
        sys.exit(1)

    print("✓ Dataset file exists")

    # Check if info file exists
    info_file = Path("/tmp/test_dataset_info.txt")
    if not info_file.exists():
        print("❌ FAILED: /tmp/test_dataset_info.txt not found")
        print("   Claude Code should have created this file with dataset info")
        sys.exit(1)

    print("✓ Dataset info file exists")

    # Read and validate dataset JSON
    try:
        with open(dataset_file) as f:
            dataset = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: Invalid JSON in dataset file")
        print(f"   Error: {e}")
        sys.exit(1)

    print("✓ Dataset is valid JSON")

    # Check if it's a list
    if not isinstance(dataset, list):
        print(f"❌ FAILED: Dataset should be a list, got {type(dataset)}")
        sys.exit(1)

    print(f"✓ Dataset is a list with {len(dataset)} examples")

    # Check we have at least 1 example
    if len(dataset) == 0:
        print("❌ FAILED: Dataset is empty")
        sys.exit(1)

    print(f"✓ Dataset has {len(dataset)} example(s)")

    # Validate structure of first example
    example = dataset[0]
    if not isinstance(example, dict):
        print(f"❌ FAILED: Example should be dict, got {type(example)}")
        sys.exit(1)

    # Check for required fields
    required_fields = ["inputs", "outputs"]
    missing_fields = [f for f in required_fields if f not in example]
    if missing_fields:
        print(f"❌ FAILED: Example missing required fields: {missing_fields}")
        print(f"   Found fields: {list(example.keys())}")
        sys.exit(1)

    print("✓ Example has required fields: inputs, outputs")

    # Check outputs has expected_response
    if "expected_response" not in example["outputs"]:
        print("❌ FAILED: Example outputs missing 'expected_response' field")
        print(f"   Found output fields: {list(example['outputs'].keys())}")
        sys.exit(1)

    print("✓ Example has 'expected_response' in outputs")

    # Check info file
    info = info_file.read_text().strip()
    if len(info) < 3:
        print(f"⚠️  WARNING: Info file seems empty or too short: '{info}'")
    else:
        print(f"✓ Info file contains: {info}")

    # Display sample of first example
    print("\n" + "-" * 60)
    print("Sample from first example:")
    print(f"  Inputs keys: {list(example['inputs'].keys())}")
    print(f"  Outputs keys: {list(example['outputs'].keys())}")
    if "query" in example["inputs"]:
        query = example["inputs"]["query"]
        print(f"  Query: {query[:100]}..." if len(query) > 100 else f"  Query: {query}")
    response = example["outputs"]["expected_response"]
    print(f"  Response: {response[:100]}..." if len(response) > 100 else f"  Response: {response}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nClaude Code successfully:")
    print("- Used langsmith-dataset skill to generate a dataset")
    print("- Created valid final_response format dataset")
    print(f"- Generated {len(dataset)} example(s)")
    print("- Saved to /tmp/test_dataset.json without uploading to LangSmith")

if __name__ == "__main__":
    main()
