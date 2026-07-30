# LangSmith Online Evaluator API Reference

Working code patterns for creating and managing LangSmith online evaluators. All snippets are derived from the [online-evals](https://github.com/langchain-ai/langchain-skills) reference scripts and tested against `langsmith >= 0.9.8`.

## Setup

```python
from langsmith import Client

client = Client()  # uses LANGSMITH_API_KEY from environment
```

Required environment variables:

```
LANGSMITH_API_KEY=lsv2_pt_...
LANGSMITH_ENDPOINT=https://api.smith.langchain.com   # optional, this is the default
```

## Inspect traces

Trace inspection uses synchronous SDK methods. Use this to discover field names before building an evaluator.

```python
import json
from langsmith import Client

client = Client()
runs = list(client.list_runs(project_name="my-project", limit=5))

for i, run in enumerate(runs):
    print(f"--- Run {i + 1} (id: {run.id}) ---")
    print(f"Name: {run.name}")
    print(f"Run type: {run.run_type}")
    print(f"Input keys: {list(run.inputs.keys()) if run.inputs else 'None'}")
    print(f"Inputs: {json.dumps(run.inputs, indent=2, default=str)[:2000]}")
    print(f"Output keys: {list(run.outputs.keys()) if run.outputs else 'None'}")
    print(f"Outputs: {json.dumps(run.outputs, indent=2, default=str)[:2000]}")
```

Each run exposes: `.id`, `.name`, `.run_type`, `.inputs` (dict), `.outputs` (dict).

## Create an LLM-as-judge evaluator

LLM evaluators use a structured prompt pushed to the LangSmith Prompt Hub. All evaluator operations are async.

### 1. Define the response schema

```python
from pydantic import BaseModel, Field

class ResponseSchema(BaseModel):
    reasoning: str = Field(
        description="Step-by-step reasoning for the evaluation."
    )
    score: bool = Field(
        description="Whether the response meets the criterion."
    )
```

Put `reasoning` first so the LLM explains before scoring.

### 2. Build and push the prompt

```python
from langchain_core.prompts.structured import StructuredPrompt

PROMPT_MESSAGES = [
    ("system", "Evaluate the following response against the criterion: ..."),
    (
        "human",
        "User question: {input}\n\nAssistant response: {output}",
    ),
]

prompt = StructuredPrompt.from_messages_and_schema(
    PROMPT_MESSAGES,
    schema=ResponseSchema.model_json_schema(),
)

url = client.push_prompt("my-evaluator", object=prompt)
```

### 3. Create the evaluator

```python
import asyncio

async def create_llm_evaluator():
    created = await client.evaluators.create(
        name="my-evaluator",
        type="llm",
        llm_evaluator={
            "prompt_repo_handle": "my-evaluator",
            "commit_hash_or_tag": "latest",
            "variable_mapping": {
                "input": "input",
                "output": "output",
            },
        },
    )
    return created.evaluator.id

evaluator_id = asyncio.run(create_llm_evaluator())
```

### Variable mapping

`variable_mapping` connects prompt template variables to top-level trace fields. The keys are template variable names (appearing as `{name}` in the prompt), and the values are trace field paths.

Common mappings:

| Template variable | Trace field | Notes |
|---|---|---|
| `input` | `input` | Top-level `run.inputs` |
| `output` | `output` | Top-level `run.outputs` |

Discover available fields using trace inspection above.

## Create a code evaluator

Code evaluators run a Python function directly against each trace. The function must be self-contained (no external imports).

### Function signature

```python
def perform_eval(run, example=None):
    """
    Parameters:
        run: dict with keys "inputs" (dict), "outputs" (dict), "attachments"
        example: None for online evaluators (only set for dataset evals)

    Returns:
        dict with keys:
            "key": str       -- evaluator identifier
            "score": value   -- bool, int, or float
            "comment": str   -- optional explanation
    """
```

> **Important:** Two runtime constraints to be aware of:
> 1. `example` must default to `None`. The online evaluator runtime calls `perform_eval(run)` with a single argument -- `example` is only passed for dataset evaluators.
> 2. `run` is a plain **dict**, not an object. Use `run.get("inputs")` and `run.get("outputs")` -- not `run.inputs` or `run.outputs`. Attribute access will raise `AttributeError`.

### Example: check whether output exists

```python
import textwrap

EVALUATOR_CODE = textwrap.dedent("""\
    def perform_eval(run, example=None):
        \"\"\"Check whether the run produced any output.\"\"\"
        outputs = run.get("outputs")
        has_output = (
            outputs is not None
            and len(outputs) > 0
        )
        return {
            "key": "has_output",
            "score": bool(has_output),
            "comment": "Run produced output" if has_output else "Run had no output",
        }
""")
```

### Create the evaluator

```python
async def create_code_evaluator():
    created = await client.evaluators.create(
        name="has-output",
        type="code",
        code_evaluator={
            "code": EVALUATOR_CODE,
            "language": "python",
        },
    )
    return created.evaluator.id

evaluator_id = asyncio.run(create_code_evaluator())
```

## Attach evaluator to a project (run rules)

Run rules connect evaluators to tracing projects. The SDK does not have a dedicated run-rules wrapper, so use `httpx` against the REST API.

```python
import os
import httpx
from langsmith import Client

client = Client()
api_key = os.environ["LANGSMITH_API_KEY"]
endpoint = os.environ.get("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

# Look up project ID
project = client.read_project(project_name="my-project")

# Create run rule
resp = httpx.post(
    f"{endpoint}/api/v1/runs/rules",
    headers={"x-api-key": api_key},
    json={
        "display_name": f"eval-{project.name}",
        "session_id": str(project.id),
        "sampling_rate": 1.0,        # 1.0 = every trace, 0.1 = 10%
        "evaluator_id": EVALUATOR_ID,
        "is_enabled": True,
    },
    timeout=30,
)
resp.raise_for_status()

rule = resp.json()
print(f"Run rule created -> {rule['id']}")
```

### Payload reference

| Field | Type | Description |
|---|---|---|
| `display_name` | str | Human-readable label in UI |
| `session_id` | str (UUID) | Project ID (from `client.read_project`) |
| `sampling_rate` | float | 0.0--1.0; fraction of traces to evaluate |
| `evaluator_id` | str (UUID) | Evaluator ID from creation step |
| `is_enabled` | bool | Whether the rule is active |

## List, update, and delete evaluators

### List all evaluators

```python
async def list_evaluators():
    result = await client.evaluators.list()
    for ev in result.evaluators:
        projects = ""
        if ev.run_rules:
            projects = ", ".join(
                r.session_name or str(r.session_id)
                for r in ev.run_rules
                if r.session_id
            )
        print(f"{ev.name:<30} {str(ev.id):<38} {ev.type:<6} {projects}")

asyncio.run(list_evaluators())
```

> **Note:** The paginated result object uses `.evaluators` to access the list of evaluator objects. Some older examples may use `.data` -- this attribute was renamed in recent SDK versions.

### Update an evaluator

```python
async def update_evaluator():
    updated = await client.evaluators.update(
        evaluator_id=EVALUATOR_ID,
        name="renamed-evaluator",
    )
    print("Updated ->", updated.evaluator.id)

asyncio.run(update_evaluator())
```

### Delete an evaluator

```python
async def delete_evaluator():
    await client.evaluators.delete(
        evaluator_id=EVALUATOR_ID,
        delete_run_rules=True,  # also removes attached run rules
    )
    print("Deleted ->", EVALUATOR_ID)

asyncio.run(delete_evaluator())
```

## Async patterns

- **Evaluator operations** (`create`, `list`, `update`, `delete`) are async -- use `asyncio.run()` or `await` in an async context.
- **Trace inspection** (`client.list_runs`) and **project lookup** (`client.read_project`) are synchronous.
- **Run rules** use `httpx` (synchronous POST).
- `client.push_prompt` is synchronous.
