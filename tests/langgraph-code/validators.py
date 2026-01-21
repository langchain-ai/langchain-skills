"""
LangGraph code test validators.
"""

import sys
from pathlib import Path

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.validators import TestValidator


class LangGraphCodeValidator(TestValidator):
    """Validator for LangGraph code generation tests."""

    def check_modern_patterns(self, summary: str) -> 'LangGraphCodeValidator':
        """Check for modern LangChain patterns.

        Args:
            summary: Summary content to check

        Returns:
            self for chaining
        """
        modern_patterns = {
            "@tool": "decorator",
            "create_agent": "function",
            "ChatAnthropic": "model",
        }

        found = [name for pattern, name in modern_patterns.items() if pattern in summary]

        if found:
            self.passed.append(f"✓ Used modern patterns: {', '.join(found)}")
        else:
            self.failed.append("✗ No modern patterns detected")

        return self

    def check_legacy_patterns_avoided(self, summary: str) -> 'LangGraphCodeValidator':
        """Check that legacy patterns were avoided.

        Args:
            summary: Summary content to check

        Returns:
            self for chaining
        """
        legacy_patterns = {
            "LLMChain": "legacy chain",
            "create_sql_agent": "legacy SQL agent",
            "PromptTemplate": "legacy prompt",
        }

        found = [name for pattern, name in legacy_patterns.items() if pattern in summary]

        if found:
            self.failed.append(f"✗ Used legacy patterns: {', '.join(found)}")
        else:
            self.passed.append("✓ Avoided legacy patterns")

        return self

    def check_agent_file(self, test_dir: Path) -> 'LangGraphCodeValidator':
        """Check that agent file was created.

        Args:
            test_dir: Test directory to check in

        Returns:
            self for chaining
        """
        return self.check_file_exists("sql_agent.py", test_dir, "SQL agent code")
