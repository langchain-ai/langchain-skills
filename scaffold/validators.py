"""
Common validation framework for autonomous tests.

Base validator class with reusable check methods that tests
can use to build custom validators.
"""

import re
import json
from pathlib import Path
from typing import List, Tuple, Callable, Optional


class TestValidator:
    """Base validator with common check methods.

    Usage:
        validator = TestValidator()
        validator.check_skill("langsmith-trace")
        validator.check_file_exists("output.txt")
        passed, failed = validator.results()
    """

    def __init__(self):
        """Initialize empty results."""
        self.passed: List[str] = []
        self.failed: List[str] = []

    def check_skill(self, skill_name: str, summary: str) -> 'TestValidator':
        """Check if a skill was consulted.

        Args:
            skill_name: Name of the skill to check for
            summary: Summary content to check

        Returns:
            self for chaining
        """
        if skill_name in summary:
            self.passed.append(f"✓ Consulted {skill_name} skill")
        else:
            self.failed.append(f"✗ Did not consult {skill_name} skill")
        return self

    def check_file_exists(self, filename: str, test_dir: Path, description: str = None) -> 'TestValidator':
        """Check if a file was created.

        Args:
            filename: Name of the file to check
            test_dir: Test directory to check in
            description: Optional description of what the file contains

        Returns:
            self for chaining
        """
        file_path = test_dir / filename
        if file_path.exists():
            desc = f" ({description})" if description else ""
            self.passed.append(f"✓ Created {filename}{desc}")
        else:
            self.failed.append(f"✗ {filename} not created")
        return self

    def check_file_content(
        self,
        filename: str,
        test_dir: Path,
        check_func: Callable[[str], Tuple[bool, str]]
    ) -> 'TestValidator':
        """Check file content with custom validation.

        Args:
            filename: Name of the file to check
            test_dir: Test directory to check in
            check_func: Function that takes content and returns (passed, message)

        Returns:
            self for chaining
        """
        file_path = test_dir / filename
        if not file_path.exists():
            self.failed.append(f"✗ {filename} not found")
            return self

        content = file_path.read_text().strip()
        check_passed, message = check_func(content)

        if check_passed:
            self.passed.append(f"✓ {message}")
        else:
            self.failed.append(f"✗ {message}")
        return self

    def check_uuid_format(self, filename: str, test_dir: Path) -> 'TestValidator':
        """Check if file contains a valid UUID.

        Args:
            filename: Name of the file containing UUID
            test_dir: Test directory to check in

        Returns:
            self for chaining
        """
        def validate_uuid(content: str) -> Tuple[bool, str]:
            uuid_pattern = re.compile(
                r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
                re.IGNORECASE
            )
            if uuid_pattern.match(content):
                return True, f"Valid UUID: {content[:8]}..."
            return False, f"Invalid UUID: {content}"

        return self.check_file_content(filename, test_dir, validate_uuid)

    def check_json_file(
        self,
        filename: str,
        test_dir: Path,
        validator: Optional[Callable[[dict], Tuple[bool, str]]] = None
    ) -> 'TestValidator':
        """Check if file contains valid JSON, optionally validate structure.

        Args:
            filename: Name of the JSON file
            test_dir: Test directory to check in
            validator: Optional function to validate JSON structure

        Returns:
            self for chaining
        """
        file_path = test_dir / filename
        if not file_path.exists():
            self.failed.append(f"✗ {filename} not found")
            return self

        try:
            with open(file_path) as f:
                data = json.load(f)
            self.passed.append(f"✓ {filename} is valid JSON")

            if validator:
                is_valid, message = validator(data)
                if is_valid:
                    self.passed.append(f"✓ {message}")
                else:
                    self.failed.append(f"✗ {message}")

        except json.JSONDecodeError as e:
            self.failed.append(f"✗ {filename} is invalid JSON: {e}")

        return self

    def check_patterns_present(
        self,
        patterns: List[str],
        summary: str,
        description: str = None
    ) -> 'TestValidator':
        """Check if patterns are present in summary.

        Args:
            patterns: List of patterns to check for
            summary: Summary content to check
            description: Optional description of what patterns represent

        Returns:
            self for chaining
        """
        found = [p for p in patterns if p in summary]

        if found:
            desc = f" ({description})" if description else ""
            self.passed.append(f"✓ Found patterns{desc}: {', '.join(found)}")

        missing = [p for p in patterns if p not in summary]
        if missing:
            desc = f" ({description})" if description else ""
            self.failed.append(f"✗ Missing patterns{desc}: {', '.join(missing)}")

        return self

    def check_patterns_absent(
        self,
        patterns: List[str],
        summary: str,
        description: str = None
    ) -> 'TestValidator':
        """Check if patterns are NOT present in summary.

        Args:
            patterns: List of patterns that should not be present
            summary: Summary content to check
            description: Optional description of what patterns represent

        Returns:
            self for chaining
        """
        found = [p for p in patterns if p in summary]

        if not found:
            desc = f" ({description})" if description else ""
            self.passed.append(f"✓ Avoided patterns{desc}")
        else:
            desc = f" ({description})" if description else ""
            self.failed.append(f"✗ Found forbidden patterns{desc}: {', '.join(found)}")

        return self

    def results(self) -> Tuple[List[str], List[str]]:
        """Get validation results.

        Returns:
            Tuple of (passed_validations, failed_validations)
        """
        return self.passed, self.failed
