# LangGraph + LangSmith Skills for DeepAgents CLI

Agent skills for building, observing, and evaluating LangGraph agents with LangSmith.

## Installation

Install as a custom agent in [DeepAgents CLI](https://github.com/langchain-ai/deepagents/tree/master/libs/deepagents-cli):

```bash
./install.sh
```

The script will:
1. Prompt for agent name (defaults to `langchain_agent`)
2. Prompt for installation directory (defaults to `~/.deepagents`)
3. Ask for confirmation
4. Create agent directory with AGENTS.md and skills/
5. Error if the agent already exists

## Usage

Once installed, use the agent with:

```bash
deepagents --agent langchain_agent  # or your custom name
```

Set your LangSmith API key:

```bash
export LANGSMITH_API_KEY=<your-key>
```

## Available Skills

- **langgraph-code** - Building agents with LangGraph (primitives, context management, multi-agent patterns)
- **langsmith-trace** - Query and inspect agent execution traces
- **langsmith-dataset** - Generate evaluation datasets from traces
- **langsmith-evaluator** - Create custom evaluation metrics

## Development

The agent configuration lives in `config/`:

```
config/
├── AGENT.md           # Agent personality/instructions (copied as AGENTS.md)
└── skills/            # Skill modules
    ├── langgraph-code/
    ├── langsmith-trace/
    ├── langsmith-dataset/
    └── langsmith-evaluator/
```

To update an existing installation:

```bash
# Remove old installation (replace with your agent name)
rm -rf ~/.deepagents/langchain_agent

# Reinstall
./install.sh
```

---

# Testing Scaffold

Testing framework for validating DeepAgents CLI behavior with skill-based agents.

## Overview

The scaffold provides tools to:
- Run DeepAgents CLI tests programmatically
- Parse TUI/ANSI output into readable text
- Validate agent behavior (skill consultation, pattern usage, file creation)
- Generate human-readable summaries and reports

## Quick Start

### Installation

1. Ensure DeepAgents CLI is installed:
```bash
cd /path/to/test/project
uv venv
source .venv/bin/activate
uv pip install deepagents-cli pexpect
```

2. Install your agent with skills:
```bash
rm -rf ~/.deepagents/your_agent
mkdir -p ~/.deepagents/your_agent
cp config/AGENTS.md ~/.deepagents/your_agent/
cp -r config/skills ~/.deepagents/your_agent/
```

### Running Tests

Basic test execution:

```bash
cd /path/to/skills
python scaffold/runner.py langchain_agent "Create a SQL agent"
```

This will:
1. Run the agent with the specified prompt
2. Capture all output
3. Run validations
4. Save readable summary, formatted output, and raw output

### Output Files

After running a test, you'll find in `logs/<agent>_<timestamp>/`:
- `summary.txt` - Complete session summary with stats, code blocks, and key responses

**Note**: The current runner is designed for automated testing with a single prompt. It uses `--auto-approve` and `-m` flag for non-interactive execution. For interactive/passthrough sessions where you can answer follow-up questions, you would need a different tool that monitors output in real-time.

## Framework Components

### 1. Parser (`scaffold/parser.py`)

Parses terminal UI output and extracts structured content.

**Basic usage**:

```python
from scaffold import parse_tui_output

# Parse raw TUI output
extractor = parse_tui_output(raw_output)

# Get structured data
skills = extractor.get_skill_consultations()  # ['langgraph-code', 'langsmith-tracing']
imports = extractor.get_imports()  # ['langchain_anthropic', 'langchain_core.tools']
files = extractor.get_file_operations()  # [('write', 'agent.py'), ('read', 'SKILL.md')]

# Generate outputs
summary = extractor.create_summary()  # Concise summary with stats
readable = extractor.format_readable()  # Clean conversation text
```

**Search and validation**:

```python
# Check if text is present
if extractor.contains("create_agent"):
    print("Modern pattern found")

# Search with regex
matches = extractor.search_pattern(r"from langchain_\w+ import \w+")
```

### 2. Validator (`scaffold/validator.py`)

Framework for testing CLI agent behavior with reusable validation checks.

**Built-in validations**:

```python
from scaffold import (
    SkillConsultationCheck,
    PatternAvoidanceCheck,
    PatternUsageCheck,
    FileCreationCheck
)

validations = [
    # Check agent consulted the right skill
    SkillConsultationCheck("langgraph-code"),

    # Check agent avoided legacy patterns
    PatternAvoidanceCheck(
        patterns=["langchain.llms", "LLMChain", "PromptTemplate"],
        description="Avoided legacy LangChain patterns"
    ),

    # Check agent used modern patterns
    PatternUsageCheck(
        patterns=["create_agent", "ChatAnthropic", "@tool"],
        description="Used modern LangChain patterns"
    ),

    # Check agent created expected files
    FileCreationCheck(["agent.py", "tools.py"])
]
```

**Creating custom validations**:

```python
from scaffold import Validation, ValidationResult

class CustomCheck(Validation):
    def __init__(self):
        super().__init__("My custom check")

    def check(self, output, interaction_log, extractor=None):
        # Use extractor for parsed content
        if extractor:
            text = extractor.clean
        else:
            text = output

        # Your validation logic
        passed = "expected_pattern" in text.lower()
        details = "Found pattern" if passed else "Pattern not found"

        return ValidationResult(
            name=self.name,
            passed=passed,
            details=details,
            evidence=[]
        )
```

### 3. Runner (`scaffold/runner.py`)

Command-line test runner with built-in validations.

**Usage**:

```bash
python scaffold/runner.py <agent_name> <prompt> [options]

Options:
  --output-dir DIR     Output directory (default: test_output)
  --working-dir DIR    Working directory (default: current)
```

**Example**:

```bash
python scaffold/runner.py langchain_agent \
    "Create a SQL agent for the Chinook database" \
    --output-dir results/sql_agent \
    --working-dir /path/to/test/project
```

**Customizing validations**:

Edit `scaffold/runner.py` to modify the validations list:

```python
validations = [
    SkillConsultationCheck("langgraph-code"),
    PatternAvoidanceCheck(
        patterns=["your_legacy_patterns"],
        description="Avoided legacy patterns"
    ),
    PatternUsageCheck(
        patterns=["your_modern_patterns"],
        description="Used modern patterns"
    ),
]
```

## Advanced Usage

### Using CLITester Directly

For more control, use the `CLITester` class:

```python
from pathlib import Path
from scaffold import CLITester, SkillConsultationCheck

tester = CLITester(
    command=["deepagents", "--agent", "langchain_agent", "--auto-approve"],
    working_dir="/path/to/test/project",
    timeout=300
)

result = tester.run_test(
    test_name="SQL Agent Test",
    prompt="Create a SQL agent",
    validations=[
        SkillConsultationCheck("langgraph-code")
    ],
    capture_duration=30.0
)

print(f"Test passed: {result.passed}")
print(f"Duration: {result.duration_seconds}s")

for validation in result.validations:
    print(f"{validation.name}: {'PASS' if validation.passed else 'FAIL'}")
    print(f"  {validation.details}")
```

### Interactive Multi-Step Tests

For tests requiring multiple interactions:

```python
steps = [
    {"input": "Create a SQL agent", "wait": 20.0},
    {"input": "Add error handling", "wait": 15.0},
    {"input": "Write tests", "wait": 10.0}
]

result = tester.run_interactive_test(
    test_name="Multi-step test",
    steps=steps,
    validations=[...]
)
```

## File Structure

```
skills/
├── README.md                 # This file
├── scaffold/                 # Testing framework
│   ├── __init__.py          # Package exports
│   ├── parser.py            # TUI/ANSI parser and formatter
│   ├── validator.py         # Validation framework
│   └── runner.py            # CLI test runner
├── config/                   # Agent configuration
│   ├── AGENTS.md            # Main agent instructions
│   └── skills/              # Skill definitions
│       └── langgraph-code/
│           └── SKILL.md
└── tests/                    # Test outputs
    └── output/
        ├── summary.txt
        ├── readable.txt
        └── raw_output.txt
```

## Validation Best Practices

1. **Skill Consultation**: Always verify the agent reads the correct skill
2. **Pattern Enforcement**: Check both avoidance (legacy) and usage (modern)
3. **File Creation**: Verify expected files are created
4. **Evidence Collection**: Use `evidence` field to show what was found

## Example Test Workflow

### Manual Testing

1. **Define your agent** in `config/AGENTS.md`
2. **Create skills** in `config/skills/your-skill/SKILL.md`
3. **Install the agent**:
   ```bash
   rm -rf ~/.deepagents/your_agent
   mkdir -p ~/.deepagents/your_agent
   cp config/AGENTS.md ~/.deepagents/your_agent/
   cp -r config/skills ~/.deepagents/your_agent/
   ```
4. **Run test with complete prompt**:
   ```bash
   python scaffold/runner.py your_agent "Specific prompt. Do not ask questions."
   ```
5. **Review output**:
   - Check `logs/<agent>_<timestamp>/summary.txt`

### Autonomous Testing

The test suite provides autonomous tests for all skills. Tests run in dependency order with a shared environment.

**Run the complete test suite:**

```bash
# Use default directory (~/Desktop/Projects/test)
python tests/run_test_suite.py

# Specify custom directory with deepagents installed
python tests/run_test_suite.py --work-dir /path/to/test/env

# Use temporary isolated directory (auto-cleanup)
python tests/run_test_suite.py --use-temp
```

**Run individual tests:**

```bash
# LangGraph code test
python tests/langgraph-code/test_sql_agent_autonomous.py

# LangSmith trace query test
python tests/langsmith-trace/test_trace_query.py

# LangSmith dataset tests
python tests/langsmith-dataset/test_dataset_generation.py
python tests/langsmith-dataset/test_dataset_upload.py

# LangSmith evaluator test
python tests/langsmith-evaluator/test_evaluator_upload.py
```

**Test dependencies:**

Tests have dependencies and should run in order:
1. **langgraph-code** - Creates and runs SQL agent (generates traces to test project)
2. **langsmith-trace** - Queries traces from test project
3. **langsmith-dataset** - Generates datasets from test project traces
4. **langsmith-evaluator** - Creates evaluators attached to test datasets

The test suite (`run_test_suite.py`) handles these dependencies automatically:
- Sets `LANGSMITH_PROJECT="Skills Test - DELETE ME"` for all tests
- Uses coordinated dataset/evaluator names for easy cleanup
- Fails fast if any test fails
- Copies chinook.db to test environment for SQL agent

**Cleanup:**

After running the test suite, clean up LangSmith artifacts:
```bash
# Delete in LangSmith UI or via API:
# - Project: "Skills Test - DELETE ME"
# - Datasets: "Test Dataset - DELETE ME", "Evaluator Test Dataset - DELETE ME"
# - Evaluator: "Test Length Check - DELETE ME"
```

**Creating new tests:**

Use the autonomous test pattern with fixtures and validators:

```python
from scaffold.fixtures import (
    setup_test_environment,
    cleanup_test_environment,
    run_autonomous_test
)
from scaffold.validators import TestValidator

def get_prompt() -> str:
    """Complete prompt that avoids follow-up questions."""
    return """Create X that does Y.

Requirements:
- Requirement 1
- Requirement 2

Do not ask clarifying questions."""

# Create custom validator by extending TestValidator
class MyTestValidator(TestValidator):
    """Custom validator with test-specific checks."""

    def check_custom_logic(self, summary: str) -> 'MyTestValidator':
        """Your custom validation logic."""
        if "expected_pattern" in summary:
            self.passed.append("✓ Check passed")
        else:
            self.failed.append("✗ Check failed")
        return self

def validate(summary_content: str, test_dir: Path) -> tuple[list[str], list[str]]:
    """Validate test results using custom validator."""
    validator = MyTestValidator()
    validator.check_skill("my-skill", summary_content)
    validator.check_custom_logic(summary_content)
    return validator.results()

def run_test(work_dir: Path = None, use_temp: bool = False):
    test_dir = setup_test_environment(work_dir, use_temp=use_temp)
    runner = Path(__file__).parent.parent / "scaffold" / "runner.py"

    result = run_autonomous_test(
        test_name="Your Test Name",
        prompt=get_prompt(),
        test_dir=test_dir,
        runner_path=runner,
        validate_func=validate,
        timeout=180
    )

    if use_temp:
        cleanup_test_environment(test_dir)

    return result
```

See `tests/langsmith-trace/test_trace_query.py` for a complete example.

