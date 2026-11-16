---
name: langchain-langsmith-cli
description: Use when inspecting LangSmith traces, threads and tracing projects from the terminal with the langsmith CLI, attaching an LLM-as-judge evaluator to a project, or tracing a Python function with the LangSmith SDK.
---

# LangSmith CLI quickstart

The `langsmith` CLI reads and manages LangSmith resources from the terminal.
Authenticate with `langsmith auth login`, or set `LANGSMITH_API_KEY`.

## Find recent traces

List the five most recent traces in a project:

```bash
langsmith traces list --project my-app --limit 5
```

Tracing projects are also called sessions, and the CLI accepts both names.
Pass `--workspace` to any command to target another workspace:

```bash
langsmith sessions list --workspace $LANGSMITH_WORKSPACE_ID
```

List the threads that were active in the last hour:

```bash
langsmith threads list --project my-app --last-n-minutes 60
```

## Score live runs with an evaluator

Attach an LLM-as-judge evaluator to a project. Only a sample of runs is
scored, and runs that score below the threshold are flagged:

```bash
langsmith evaluators create-llm --name relevance --project my-app \
  --prompt prompt.json --sampling-rate 0.2 --threshold 0.8
```

## Trace a Python function

Decorate a function so every call is recorded as a run:

```python
from langsmith import trace_function

@trace_function
def answer(question: str) -> str:
    ...
```

Wrap an OpenAI client to trace its calls with `wrap_openai` from
`langsmith.wrappers`.

## Call the API directly

For anything the CLI has no command for, `langsmith api` calls the REST API
with your credentials, for example `langsmith api sessions?limit=5`.
