"""
LangSmith evaluator test validators.
"""

import sys
import ast
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.validators import TestValidator


class EvaluatorValidator(TestValidator):
    """Validator for evaluator upload tests."""

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

    def check_dataset_created(self, test_dir: Path, expected_name: str) -> 'EvaluatorValidator':
        """Check that dataset was created for evaluator.

        Args:
            test_dir: Test directory to check in
            expected_name: Expected dataset name

        Returns:
            self for chaining
        """
        def check_name(content: str):
            if content == expected_name:
                return True, f"Dataset created: {content}"
            return False, f"Dataset name incorrect: {content} (expected {expected_name})"

        return self.check_file_content("test_evaluator_dataset_name.txt", test_dir, check_name)

    def check_evaluator_uploaded(self, test_dir: Path, expected_name: str) -> 'EvaluatorValidator':
        """Check that evaluator was uploaded with correct name.

        Args:
            test_dir: Test directory to check in
            expected_name: Expected evaluator name

        Returns:
            self for chaining
        """
        def check_name(content: str):
            if content == expected_name:
                return True, f"Evaluator uploaded: {content}"
            return False, f"Evaluator name incorrect: {content} (expected {expected_name})"

        return self.check_file_content("test_evaluator_name.txt", test_dir, check_name)
