"""
LangSmith trace test validators.
"""

import sys
from pathlib import Path
from langsmith import Client

# Skills root
skills_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(skills_root))

from scaffold.validators import TestValidator


class TraceValidator(TestValidator):
    """Validator for trace query tests."""

    def __init__(self):
        """Initialize validator with LangSmith client."""
        super().__init__()
        try:
            self.client = Client()
        except Exception:
            self.client = None

    def check_trace_in_langsmith(self, test_dir: Path, project: str = None) -> 'TraceValidator':
        """Check that trace ID exists in LangSmith.

        Args:
            test_dir: Test directory containing trace ID file
            project: Optional project name to check

        Returns:
            self for chaining
        """
        if not self.client:
            self.failed.append("✗ LangSmith client not available")
            return self

        trace_id_file = test_dir / "test_trace_id.txt"
        if not trace_id_file.exists():
            self.failed.append("✗ test_trace_id.txt not found")
            return self

        trace_id = trace_id_file.read_text().strip()

        try:
            params = {"trace_id": trace_id}
            if project:
                params["project_name"] = project

            runs = list(self.client.list_runs(**params))
            if runs:
                self.passed.append(f"✓ Trace exists in LangSmith: {trace_id[:16]}... ({len(runs)} runs)")
            else:
                self.failed.append(f"✗ Trace not found in LangSmith: {trace_id}")
        except Exception as e:
            self.failed.append(f"✗ Error checking LangSmith for trace: {e}")

        return self
