# Evaluator Design

Best practices for designing LangSmith online evaluators. One quality dimension per evaluator.

## LLM-as-judge vs code: decision framework

| Factor | LLM-as-judge | Code evaluator |
|---|---|---|
| **Use when** | Success is subjective or semantic | Success is objective or deterministic |
| **Examples** | Relevance, helpfulness, safety, tone, factual grounding | Output exists, format validation, length thresholds, JSON structure, keyword presence |
| **Speed** | Slower (LLM inference per trace) | Fast (direct execution) |
| **Cost** | LLM token cost per evaluation | No additional cost |
| **Determinism** | Non-deterministic; may vary across runs | Fully deterministic |

**Rules of thumb:**
- If you can write a Python expression that decides pass/fail, use code.
- If a human would need to read and reason about the output, use an LLM judge.
- When in doubt, start with an LLM judge -- you can always replace it with code later if the criterion turns out to be fully decidable.

## LLM-as-judge best practices

### Reasoning-first schema

Always put a `reasoning` field before the score field in the Pydantic schema. This forces the LLM to explain before committing to a score, improving accuracy.

```python
class ResponseSchema(BaseModel):
    reasoning: str = Field(
        description="Step-by-step reasoning for the evaluation."
    )
    score: bool = Field(
        description="Whether the response meets the criterion."
    )
```

### Grounded rubrics

Write the system prompt as a clear rubric. The evaluator should assess the result, not whether it matches a reference answer or preferred process.

Good: "Does the response answer the user's question using information from the provided context?"

Bad: "Does the response match the expected answer?" (there is no expected answer in online evaluation)

### One quality per evaluator

Each evaluator should measure exactly one quality dimension. Combining multiple criteria (e.g., relevance AND tone AND safety) in a single evaluator makes scores uninterpretable and harder to debug.

Create separate evaluators for separate concerns:
- `relevance-evaluator` -- Does the response address the question?
- `safety-evaluator` -- Is the response free of harmful content?
- `tone-evaluator` -- Is the tone appropriate for the context?

### Variable mapping

Map only the trace fields the prompt actually uses. Passing unused fields adds noise. See [trace-inspection.md](trace-inspection.md) for how to discover available fields.

### Scoring types

- **Boolean** (`bool`): pass/fail -- simplest, use when the criterion is binary.
- **Numeric** (`float`, 0--1): granular scoring -- use when partial credit matters.
- **Categorical** (`str`): labels -- use when the result is a category, not a scale.

Use the simplest type that captures the distinction you need. Boolean is usually sufficient for online evaluation.

## Code evaluator best practices

### Access `run` as a dict

`run` is a plain dict at runtime, not an object. Use `run.get("inputs")` and `run.get("outputs")` -- never `run.inputs` or `run.outputs`.

`run.get("outputs")` can be `None` if the run errored. Always check:

```python
def perform_eval(run, example=None):
    outputs = run.get("outputs")
    if outputs is None:
        return {"key": "my_check", "score": 0, "comment": "No output"}
    # ... evaluate ...
```

### Self-contained

Code evaluators cannot import external packages. All logic must be in the `perform_eval` function body using only Python builtins and the standard library. No `import numpy`, no `import requests`, no `import langchain`.

### Descriptive keys

The `"key"` in the return dict appears as the score name in the LangSmith UI. Use descriptive, lowercase, underscore-separated names:
- `"has_output"` -- not `"check1"`
- `"response_length"` -- not `"len"`
- `"contains_greeting"` -- not `"g"`

### Return types

```python
# Boolean (pass/fail)
return {"key": "has_output", "score": True, "comment": "Output exists"}

# Numeric (0-1 scale)
return {"key": "response_length", "score": 0.75, "comment": "375 of 500 char target"}

# Integer
return {"key": "word_count", "score": 42, "comment": "42 words in response"}
```

## Anti-patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Guessing field names | Evaluator silently gets empty data | Inspect traces first |
| Using `run.inputs` (attribute access) | `AttributeError` -- `run` is a dict | Use `run.get("inputs")` |
| `def perform_eval(run, example)` without default | `TypeError` -- runtime passes one arg | Use `example=None` |
| Multiple criteria in one evaluator | Ambiguous scores | One quality per evaluator |
| Scoring against a reference answer | No reference exists in online eval | Score against a rubric |
| External imports in code evaluator | Runtime error | Use only builtins/stdlib |
| Ignoring `None` outputs | Crash on errored runs | Check `run.get("outputs") is None` |
| Generic score names (`"score"`, `"result"`) | Indistinguishable in UI | Use descriptive keys |
| Reasoning after score | LLM rationalizes instead of reasons | Put `reasoning` field first |

## Mental verification checklist

Before deploying an evaluator, mentally verify it against three cases:

1. **Good trace**: A run where the agent performed well. Does the evaluator give a passing score?
2. **Bad trace**: A run with a clear failure in the quality dimension. Does the evaluator give a failing score?
3. **Edge case**: A run with missing output, empty input, or unusual structure. Does the evaluator handle it without crashing?

If any case produces an unexpected result, revise the evaluator before deploying.
