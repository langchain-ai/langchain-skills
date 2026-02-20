---
name: langsmith-evaluator
description: "INVOKE THIS SKILL when creating evaluators for LangSmith OR running evaluations on datasets. Covers LLM-as-Judge evaluators, custom code evaluators, and uploading to LangSmith. Contains helper scripts to use or refer to."
---

<oneliner>
Create evaluators to measure agent performance on your datasets. LangSmith supports two types: **LLM as Judge** (uses LLM to grade outputs) and **Custom Code** (deterministic logic). Evaluators can be written in Python or JavaScript: the language chosen should match what's being evaluated.
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

### Python Format

```python
def evaluator_name(run, example):
    """Evaluate using run/example dicts."""
    agent_response = run["outputs"].get("expected_response", "")
    expected = example["outputs"].get("expected_response", "")

    return {
        "metric_name": 0.85,      # Metric name as key directly
        "comment": "Reason..."    # Optional explanation
    }
```

### JavaScript Format

```javascript
function evaluatorName(run, example) {
  const agentResponse = run.outputs?.expected_response ?? "";
  const expected = example.outputs?.expected_response ?? "";

  const score = agentResponse === expected ? 1 : 0;
  return { metric_name: score, comment: "Reason..." };
}
```
</evaluator_format>

<evaluator_types>
- **LLM as Judge** - Uses an LLM to grade outputs. Best for subjective quality (accuracy, helpfulness, relevance).
- **Custom Code** - Deterministic logic. Best for objective checks (exact match, trajectory validation, format compliance).
- **Trajectory Evaluators** - Check tool call sequences.
</evaluator_types>

<llm_judge>
### Python LLM as Judge

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

### JavaScript LLM as Judge

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
</llm_judge>

<code_evaluators>
### Python Exact Match

```python
def exact_match_evaluator(run, example):
    output = run["outputs"].get("expected_response", "").strip().lower()
    expected = example["outputs"].get("expected_response", "").strip().lower()
    match = output == expected
    return {"exact_match": 1 if match else 0, "comment": f"Match: {match}"}
```

### JavaScript Exact Match

```javascript
function exactMatchEvaluator(run, example) {
  const output = (run.outputs?.expected_response ?? "").trim().toLowerCase();
  const expected = (example.outputs?.expected_response ?? "").trim().toLowerCase();
  const match = output === expected;
  return { exact_match: match ? 1 : 0, comment: `Match: ${match}` };
}
```

### Python Trajectory Validation

```python
def trajectory_evaluator(run, example):
    trajectory = run["outputs"].get("expected_trajectory", [])
    expected = example["outputs"].get("expected_trajectory", [])
    exact = trajectory == expected
    all_tools = set(expected).issubset(set(trajectory))
    return {
        "trajectory_match": 1 if exact else 0,
        "comment": f"Exact: {exact}, All tools: {all_tools}"
    }
```

### JavaScript Trajectory Validation

```javascript
function trajectoryEvaluator(run, example) {
  const trajectory = run.outputs?.expected_trajectory ?? [];
  const expected = example.outputs?.expected_trajectory ?? [];
  const exact = JSON.stringify(trajectory) === JSON.stringify(expected);
  const allTools = expected.every(tool => trajectory.includes(tool));
  return {
    trajectory_match: exact ? 1 : 0,
    comment: `Exact: ${exact}, All tools: ${allTools}`
  };
}
```
</code_evaluators>

<upload>
### Python Upload

```bash
python upload_evaluators.py list
python upload_evaluators.py upload my_evaluators.py \
  --name "Exact Match" \
  --function exact_match \
  --dataset "Skills: Final Response" \
  --replace
python upload_evaluators.py delete "Exact Match"
```

### JavaScript Upload

```bash
npx tsx upload_evaluators.ts list
npx tsx upload_evaluators.ts upload my_evaluators.js \
  --name "Exact Match" \
  --function exactMatch \
  --dataset "Skills: Final Response" \
  --replace
npx tsx upload_evaluators.ts delete "Exact Match"
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

<example_workflow>
### Python Evaluator Workflow

```bash
cat > evaluators.py <<'EOF'
def exact_match(run, example):
    output = run["outputs"].get("expected_response", "").strip().lower()
    expected = example["outputs"].get("expected_response", "").strip().lower()
    match = output == expected
    return {"exact_match": 1 if match else 0, "comment": f"Match: {match}"}
EOF

python upload_evaluators.py upload evaluators.py \
  --name "Exact Match" \
  --function exact_match \
  --dataset "Skills: Final Response" \
  --replace
```

### JavaScript Evaluator Workflow

```bash
cat > evaluators.js <<'EOF'
function exactMatch(run, example) {
  const output = (run.outputs?.expected_response ?? "").trim().toLowerCase();
  const expected = (example.outputs?.expected_response ?? "").trim().toLowerCase();
  const match = output === expected;
  return { exact_match: match ? 1 : 0, comment: `Match: ${match}` };
}
EOF

npx tsx upload_evaluators.ts upload evaluators.js \
  --name "Exact Match" \
  --function exactMatch \
  --dataset "Skills: Final Response" \
  --replace
```
</example_workflow>

<running_evaluations>
### Python

```python
from langsmith import Client

client = Client()

def run_agent(inputs: dict) -> dict:
    result = your_agent.invoke(inputs)
    return {"expected_response": result}

results = await client.aevaluate(
    run_agent,
    data="Skills: Final Response",
    evaluators=[exact_match_evaluator, accuracy_evaluator],
    experiment_prefix="skills-eval-v1",
    max_concurrency=4
)
```

### JavaScript

```javascript
import { Client } from "langsmith";

const client = new Client();

async function runAgent(inputs) {
  const result = await yourAgent.invoke(inputs);
  return { expected_response: result };
}

const results = await client.evaluate(
  runAgent,
  {
    data: "Skills: Final Response",
    evaluators: [exactMatchEvaluator, accuracyEvaluator],
    experimentPrefix: "skills-eval-v1",
    maxConcurrency: 4
  }
);
```
</running_evaluations>

<resources>
- [LangSmith Evaluation Concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [Custom Code Evaluators](https://changelog.langchain.com/announcements/custom-code-evaluators-in-langsmith)
- [OpenEvals - Readymade Evaluators](https://github.com/langchain-ai/openevals)
</resources>
