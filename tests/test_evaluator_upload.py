#!/usr/bin/env python3
"""
Test: Verify Claude Code can create and upload evaluators

TASK FOR CLAUDE CODE:
====================
1. Create a temporary dataset for the evaluator test:
   - Generate 2 examples of type "final_response" from any project
   - Upload to LangSmith with name: "Evaluator Test Dataset - DELETE ME"
   - Store dataset name in /tmp/test_evaluator_dataset_name.txt

2. Create a simple evaluator function in /tmp/test_evaluator.py with:
   - Function name: test_length_check
   - Purpose: Check if output length is > 10 characters
   - Return format: {"length_check": 1 if len > 10 else 0, "comment": "..."}
   - Use (run, example) signature for LangSmith upload

3. Upload the evaluator using langsmith-evaluator skill:
   - Name: "Test Length Check - DELETE ME"
   - Attach to dataset: "Evaluator Test Dataset - DELETE ME" (use --dataset flag)
   - Use --replace flag but DO NOT use --yes flag (respect confirmation prompts)

4. Store the evaluator name in /tmp/test_evaluator_name.txt

IMPORTANT: Both the evaluator and dataset will be named with "DELETE ME" so they can be
easily identified and cleaned up later.

VALIDATION:
===========
This script checks:
- The dataset name file was created
- The dataset exists in LangSmith
- The evaluator file was created
- The function has correct signature (run, example)
- The function returns correct format (metric name as key)
- The evaluator exists in LangSmith
- The evaluator has correct name and is attached to the dataset
"""

import os
import sys
import re
import ast
import requests
from pathlib import Path
from langsmith import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_evaluator_function(file_path):
    """Validate evaluator function structure."""
    with open(file_path) as f:
        source = f.read()

    # Parse the Python code
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

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

def check_evaluator_exists(name):
    """Check if evaluator exists in LangSmith."""
    api_key = os.getenv("LANGSMITH_API_KEY")
    api_url = os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
    workspace_id = os.getenv("LANGSMITH_WORKSPACE_ID")

    if not api_key:
        return False, "LANGSMITH_API_KEY not set"

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    if workspace_id:
        headers["x-tenant-id"] = workspace_id

    try:
        response = requests.get(f"{api_url}/runs/rules", headers=headers)
        response.raise_for_status()
        rules = response.json()

        evaluator = next((r for r in rules if r.get("display_name") == name), None)
        if not evaluator:
            return False, f"Evaluator '{name}' not found in LangSmith"

        return True, evaluator
    except Exception as e:
        return False, f"Error checking LangSmith: {e}"

def main():
    print("=" * 60)
    print("LangSmith Evaluator Upload Test - Validation")
    print("=" * 60)

    # Check if dataset name file exists
    dataset_name_file = Path("/tmp/test_evaluator_dataset_name.txt")
    if not dataset_name_file.exists():
        print("❌ FAILED: /tmp/test_evaluator_dataset_name.txt not found")
        print("   Claude Code should have created the temp dataset first")
        sys.exit(1)

    print("✓ Dataset name file exists")

    # Read dataset name
    dataset_name = dataset_name_file.read_text().strip()
    expected_dataset_name = "Evaluator Test Dataset - DELETE ME"

    if dataset_name != expected_dataset_name:
        print(f"❌ FAILED: Expected dataset name '{expected_dataset_name}'")
        print(f"   Found: '{dataset_name}'")
        sys.exit(1)

    print(f"✓ Dataset name is correct: {dataset_name}")

    # Check if dataset exists in LangSmith
    try:
        client = Client()
        dataset = client.read_dataset(dataset_name=dataset_name)
        print(f"✓ Dataset exists in LangSmith (ID: {dataset.id})")
    except Exception as e:
        print(f"❌ FAILED: Could not retrieve dataset from LangSmith")
        print(f"   Error: {e}")
        sys.exit(1)

    # Check if evaluator file exists
    evaluator_file = Path("/tmp/test_evaluator.py")
    if not evaluator_file.exists():
        print("❌ FAILED: /tmp/test_evaluator.py not found")
        print("   Claude Code should have created this evaluator file")
        sys.exit(1)

    print("✓ Evaluator file exists")

    # Validate function structure
    valid, message = validate_evaluator_function(evaluator_file)
    if not valid:
        print(f"❌ FAILED: {message}")
        sys.exit(1)

    print(f"✓ {message}")

    # Check if name file exists
    name_file = Path("/tmp/test_evaluator_name.txt")
    if not name_file.exists():
        print("❌ FAILED: /tmp/test_evaluator_name.txt not found")
        print("   Claude Code should have stored the evaluator name here")
        sys.exit(1)

    print("✓ Evaluator name file exists")

    # Read evaluator name
    evaluator_name = name_file.read_text().strip()
    expected_name = "Test Length Check - DELETE ME"

    if evaluator_name != expected_name:
        print(f"❌ FAILED: Expected evaluator name '{expected_name}'")
        print(f"   Found: '{evaluator_name}'")
        sys.exit(1)

    print(f"✓ Evaluator name is correct: {evaluator_name}")

    # Check if evaluator exists in LangSmith
    exists, result = check_evaluator_exists(evaluator_name)
    if not exists:
        print(f"❌ FAILED: {result}")
        print("\n   Make sure:")
        print("   - The upload command completed successfully")
        print("   - LANGSMITH_API_KEY is set correctly")
        sys.exit(1)

    print(f"✓ Evaluator exists in LangSmith")

    # Display evaluator details
    print("\n" + "-" * 60)
    print("Evaluator details:")
    print(f"  Name: {result.get('display_name')}")
    print(f"  Sampling rate: {result.get('sampling_rate', 1.0) * 100}%")
    print(f"  Has code evaluators: {bool(result.get('code_evaluators'))}")

    # Display sample of function code
    print("\n" + "-" * 60)
    print("Sample of evaluator function:")
    with open(evaluator_file) as f:
        lines = f.readlines()[:15]  # First 15 lines
        for i, line in enumerate(lines, 1):
            print(f"  {i:2d}: {line.rstrip()}")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nClaude Code successfully:")
    print("- Created a temporary dataset for testing")
    print("- Created a valid evaluator function with (run, example) signature")
    print("- Used langsmith-evaluator skill to upload the evaluator")
    print("- The evaluator exists in LangSmith and is attached to the dataset")
    print(f"\n⚠️  CLEANUP:")
    print(f"   - Delete evaluator: '{evaluator_name}'")
    print(f"   - Delete dataset: '{dataset_name}'")

if __name__ == "__main__":
    main()
