"""
LangSmith dataset test validators.
"""

import sys
import json
from pathlib import Path
from langsmith import Client

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.validators import TestValidator


class DatasetGenerationValidator(TestValidator):
    """Validator for dataset generation tests."""

    def check_dataset_json(self, test_dir: Path) -> 'DatasetGenerationValidator':
        """Check that dataset JSON was created with valid structure.

        Args:
            test_dir: Test directory to check in

        Returns:
            self for chaining
        """
        def validate_structure(data):
            if not isinstance(data, list):
                return False, f"Dataset should be a list, got {type(data)}"

            if len(data) == 0:
                return False, "Dataset is empty"

            # Check first example structure
            example = data[0]
            if not isinstance(example, dict):
                return False, f"Example should be dict, got {type(example)}"

            if "inputs" not in example or "outputs" not in example:
                return False, f"Example missing required fields, found: {list(example.keys())}"

            if "expected_response" not in example.get("outputs", {}):
                return False, "Example outputs missing 'expected_response' field"

            return True, f"Dataset has valid structure with {len(data)} examples"

        return self.check_json_file("test_dataset.json", test_dir, validate_structure)

    def check_info_file(self, test_dir: Path) -> 'DatasetGenerationValidator':
        """Check that info file was created with content.

        Args:
            test_dir: Test directory to check in

        Returns:
            self for chaining
        """
        def check_content(content: str):
            if len(content) < 3:
                return False, "Info file is empty or too short"
            return True, f"Info file contains: {content}"

        return self.check_file_content("test_dataset_info.txt", test_dir, check_content)


class DatasetUploadValidator(TestValidator):
    """Validator for dataset upload tests."""

    def __init__(self):
        """Initialize validator with LangSmith client."""
        super().__init__()
        try:
            self.client = Client()
        except Exception:
            self.client = None

    def check_dataset_uploaded(self, test_dir: Path, expected_name: str) -> 'DatasetUploadValidator':
        """Check that dataset was uploaded with correct name.

        Args:
            test_dir: Test directory to check in
            expected_name: Expected dataset name

        Returns:
            self for chaining
        """
        def check_name(content: str):
            if content == expected_name:
                return True, f"Dataset uploaded: {content}"
            return False, f"Dataset name incorrect: {content} (expected {expected_name})"

        return self.check_file_content("test_dataset_upload_name.txt", test_dir, check_name)

    def check_dataset_in_langsmith(self, dataset_name: str) -> 'DatasetUploadValidator':
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
                dataset = datasets[0]
                example_count = len(list(self.client.list_examples(dataset_id=dataset.id)))
                self.passed.append(f"✓ Dataset exists in LangSmith: {dataset_name} ({example_count} examples)")
            else:
                self.failed.append(f"✗ Dataset not found in LangSmith: {dataset_name}")
        except Exception as e:
            self.failed.append(f"✗ Error checking LangSmith for dataset: {e}")

        return self
