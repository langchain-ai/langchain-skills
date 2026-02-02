---
name: langsmith-evaluator
description: Use this skill for ANY question about CREATING evaluators. Covers creating custom metrics, LLM as Judge evaluators, code-based evaluators, and uploading evaluation logic to LangSmith. Does NOT cover RUNNING evaluations.
---

# LangSmith Evaluator

Create evaluators to measure agent performance on your datasets. LangSmith supports two types: **LLM as Judge** (uses LLM to grade outputs) and **Custom Code** (deterministic logic).

## Setup

### Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here          # Required
LANGSMITH_WORKSPACE_ID=your-workspace-id              # Optional: for org-scoped keys
OPENAI_API_KEY=your_openai_key                        # For LLM as Judge
```

### Dependencies

```bash
pip install langsmith langchain-openai python-dotenv
```

## Evaluator Format

Evaluators support two function signatures:

**Method 1: Dict Parameters (For running evaluations locally):**
```python
def evaluator_name(inputs: dict, outputs: dict, reference_outputs: dict = None) -> dict:
    """Evaluate a single prediction."""
    user_query = inputs.get("query", "")
    agent_response = outputs.get("expected_response", "")
    expected = reference_outputs.get("expected_response", "") if reference_outputs else None

    return {
        "key": "metric_name",    # Metric identifier
        "score": 0.85,           # Number or boolean
        "comment": "Reason..."   # Optional explanation
    }
```

**Method 2: Run/Example Parameters (For uploading to LangSmith):**
```python
def evaluator_name(run, example):
    """Evaluate using run/example dicts.

    Args:
        run: Dict with run["outputs"] containing agent outputs
        example: Dict with example["outputs"] containing expected outputs
    """
    agent_response = run["outputs"].get("expected_response", "")
    expected = example["outputs"].get("expected_response", "")

    return {
        "metric_name": 0.85,      # Metric name as key directly
        "comment": "Reason..."    # Optional explanation
    }
```

## LLM as Judge Evaluators

Use structured output for reliable grading:

```python
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI

class AccuracyGrade(TypedDict):
    """Structured evaluation output."""
    reasoning: Annotated[str, ..., "Explain your reasoning"]
    is_accurate: Annotated[bool, ..., "True if response is accurate"]
    confidence: Annotated[float, ..., "Confidence 0.0-1.0"]

# Configure model with structured output
judge = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
    AccuracyGrade, method="json_schema", strict=True
)

async def accuracy_evaluator(run, example):
    """Evaluate factual accuracy for LangSmith upload."""
    expected = example["outputs"].get('expected_response', '')
    agent_output = run["outputs"].get('expected_response', '')

    prompt = f"""Expected: {expected}
Agent Output: {agent_output}
Evaluate accuracy:"""

    grade = await judge.ainvoke([{"role": "user", "content": prompt}])

    return {
        "accuracy": 1 if grade["is_accurate"] else 0,
        "comment": f"{grade['reasoning']} (confidence: {grade['confidence']})"
    }
```

**Common Metrics:** Completeness, correctness, helpfulness, professionalism

## Custom Code Evaluators

### Exact Match
```python
def exact_match_evaluator(run, example):
    """Check if output exactly matches expected."""
    output = run["outputs"].get("expected_response", "").strip().lower()
    expected = example["outputs"].get("expected_response", "").strip().lower()

    match = output == expected
    return {
        "exact_match": 1 if match else 0,
        "comment": f"Match: {match}"
    }
```

### Trajectory Validation
```python
def trajectory_evaluator(run, example):
    """Evaluate tool call sequence."""
    trajectory = run["outputs"].get("expected_trajectory", [])
    expected = example["outputs"].get("expected_trajectory", [])

    # Exact sequence match
    exact = trajectory == expected

    # All required tools used (order-agnostic)
    all_tools = set(expected).issubset(set(trajectory))

    # Efficiency: count extra steps
    extra_steps = len(trajectory) - len(expected)

    return {
        "trajectory_match": 1 if exact else 0,
        "comment": f"Exact: {exact}, All tools: {all_tools}, Extra: {extra_steps}"
    }
```

### Single Step Validation
```python
def single_step_evaluator(run, example):
    """Evaluate single node output."""
    output = run["outputs"].get("output", {})
    expected = example["outputs"].get("expected_output", {})
    node_name = run["outputs"].get("node_name", "")

    # For classification nodes
    if "classification" in node_name:
        classification = output.get("classification", "")
        expected_class = expected.get("classification", "")
        match = classification.lower() == expected_class.lower()

        return {
            "classification_correct": 1 if match else 0,
            "comment": f"Output: {classification}, Expected: {expected_class}"
        }

    # For other nodes
    match = output == expected
    return {
        "output_match": 1 if match else 0,
        "comment": f"Match: {match}"
    }
```

## Running Evaluations

```python
from langsmith import Client

client = Client()

# Define your agent function
def run_agent(inputs: dict) -> dict:
    """Your agent invocation logic."""
    result = your_agent.invoke(inputs)
    return {"expected_response": result}

# Run evaluation
results = await client.aevaluate(
    run_agent,
    data="Skills: Final Response",              # Dataset name
    evaluators=[
        exact_match_evaluator,
        accuracy_evaluator,
        trajectory_evaluator
    ],
    experiment_prefix="skills-eval-v1",
    max_concurrency=4
)
```

## Upload Evaluators to LangSmith

The upload script is a utility tool to deploy your custom evaluators to LangSmith. Write evaluators specific to your use case, then upload them.

Navigate to `skills/langsmith-evaluator/scripts/` to upload evaluators.

**Important:** LangSmith API requires evaluators to use `(run, example)` signature where:
- `run`: dict with `run["outputs"]` containing agent outputs
- `example`: dict with `example["outputs"]` containing expected outputs

### Create Evaluator File

```python
# my_project/evaluators/custom_evals.py

def my_custom_evaluator(run, example):
    """Your custom evaluation logic.

    Args:
        run: Dict with run["outputs"] - agent outputs
        example: Dict with example["outputs"] - expected outputs

    Returns:
        Dict with metric_name as key, score as value, optional comment
    """
    # Extract relevant data
    agent_output = run["outputs"].get("expected_trajectory", [])
    expected = example["outputs"].get("expected_trajectory", [])

    # Your custom logic here
    match = agent_output == expected

    return {
        "my_metric": 1 if match else 0,
        "comment": "Custom reasoning here"
    }
```

### Upload

```bash
# List existing evaluators
python upload_evaluators.py list

# Upload evaluator
python upload_evaluators.py upload my_evaluators.py \
  --name "Trajectory Match" \
  --function trajectory_match \
  --dataset "Skills: Trajectory" \
  --replace

# Delete evaluator (will prompt for confirmation)
python upload_evaluators.py delete "Trajectory Match"

# Skip confirmation prompts (use with caution)
python upload_evaluators.py delete "Trajectory Match" --yes
python upload_evaluators.py upload my_evaluators.py \
  --name "Trajectory Match" \
  --function trajectory_match \
  --replace --yes
```

**Options:**
- `--name` - Display name in LangSmith
- `--function` - Function name to extract
- `--dataset` - Target dataset name
- `--project` - Target project name
- `--sample-rate` - Sampling rate (0.0-1.0)
- `--replace` - Replace if exists (will prompt for confirmation)
- `--yes` - Skip confirmation prompts for replace/delete operations

**IMPORTANT - Safety Prompts:**
- The script prompts for confirmation before any destructive operations (delete, replace)
- **ALWAYS respect these prompts** - wait for user input before proceeding
- **NEVER use `--yes` flag unless the user explicitly requests it**
- The `--yes` flag skips all safety prompts and should only be used in automated workflows when explicitly authorized by the user

## Best Practices

1. **Use structured output for LLM judges** - More reliable than parsing free-text
2. **Match evaluator to dataset type**
   - Final Response → LLM as Judge for quality, Custom Code for format
   - Single Step → Custom Code for exact match
   - Trajectory → Custom Code for sequence/efficiency
3. **Combine multiple evaluators** - Run both subjective (LLM) and objective (code)
4. **Use async for LLM judges** - Enables parallel evaluation, much faster
5. **Test evaluators independently** - Validate on known good/bad examples first
6. **Upload to LangSmith** - Automatic evaluation on new runs

## Example Workflow

```bash
# 1. Create evaluators file
cat > evaluators.py <<'EOF'
def exact_match(run, example):
    """Check if output exactly matches expected."""
    output = run["outputs"].get("expected_response", "").strip().lower()
    expected = example["outputs"].get("expected_response", "").strip().lower()
    match = output == expected
    return {
        "exact_match": 1 if match else 0,
        "comment": f"Match: {match}"
    }
EOF

# 2. Upload to LangSmith
python upload_evaluators.py upload evaluators.py \
  --name "Exact Match" \
  --function exact_match \
  --dataset "Skills: Final Response" \
  --replace

# 3. Evaluator runs automatically on new dataset runs
```

## Resources

- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Custom Code Evaluators](https://changelog.langchain.com/announcements/custom-code-evaluators-in-langsmith)
- [OpenEvals - Readymade Evaluators](https://github.com/langchain-ai/openevals)

## Related Skills

- Use **langsmith-trace** skill to query and export traces
- Use **langsmith-dataset** skill to generate evaluation datasets from traces
