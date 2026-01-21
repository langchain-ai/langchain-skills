"""
Testing scaffold for CLI agents.

Main components:
- fixtures: Test environment setup and cleanup helpers
- validators: Reusable validation framework with TestValidator base class
- runner: CLI runner that executes deepagents and captures agent-written summaries

Quick start:
    from scaffold.fixtures import setup_test_environment, run_autonomous_test
    from scaffold.validators import TestValidator

    # Create custom validator by extending TestValidator
    class MyValidator(TestValidator):
        def check_custom_logic(self, summary: str):
            if "expected" in summary:
                self.passed.append("✓ Custom check passed")
            else:
                self.failed.append("✗ Custom check failed")
            return self

    def validate(summary: str, test_dir: Path):
        validator = MyValidator()
        validator.check_skill("my-skill", summary)
        validator.check_custom_logic(summary)
        return validator.results()

    test_dir = setup_test_environment()
    result = run_autonomous_test(
        test_name="My Test",
        prompt="...",
        test_dir=test_dir,
        runner_path=runner,
        validate_func=validate
    )
"""

from .validators import TestValidator

__all__ = [
    'TestValidator',
]
