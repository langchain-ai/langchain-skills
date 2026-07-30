# Trace Inspection

How to discover trace field names for use in evaluator `variable_mapping` (LLM evaluators) and `run.inputs`/`run.outputs` (code evaluators).

Always inspect traces before building an evaluator. Never guess field names.

## Procedure

1. Ask the user for their LangSmith project name.
2. Fetch 3--5 recent traces:

```python
from langsmith import Client

client = Client()
runs = list(client.list_runs(project_name="<project>", limit=5))
```

3. For each run, print:
   - `run.name` -- the run name (often the chain or agent class)
   - `run.run_type` -- `chain`, `llm`, `tool`, `retriever`, etc.
   - `list(run.inputs.keys())` -- available input field names
   - `list(run.outputs.keys())` -- available output field names
   - Truncated samples of `run.inputs` and `run.outputs` (cap at ~2000 chars)

4. Identify which fields carry the data the evaluator needs.

## Common field name patterns

### Chatbot / conversational agent

```
inputs:  {"input": "user message"}      or  {"messages": [...]}
outputs: {"output": "assistant reply"}  or  {"messages": [...]}
```

Typical `variable_mapping`: `{"input": "input", "output": "output"}`

### RAG / retrieval chain

```
inputs:  {"input": "user question", "chat_history": [...]}
outputs: {"output": "answer", "context": [...]}
```

Context may appear as `"context"`, `"documents"`, or `"source_documents"`. Check the actual keys.

### Tool-calling agent

```
inputs:  {"input": "user request"}
outputs: {"output": "final answer"}
```

Tool calls appear in child runs, not in the top-level run's inputs/outputs. The top-level run still has `input` and `output` for the user-facing request and response.

### Custom chains

Field names depend on the chain's implementation. There is no universal schema -- this is why inspection is required.

## Mapping fields to evaluators

### LLM evaluators: `variable_mapping`

`variable_mapping` connects prompt template variables to top-level trace fields. Only top-level fields are supported.

```python
# If the prompt template uses {question} and {answer}:
VARIABLE_MAPPING = {
    "question": "input",    # template var -> trace field
    "answer": "output",
}
```

The template variables must match `{placeholders}` in the prompt messages. The trace field values must match keys in `run.inputs` or `run.outputs`.

### Code evaluators: `run["inputs"]` and `run["outputs"]`

Code evaluators access trace data through the `run` dict:

```python
def perform_eval(run, example=None):
    inputs = run.get("inputs") or {}
    outputs = run.get("outputs") or {}
    user_input = inputs.get("input", "")
    agent_output = outputs.get("output", "")
    # ... evaluate ...
```

`run` is a plain dict at runtime -- use `run.get("inputs")`, not `run.inputs`. Always use `.get()` with defaults and guard against `None` outputs.

## Handling variations

### Nested structures

Some traces nest data inside wrapper keys:

```
inputs: {"input": {"question": "...", "context": "..."}}
```

For LLM evaluators, `variable_mapping` maps to top-level keys only. If data is nested, either:
- Map to the top-level key and handle the nested structure in the prompt
- Use a code evaluator instead, which can traverse nested dicts

### Inconsistent schemas

Different runs in the same project may have different field names if multiple chain types feed into one project. Inspect several traces to identify the common pattern. If schemas vary, a code evaluator with defensive `.get()` calls is more robust than an LLM evaluator with fixed `variable_mapping`.

### Missing outputs

Runs that errored may have `run["outputs"]` set to `None`. Code evaluators must handle this:

```python
def perform_eval(run, example=None):
    outputs = run.get("outputs")
    if outputs is None:
        return {"key": "my_check", "score": 0, "comment": "No output (run may have errored)"}
    # ... normal evaluation ...
```

LLM evaluators will receive an empty string for mapped fields when the trace field is missing.
