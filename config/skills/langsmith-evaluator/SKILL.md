---
name: LangSmith Evaluators
description: "INVOKE THIS SKILL when building evaluation pipelines for LangSmith. Covers three core components: (1) Creating Evaluators - LLM-as-Judge, custom code; (2) Defining Run Functions - how to capture outputs and trajectories from your agent; (3) Running Evaluations - locally with evaluate() or auto-run via LangSmith. Contains helper scripts."
---

<oneliner>
Three core components: **(1) Creating Evaluators** - LLM-as-Judge, custom code; **(2) Defining Run Functions** - capture agent outputs/trajectories for evaluation; **(3) Running Evaluations** - locally with `evaluate()` or auto-run via uploaded evaluators. Python and TypeScript examples included.
</oneliner>

<setup>
Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here          # Required
LANGSMITH_WORKSPACE_ID=your-workspace-id              # Optional: for org-scoped keys
OPENAI_API_KEY=your_openai_key                        # For LLM as Judge
```

Python Dependencies
```bash
pip install langsmith langchain-openai python-dotenv
```

JavaScript Dependencies
```bash
npm install langsmith commander chalk cli-table3 dotenv openai
```
</setup>

<evaluator_format>
## Offline vs Online Evaluators

**Offline Evaluators** (attached to datasets):
- Function signature: `(run, example)` - receives both run outputs and dataset example
- Use case: Comparing agent outputs to expected values in a dataset
- Upload with: `--dataset "Dataset Name"`

**Online Evaluators** (attached to projects):
- Function signature: `(run)` - receives only run outputs, NO example parameter
- Use case: Real-time quality checks on production runs (no reference data)
- Upload with: `--project "Project Name"`

**CRITICAL - Return Format:**
- Return `{"score": value, "comment": "..."}` - the metric key is auto-derived from the function name
- Each evaluator returns **ONE metric only**. For multiple metrics, create multiple evaluator functions.
- Do NOT return `{"metric_name": value}` or lists of metrics - this will error.

**CRITICAL - Local vs Uploaded (Python only):**
- Local `evaluate()`: `run` is a `RunTree` object → use `run.outputs`
- Uploaded to LangSmith: `run` is a dict → use `run["outputs"]`
- Handle both: `run.outputs if hasattr(run, "outputs") else run.get("outputs", {})`
- TypeScript always uses attribute access: `run.outputs?.field`
</evaluator_format>

<evaluator_types>
- **LLM as Judge** - Uses an LLM to grade outputs. Best for subjective quality (accuracy, helpfulness, relevance).
- **Custom Code** - Deterministic logic. Best for objective checks (exact match, trajectory validation, format compliance).
</evaluator_types>

<llm_judge>
## LLM as Judge Evaluators

**NOTE:** LLM-as-Judge upload is currently not supported by our script only supports code evaluators. For evaluations against a dataset, STRONGLY PREFER defining local evaluators to use with `evaluate(evaluators=[...])`.

<python>
```python
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI

class Grade(TypedDict):
    reasoning: Annotated[str, ..., "Explain your reasoning"]
    is_accurate: Annotated[bool, ..., "True if response is accurate"]

judge = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(Grade, method="json_schema", strict=True)

async def accuracy_evaluator(run, example):
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    example_outputs = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}
    grade = await judge.ainvoke([{"role": "user", "content": f"Expected: {example_outputs}\nActual: {run_outputs}\nIs this accurate?"}])
    return {"score": 1 if grade["is_accurate"] else 0, "comment": grade["reasoning"]}
```
</python>
</llm_judge>

<code_evaluators>
## Custom Code Evaluators

**Inspect your dataset first** to understand field names. Your run function output must match the dataset schema.

<python>
```python
def trajectory_evaluator(run, example):
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    example_outputs = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}
    actual = run_outputs.get("trajectory", [])
    expected = example_outputs.get("expected_trajectory", [])
    return {"score": 1 if actual == expected else 0, "comment": f"Expected {expected}, got {actual}"}
```
</python>
</code_evaluators>

<run_functions>
## Defining Run Functions

Run functions execute your agent and return outputs matching your dataset schema. Field names must match exactly.

```python
def run_agent(inputs: dict) -> dict:
    result = your_agent.invoke(inputs)
    return {"output": result}  # Field name must match dataset
```

### Capturing Trajectories

For trajectory evaluation, your run function must capture tool calls during execution.

**LangGraph agents:** Use `stream_mode="debug"` with `subgraphs=True` to capture nested subagent tool calls.

```python
import uuid

def run_agent_with_trajectory(agent, inputs: dict) -> dict:
    config = {"configurable": {"thread_id": f"eval-{uuid.uuid4()}"}}
    trajectory = []

    for chunk in agent.stream(inputs, config=config, stream_mode="debug", subgraphs=True):
        # Chunk structure varies by agent - inspect to find tool_call names
        # Example: chunk may contain {"payload": {"name": "tool_name", ...}}
        pass

    return {"output": final_result, "trajectory": trajectory}
```

**Custom / Non-LangChain Agents:**

1. **Inspect output first** - Run your agent and inspect the result structure. Trajectory data may already be included in the output (e.g., `result.tool_calls`, `result.steps`, etc.)
2. **Callbacks/Hooks** - If your framework supports execution callbacks, register a hook that records tool names on each invocation
3. **Parse execution logs** - As a last resort, extract tool names from structured logs or trace data

The key is to capture the tool name at execution time, not at definition time.
</run_functions>

<upload>
## Uploading Evaluators to LangSmith

**IMPORTANT - Auto-Run Behavior:**
Evaluators uploaded to a dataset **automatically run** when you run experiments on that dataset. You do NOT need to pass them to `evaluate()` - just run your agent against the dataset and the uploaded evaluators execute automatically.

**IMPORTANT - Local vs Uploaded:**
Uploaded evaluators have very limited package access for security reasons! DO NOT upload evaluators that unless they only need to rely on standard Python / Javascript functionality, such as built-in packages. For dataset (offline) evaluators, prefer running locally with `evaluate(evaluators=[...])` first. This gives you full package access.

**IMPORTANT - Code vs Structured Evaluators:**
- **Code evaluators** (what our script uploads): Run in a limited environment without external packages. Use for deterministic logic (exact match, trajectory validation).
- **Structured evaluators** (LLM-as-Judge): Configured via LangSmith UI, use a specific payload format with model/prompt/schema. Our script does not support this format yet.

**IMPORTANT - Choose the right target:**
- `--dataset`: Offline evaluator with `(run, example)` signature - for comparing to expected values
- `--project`: Online evaluator with `(run)` signature - for real-time quality checks

You must specify one. Global evaluators are not supported.

```bash
# Python: python upload_evaluators.py ...
# TypeScript: npx tsx upload_evaluators.ts ...

# List all evaluators
upload_evaluators.py list

# Upload offline evaluator (attached to dataset)
upload_evaluators.py upload my_evaluators.py \
  --name "Trajectory Match" --function trajectory_evaluator \
  --dataset "My Dataset" --replace

# Upload online evaluator (attached to project)
upload_evaluators.py upload my_evaluators.py \
  --name "Quality Check" --function quality_check \
  --project "Production Agent" --replace

# Delete
upload_evaluators.py delete "Trajectory Match"
```

**IMPORTANT - Safety Prompts:**
- The script prompts for confirmation before destructive operations
- **NEVER use `--yes` flag unless the user explicitly requests it**
</upload>

<best_practices>
1. **Use structured output for LLM judges** - More reliable than parsing free-text
2. **Match evaluator to dataset type**
   - Final Response → LLM as Judge for quality
   - Trajectory → Custom Code for sequence
3. **Use async for LLM judges** - Enables parallel evaluation
4. **Test evaluators independently** - Validate on known good/bad examples first
5. **Choose the right language**
   - Python: Use for Python agents, langchain integrations
   - JavaScript: Use for TypeScript/Node.js agents
</best_practices>

<running_evaluations>
## Running Evaluations

**Uploaded evaluators** auto-run when you run experiments - no code needed. **Local evaluators** are passed directly for development/testing.

```python
from langsmith import evaluate

# Uploaded evaluators run automatically
results = evaluate(run_agent, data="My Dataset", experiment_prefix="eval-v1")

# Or pass local evaluators for testing
results = evaluate(run_agent, data="My Dataset", evaluators=[my_evaluator], experiment_prefix="eval-v1")
```
</running_evaluations>

<troubleshooting>
## Common Issues

**One metric per evaluator:** Return `{"score": value, "comment": "..."}`. For multiple metrics, create separate functions.

**Field name mismatch:** Your run function output must match dataset schema exactly. Inspect dataset first with `client.read_example(example_id)`.

**RunTree vs dict (Python):** Local `evaluate()` passes `RunTree`, uploaded evaluators receive `dict`. Handle both:
```python
run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
```
</troubleshooting>

<resources>
- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Custom Code Evaluators](https://changelog.langchain.com/announcements/custom-code-evaluators-in-langsmith)
- [OpenEvals - Readymade Evaluators](https://github.com/langchain-ai/openevals)
</resources>
