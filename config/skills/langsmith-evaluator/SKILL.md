---
name: LangSmith Evaluators
description: "INVOKE THIS SKILL when creating evaluators for LangSmith OR running evaluations on datasets. Covers two main topics: (1) Creating Evaluators - LLM-as-Judge, custom code, trajectory evaluators; (2) Running Evaluations - uploading to LangSmith (auto-run) vs running locally. Contains helper scripts."
---

<oneliner>
Two main topics: **(1) Creating & Uploading Evaluators** - LLM-as-Judge, custom code, trajectory evaluators, plus how to upload to LangSmith; **(2) Running Evaluations** - uploaded evaluators auto-run on experiments, or run locally with `evaluate()`. Python and TypeScript examples included.
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
Evaluators use `(run, example)` signature for offline (dataset) evaluations.

**CRITICAL - Return Format:**
- Return `{"score": value, "comment": "..."}` - the metric key is auto-derived from the function name
- Each evaluator returns **ONE metric only**. For multiple metrics, create multiple evaluator functions.
- Do NOT return `{"metric_name": value}` or lists of metrics - this will error.

**CRITICAL - Local vs Uploaded:**
- When running locally with `evaluate()`, `run` is a `RunTree` object - use `run.outputs` (attribute)
- When uploaded to LangSmith, `run` is a dict - use `run["outputs"]` (subscript)
- Handle both by checking: `run.outputs if hasattr(run, "outputs") else run.get("outputs", {})`

<python>
Basic evaluator function signature returning score dict.
```python
def evaluator_name(run, example):
    """Evaluate using run/example - handles both RunTree and dict."""
    # Handle both RunTree (local) and dict (uploaded)
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    example_outputs = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}

    actual = run_outputs.get("output", "")
    expected = example_outputs.get("output", "")

    score = 1.0 if actual == expected else 0.0
    return {"score": score, "comment": "Matched" if score else "No match"}
```
</python>

<typescript>
Basic evaluator function signature returning score object.
```javascript
function evaluatorName(run, example) {
  // TypeScript always uses attribute access
  const actual = run.outputs?.output ?? "";  // Actual from run
  const expected = example.outputs?.output ?? "";  // Reference from dataset

  const score = actual === expected ? 1 : 0;
  return { score, comment: score ? "Matched" : "No match" };
}
```
</typescript>
</evaluator_format>

<evaluator_types>
- **LLM as Judge** - Uses an LLM to grade outputs. Best for subjective quality (accuracy, helpfulness, relevance).
- **Custom Code** - Deterministic logic. Best for objective checks (exact match, trajectory validation, format compliance).
- **Trajectory Evaluators** - Check tool call sequences.
</evaluator_types>

<runtree_vs_dict>
## RunTree vs Dict: Why Both Access Patterns?

When evaluators run, the `run` parameter type differs based on context:

| Context | `run` type | Access pattern |
|---------|-----------|----------------|
| Local `evaluate()` | `RunTree` object | `run.outputs` (attribute) |
| Uploaded to LangSmith | `dict` | `run["outputs"]` (subscript) |

**Why?**
- **Local:** The SDK wraps execution in a `RunTree` class for live tracing (timing, nesting, metadata). Your evaluator receives this object directly.
- **Uploaded:** Run data is fetched from the database as JSON, parsed into a Python dict.

**The fix:** Always handle both:
```python
run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
```

This pattern checks for attribute access first (RunTree), falls back to dict access.
</runtree_vs_dict>

<llm_judge>
## LLM as Judge Evaluators

<python>
Create an accuracy evaluator using structured output with LangChain.
```python
from typing import TypedDict, Annotated
from langchain_openai import ChatOpenAI

class AccuracyGrade(TypedDict):
    reasoning: Annotated[str, ..., "Explain your reasoning"]
    is_accurate: Annotated[bool, ..., "True if response is accurate"]
    confidence: Annotated[float, ..., "Confidence 0.0-1.0"]

judge = ChatOpenAI(model="gpt-4o-mini", temperature=0).with_structured_output(
    AccuracyGrade, method="json_schema", strict=True
)

async def accuracy_evaluator(run, example):
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
</python>

<typescript>
Create an accuracy evaluator using JSON mode with OpenAI SDK.
```javascript
import OpenAI from "openai";

const openai = new OpenAI();

async function accuracyEvaluator(run, example) {
  const expected = example.outputs?.expected_response ?? "";
  const agentOutput = run.outputs?.expected_response ?? "";

  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    temperature: 0,
    response_format: { type: "json_object" },
    messages: [
      {
        role: "system",
        content: `You are an evaluator. Respond with JSON: {"is_accurate": boolean, "reasoning": string, "confidence": number}`
      },
      {
        role: "user",
        content: `Expected: ${expected}\nAgent Output: ${agentOutput}\n\nIs the agent output accurate?`
      }
    ]
  });

  const grade = JSON.parse(response.choices[0].message.content);
  return {
    accuracy: grade.is_accurate ? 1 : 0,
    comment: `${grade.reasoning} (confidence: ${grade.confidence})`
  };
}
```
</typescript>
</llm_judge>

<code_evaluators>
## Custom Code Evaluators

### Exact Match

**Field name:** Both run outputs and dataset examples use `output`.

<python>
Compare outputs with case-insensitive exact match.
```python
def exact_match_evaluator(run, example):
    # Handle both RunTree (local) and dict (uploaded)
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    example_outputs = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}

    actual = run_outputs.get("output", "").strip().lower()  # from run
    expected = example_outputs.get("output", "").strip().lower()  # from dataset
    match = actual == expected
    return {"score": 1 if match else 0, "comment": f"Match: {match}"}
```
</python>

<typescript>
Compare outputs with case-insensitive exact match.
```javascript
function exactMatchEvaluator(run, example) {
  const actual = (run.outputs?.output ?? "").trim().toLowerCase();  // Actual from run
  const expected = (example.outputs?.output ?? "").trim().toLowerCase();  // Reference from dataset
  const match = actual === expected;
  return { score: match ? 1 : 0, comment: `Match: ${match}` };
}
```
</typescript>

### Trajectory Validation

**Field name:** Both run outputs and dataset examples use `trajectory`.

**CRITICAL:** Your run function output must match the dataset schema. See `<fix-run-output-dataset-mismatch>` for common errors.

<python>
Validate tool call sequence matches expected trajectory.
```python
def trajectory_evaluator(run, example):
    # Handle both RunTree (local) and dict (uploaded)
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    example_outputs = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}

    actual = run_outputs.get("trajectory", [])  # from run
    expected = example_outputs.get("trajectory", [])  # from dataset
    exact = actual == expected
    all_tools = set(expected).issubset(set(actual))
    return {"score": 1 if exact else 0, "comment": f"Exact: {exact}, All tools: {all_tools}"}
```
</python>

<typescript>
Validate tool call sequence matches expected trajectory.
```javascript
function trajectoryEvaluator(run, example) {
  const actual = run.outputs?.trajectory ?? [];  // Actual from run
  const expected = example.outputs?.trajectory ?? [];  // Reference from dataset
  const exact = JSON.stringify(actual) === JSON.stringify(expected);
  const allTools = expected.every(tool => actual.includes(tool));
  return { score: exact ? 1 : 0, comment: `Exact: ${exact}, All tools: ${allTools}` };
}
```
</typescript>

<python>
Capture full trajectory including subagent tool calls from LangSmith traces.
```python
def extract_full_trajectory(run_id: str) -> list[str]:
    """Extract all tool calls from a trace, including subagent calls."""
    from langsmith import Client
    client = Client()

    trajectory = []
    # Get all runs in the trace, not just top-level
    for run in client.list_runs(trace_id=run_id, run_type="tool"):
        trajectory.append(run.name)
    return trajectory
```
</python>
</code_evaluators>

<upload>
## Uploading Evaluators to LangSmith

**IMPORTANT - Auto-Run Behavior:**
Evaluators uploaded to a dataset **automatically run** when you run experiments on that dataset. You do NOT need to pass them to `evaluate()` - just run your agent against the dataset and the uploaded evaluators execute automatically.

<python>
Upload, list, and delete evaluators using the Python CLI script.
```bash
python upload_evaluators.py list
python upload_evaluators.py upload my_evaluators.py \
  --name "Exact Match" \
  --function exact_match \
  --dataset "Skills: Final Response" \
  --replace
python upload_evaluators.py delete "Exact Match"
```
</python>

<typescript>
Upload, list, and delete evaluators using the TypeScript CLI script.
```bash
npx tsx upload_evaluators.ts list
npx tsx upload_evaluators.ts upload my_evaluators.js \
  --name "Exact Match" \
  --function exactMatch \
  --dataset "Skills: Final Response" \
  --replace
npx tsx upload_evaluators.ts delete "Exact Match"
```
</typescript>

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

<example_workflow>
## Complete Evaluator Workflow

<python>
Create and upload an exact match evaluator.
```bash
cat > evaluators.py <<'EOF'
def exact_match(run, example):
    # Handle both RunTree (local) and dict (uploaded)
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    example_outputs = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}

    output = run_outputs.get("output", "").strip().lower()
    expected = example_outputs.get("output", "").strip().lower()
    match = output == expected
    return {"score": 1 if match else 0, "comment": f"Match: {match}"}
EOF

python upload_evaluators.py upload evaluators.py \
  --name "Exact Match" \
  --function exact_match \
  --dataset "Skills: Final Response" \
  --replace
```
</python>

<typescript>
Create and upload an exact match evaluator.
```bash
cat > evaluators.js <<'EOF'
function exactMatch(run, example) {
  const output = (run.outputs?.output ?? "").trim().toLowerCase();
  const expected = (example.outputs?.output ?? "").trim().toLowerCase();
  const match = output === expected;
  return { score: match ? 1 : 0, comment: `Match: ${match}` };
}
EOF

npx tsx upload_evaluators.ts upload evaluators.js \
  --name "Exact Match" \
  --function exactMatch \
  --dataset "Skills: Final Response" \
  --replace
```
</typescript>
</example_workflow>

<running_evaluations>
## Running Evaluations

Two ways to run evaluations:

| Method | When to use | Evaluator receives |
|--------|-------------|-------------------|
| **Upload to LangSmith** | Production, auto-run on experiments | `dict` |
| **Local `evaluate()`** | Development, testing | `RunTree` object |

### Option 1: Uploaded Evaluators (Recommended for Production)

Upload evaluators to a dataset - they **auto-run** on every experiment:

<python>
```bash
python upload_evaluators.py upload my_eval.py --name "My Eval" --dataset "My Dataset"
```
</python>

<typescript>
```bash
npx tsx upload_evaluators.ts upload my_eval.js --name "My Eval" --dataset "My Dataset"
```
</typescript>

Then just run your agent - no evaluators needed in code:

<python>
```python
from langsmith import evaluate

def run_agent(inputs: dict) -> dict:
    result = your_agent.invoke(inputs)
    return {"output": result}  # Use "output", not "output"

# Uploaded evaluators run automatically!
results = evaluate(
    run_agent,
    data="My Dataset",
    experiment_prefix="eval-v1",
)
```
</python>

<typescript>
```javascript
import { evaluate } from "langsmith/evaluation";

async function runAgent(inputs) {
  const result = await yourAgent.invoke(inputs);
  return { output: result };
}

// Uploaded evaluators run automatically!
const results = await evaluate(runAgent, {
  data: "My Dataset",
  experimentPrefix: "eval-v1",
});
```
</typescript>

### Option 2: Local Evaluators (Development/Testing)

Pass evaluators directly - useful for iterating on evaluator logic:

<python>
```python
from langsmith import evaluate

# When running locally, evaluator receives RunTree objects
results = evaluate(
    run_agent,
    data="My Dataset",
    evaluators=[my_evaluator],  # Local functions
    experiment_prefix="eval-v1",
)

for result in results:
    print(result)
```
</python>

<typescript>
```javascript
import { evaluate } from "langsmith/evaluation";

async function runAgent(inputs) {
  const result = await yourAgent.invoke(inputs);
  return { output: result };
}

const results = await evaluate(runAgent, {
  data: "My Dataset",
  evaluators: [myEvaluator],
  experimentPrefix: "eval-v1",
});
```
</typescript>
</running_evaluations>

<fix-one-metric-per-evaluator>
Each evaluator must return exactly one metric. For multiple metrics, create separate evaluator functions.
```python
# WRONG - Will error: "Expected dict with 'score', got extra fields"
return {
    "accuracy": 0.9,
    "completeness": 0.8,
    "comment": "..."
}

# WRONG - Will error: "Expected a list of dicts or EvaluationResults"
return [
    {"key": "accuracy", "score": 0.9},
    {"key": "completeness", "score": 0.8}
]

# CORRECT - One score per evaluator
return {"score": 0.9, "comment": "Accuracy check passed"}

# For multiple metrics, create separate functions:
def accuracy_evaluator(run, example): ...
def completeness_evaluator(run, example): ...
```
</fix-one-metric-per-evaluator>

<fix-runtree-vs-dict>
Handle both RunTree (local) and dict (uploaded) access patterns.
```python
# WRONG - Fails locally with: "'RunTree' object is not subscriptable"
output = run["outputs"].get("output", "")

# WRONG - Fails when uploaded: "'dict' object has no attribute 'outputs'"
output = run.outputs.get("output", "")

# CORRECT - Handle both
run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
output = run_outputs.get("output", "")
```
</fix-runtree-vs-dict>

<fix-run-output-dataset-mismatch>
Your run function output MUST match the schema expected by the dataset. Inspect your dataset examples first to understand what fields and structure are expected.

Common issues:
- **Wrong field names:** Dataset has `output`, you return `response`
- **Missing fields:** Dataset expects `trajectory`, you only return `output`
- **Different depth:** Dataset trajectory includes subagent calls, yours only has top-level

```python
# WRONG - Field name mismatch
# Dataset expects: {"output": "..."}
return {"response": result}  # Evaluator won't find the field!

# WRONG - Trajectory depth mismatch
# Dataset: {"trajectory": ["task", "tavily_search", "task"]}
return {"trajectory": ["task", "task"]}  # Missing subagent internals!

# CORRECT - Match dataset schema exactly
# 1. Check dataset structure first:
#    client.read_example(example_id)
# 2. Return matching fields:
return {"output": result, "trajectory": full_trajectory}

# For full trajectory including subagent calls:
from langsmith import Client
client = Client()
trajectory = [run.name for run in client.list_runs(trace_id=trace_id, run_type="tool")]
```
</fix-run-output-dataset-mismatch>

<resources>
- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Custom Code Evaluators](https://changelog.langchain.com/announcements/custom-code-evaluators-in-langsmith)
- [OpenEvals - Readymade Evaluators](https://github.com/langchain-ai/openevals)
</resources>
