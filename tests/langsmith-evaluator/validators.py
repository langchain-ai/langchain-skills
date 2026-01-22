"""
LangSmith evaluator test validators.
"""

import sys
import ast
import os
from pathlib import Path
from langsmith import Client

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.validators import TestValidator


class EvaluatorValidator(TestValidator):
    """Validator for evaluator upload tests."""

    def __init__(self):
        """Initialize validator with LangSmith client."""
        super().__init__()
        try:
            self.client = Client()
        except Exception:
            self.client = None

    def check_evaluator_function(self, test_dir: Path) -> 'EvaluatorValidator':
        """Check that evaluator function was created with correct structure.

        Args:
            test_dir: Test directory to check in

        Returns:
            self for chaining
        """
        file_path = test_dir / "test_evaluator.py"
        if not file_path.exists():
            self.failed.append("✗ test_evaluator.py not found")
            return self

        self.passed.append("✓ Created test_evaluator.py")

        try:
            with open(file_path) as f:
                source = f.read()

            # Parse the Python code
            tree = ast.parse(source)

            # Find function definitions
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

            if not functions:
                self.failed.append("✗ No functions found in evaluator")
                return self

            # Find the test_length_check function
            func = next((f for f in functions if f.name == "test_length_check"), None)
            if not func:
                self.failed.append("✗ Function 'test_length_check' not found")
                return self

            # Check signature - should have 2 parameters (run, example)
            if len(func.args.args) != 2:
                self.failed.append(f"✗ Function should have 2 parameters, found {len(func.args.args)}")
                return self

            param_names = [arg.arg for arg in func.args.args]
            expected_params = ["run", "example"]
            if param_names != expected_params:
                self.failed.append(f"✗ Parameters should be (run, example), found {param_names}")
                return self

            self.passed.append("✓ Function has correct signature (run, example)")

        except Exception as e:
            self.failed.append(f"✗ Error validating function: {e}")

        return self

    def check_dataset_verified(self, test_dir: Path, expected_name: str) -> 'EvaluatorValidator':
        """Check that dataset was verified for evaluator.

        Args:
            test_dir: Test directory to check in
            expected_name: Expected dataset name

        Returns:
            self for chaining
        """
        def check_name(content: str):
            if content == expected_name:
                return True, f"Dataset verified: {content}"
            return False, f"Dataset name incorrect: {content} (expected {expected_name})"

        return self.check_file_content("test_evaluator_dataset_name.txt", test_dir, check_name)

    def check_evaluator_recorded(self, test_dir: Path, expected_name: str) -> 'EvaluatorValidator':
        """Check that evaluator name was recorded to file.

        Args:
            test_dir: Test directory to check in
            expected_name: Expected evaluator name

        Returns:
            self for chaining
        """
        def check_name(content: str):
            if content == expected_name:
                return True, f"Evaluator name recorded: {content}"
            return False, f"Evaluator name incorrect: {content} (expected {expected_name})"

        return self.check_file_content("test_evaluator_name.txt", test_dir, check_name)

    def check_dataset_in_langsmith(self, dataset_name: str) -> 'EvaluatorValidator':
        """Check that dataset exists in LangSmith.

        Args:
            dataset_name: Expected dataset name

        Returns:
            self for chaining
        """
        if not self.client:
            self.failed.append("✗ LangSmith client not available")
            return self

        try:
            datasets = list(self.client.list_datasets(dataset_name=dataset_name))
            if datasets:
                self.passed.append(f"✓ Dataset exists in LangSmith: {dataset_name}")
            else:
                self.failed.append(f"✗ Dataset not found in LangSmith: {dataset_name}")
        except Exception as e:
            self.failed.append(f"✗ Error checking LangSmith for dataset: {e}")

        return self

    def check_evaluator_in_langsmith(self, evaluator_name: str) -> 'EvaluatorValidator':
        """Check that evaluator exists in LangSmith using API.

        Args:
            evaluator_name: Expected evaluator name

        Returns:
            self for chaining
        """
        try:
            import requests
            import os

            api_key = os.getenv("LANGSMITH_API_KEY")
            if not api_key:
                self.failed.append("✗ LANGSMITH_API_KEY not set")
                return self

            api_url = os.getenv("LANGSMITH_API_URL", "https://api.smith.langchain.com")
            headers = {
                "x-api-key": api_key,
                "Content-Type": "application/json"
            }

            # Query /runs/rules endpoint to get evaluators
            url = f"{api_url}/runs/rules"
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            rules = response.json()
            evaluator = next((r for r in rules if r.get("display_name") == evaluator_name), None)

            if evaluator:
                # Check if it has dataset targets
                dataset_ids = evaluator.get("target_dataset_ids", [])
                if dataset_ids:
                    self.passed.append(f"✓ Evaluator exists in LangSmith: {evaluator_name} (attached to {len(dataset_ids)} dataset(s))")
                else:
                    self.failed.append(f"✗ Evaluator '{evaluator_name}' exists but not attached to any dataset")
            else:
                self.failed.append(f"✗ Evaluator not found in LangSmith: {evaluator_name}")

        except Exception as e:
            self.failed.append(f"✗ Error checking evaluator in LangSmith: {e}")

        return self
