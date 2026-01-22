# LangGraph + LangSmith Skills for DeepAgents CLI

Agent skills for building, observing, and evaluating LangGraph agents with LangSmith.

## Installation

```bash
./install.sh
```

Prompts for agent name (default: `langchain_agent`) and installation directory (default: `~/.deepagents`), then installs the agent with AGENTS.md and skills.

## Usage

```bash
deepagents --agent langchain_agent
export LANGSMITH_API_KEY=<your-key>
```

## Available Skills

- **langgraph-code** - Build agents with LangGraph (primitives, context management, multi-agent patterns)
- **langsmith-trace** - Query and inspect traces
- **langsmith-dataset** - Generate evaluation datasets from traces
- **langsmith-evaluator** - Create custom evaluation metrics

## Development

Agent configuration lives in `config/`. To update:

```bash
rm -rf ~/.deepagents/langchain_agent
./install.sh
```

---

# Testing Scaffold

Framework for validating DeepAgents CLI with skill-based agents.

## Quick Start

```bash
# Run all tests (automatically cleans local data between tests, LangSmith at end)
uv run python tests/run_test_suite.py

# Run individual tests (IMPORTANT: clean local data between each run)
uv run python scaffold/cleanup.py --local
uv run python tests/langgraph-code/test_create_agent.py
uv run python scaffold/cleanup.py --local
uv run python tests/langsmith-trace/test_trace_query.py

# After all tests complete, clean up LangSmith assets
uv run python scaffold/cleanup.py --langsmith
```

**Critical**: Always clean local files between individual test runs and LangSmith assets at the end to avoid test contamination.

Output saved to `logs/<agent>_<timestamp>/summary.txt`.

## Components

### Setup (`scaffold/setup.py`)
- `setup_test_environment()` - Set up test environment (always uses temp directories)
- `cleanup_test_environment()` - Clean up temp directories

### Runner (`scaffold/runner.py`)
- `run_autonomous_test()` - Run complete test with validation
- CLI: `uv run python scaffold/runner.py <agent_name> <prompt>`

### Cleanup (`scaffold/cleanup.py`)
```bash
uv run python scaffold/cleanup.py           # Both local and LangSmith
uv run python scaffold/cleanup.py --local   # Local files only
uv run python scaffold/cleanup.py --langsmith  # LangSmith assets only
```

### Validators (`scaffold/validators.py`)
Custom validators extending `TestValidator`:

```python
class MyValidator(TestValidator):
    def check_custom(self, summary: str) -> 'MyValidator':
        if "pattern" in summary:
            self.passed.append("✓ Check passed")
        else:
            self.failed.append("✗ Check failed")
        return self
```

## Test Suite

Tests run in dependency order:
1. **langgraph-code** - Creates SQL agent (generates traces)
2. **langsmith-trace** - Queries traces
3. **langsmith-dataset** - Generates datasets from traces
4. **langsmith-evaluator** - Creates evaluators attached to datasets

The test suite handles cleanup automatically between tests and at the end.

## Creating New Tests

Extend `TestValidator` for custom checks:

```python
from scaffold.setup import setup_test_environment, cleanup_test_environment
from scaffold.runner import run_autonomous_test, make_autonomous_prompt
from scaffold.validators import TestValidator

class MyValidator(TestValidator):
    def check_custom(self, summary: str) -> 'MyValidator':
        if "expected_pattern" in summary:
            self.passed.append("✓ Check passed")
        else:
            self.failed.append("✗ Check failed")
        return self

def validate(summary_content: str, test_dir: Path) -> tuple[list[str], list[str]]:
    validator = MyValidator()
    validator.check_skill("my-skill", summary_content)
    validator.check_custom(summary_content)
    return validator.results()

def run_test(work_dir: Path = None):
    test_dir = setup_test_environment(work_dir)
    result = run_autonomous_test(
        test_name="Test Name",
        prompt=make_autonomous_prompt("Create X. Do not ask questions."),
        test_dir=test_dir,
        runner_path=Path(__file__).parent.parent / "scaffold" / "runner.py",
        validate_func=validate
    )
    cleanup_test_environment(test_dir)
    return result
```

See `tests/langsmith-trace/test_trace_query.py` for a complete example.

