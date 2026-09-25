---
name: langgraph-decision-models
description: "INVOKE THIS SKILL when routing a LangGraph agent with a decision model (TypeSafe Jev, SemIf) instead of an LLM, or when auditing an existing agent for LLM calls that only produce a routing decision. Covers langchain-typesafe Noul/Choice/Score, reading answers correctly, threshold design, and LangSmith Gateway wiring."
---

<overview>
A **decision model** answers typed questions about state and returns probabilities instead of prose. It replaces the common pattern of prompting an LLM, parsing its text, and branching on the result.

- **`Noul(instructions=...)`** — binary question, returns a probability of yes
- **`Choice(instructions=..., criteria={...})`** — picks one label, returns the full distribution plus confidence
- **`Score(instructions=..., criteria=[...])`** — grades against an ordered rubric, returns an expected value plus confidence

`TypeSafeClassifier` is a LangChain `Runnable[ClassifierRequest, ClassifierResponse]`, so it drops into a node like any other runnable. Up to 32 questions share one request and are answered independently — your code combines them.

**Reach for one when** a node generates text only so you can parse a decision out of it: routing, triage, filtering, guardrails, or per-item classification over a batch.

**Do not** reach for one when the node's output is the product (summaries, drafts, code) or when the judgment needs multi-step reasoning. A decision model classifies; it does not think.
</overview>

---

## Install and wire

`langchain-typesafe` is alpha (`0.0.1a3`) and `TypeSafeClassifier` is marked `@beta` — pin it and expect churn.

```bash
uv add langchain-typesafe
```

Three ways to reach a model. The classifier POSTs to `{base_url}/v1/systemone` with `Authorization: Bearer {api_key}`, so switching providers is constructor arguments only:

<ex-wiring>
<python>
```python
import os
from langchain_typesafe import TypeSafeClassifier

# 1. TypeSafe directly (Jev). Reads TYPESAFE_API_KEY when api_key is omitted.
classifier = TypeSafeClassifier(model="jev-latest")

# 2. SemIf, hosted on the LangSmith Gateway. Note: LangSmith key, not a TypeSafe key.
classifier = TypeSafeClassifier(
    model="semif-qwen3.5-4b",
    api_key=os.environ["LANGSMITH_API_KEY"],
    base_url="https://gateway.smith.langchain.com",
)

# 3. Jev through the Gateway (BYOK). The `typesafe/` prefix routes to a
# TYPESAFE_API_KEY stored in LangSmith workspace secrets. Without that secret
# every `typesafe/*` id returns 424 Failed Dependency -- before the model name is
# even validated, so a 424 does not confirm the id is real.
classifier = TypeSafeClassifier(
    model="typesafe/jev-1.13.0",
    api_key=os.environ["LANGSMITH_API_KEY"],
    base_url="https://gateway.smith.langchain.com",
)
```
</python>
</ex-wiring>

---

## The conversion pattern

Ask every question about a page/item in **one** request, put the typed response in state, and let a plain function route on it. The router is ordinary Python — testable without touching a network.

<ex-classify-and-route>
<python>
```python
from typing import TypedDict
from langchain_typesafe import ClassifierResponse, Noul, Score, TypeSafeClassifier
from langgraph.graph import StateGraph, START, END

QUESTIONS = {
    "relevant": Score(
        instructions="How relevant is this ticket to a billing problem?",
        criteria=["Unrelated.", "Possibly related.", "Directly about billing."],
    ),
    "angry": Noul(instructions="Is the customer expressing anger?"),
}

class State(TypedDict):
    text: str
    answers: ClassifierResponse
    route: str

classifier = TypeSafeClassifier(model="jev-latest")

def classify(state: State) -> dict:
    # One request, every question. They are answered independently.
    return {"answers": classifier.invoke(
        {"state": state["text"], "questions": QUESTIONS}
    )}

def route(state: State) -> str:
    a = state["answers"]
    if a.nouls["angry"].noul > 0.7:
        return "escalate"
    if a.scores["relevant"].score < 0.5:
        return "close"
    return "handle"
```
</python>
</ex-classify-and-route>

Reading answers: `response.nouls[id].noul`, `response.choices[id].choice`, `response.scores[id].score`. Each view is keyed by your question id; `response.answers` holds them all.

---

## Three traps when reading answers

These cause silent misrouting, not exceptions.

**1. `Score.score` is an expected value, not a level.** It is a probability-weighted average over the rubric and is routinely fractional. `score == 0` almost never fires — a "not responsive" item lands at `0.07`, not `0`. Always compare against a band.

```python
if a.scores["relevant"].score < 0.5:   # correct
if a.scores["relevant"].score == 0:    # WRONG -- nearly never true
```

**2. Confidence measures distribution shape, not correctness.** On a `Score`, confidence reports how *concentrated* the rubric distribution is. An item sitting cleanly between two levels scores low confidence even when the model is entirely clear about it. A blanket `confidence < X -> escalate` rule therefore escalates items the model already decided. Gate on confidence only inside the ambiguous middle:

```python
if score < NOT_RELEVANT:                          # decisive -- trust it
    return "close"
if score < RELEVANT or confidence < MIN_CONF:     # ambiguous -- escalate
    return "human_review"
return "handle"
```

**3. Thresholds do not transfer between models.** Calibration is part of the model. The same policy over the same items routes differently on Jev vs SemIf vs an LLM adapter. Re-tune thresholds whenever you change models, and pin the model id.

---

## Question wording dominates accuracy

A loose question produces confident wrong answers, and no threshold fixes it. Use `criteria` to say what each outcome means, including what should *not* count.

In a measured case, "Is this a confidential communication with a lawyer?" scored a routine finance memo at **0.798**. Rewriting it to name the actual test — written by or to a lawyer, with an explicit carve-out for finance and accounting content — moved the same page to **0.005** while a genuinely privileged page held at **0.991**.

```python
Noul(
    instructions=(
        "Was this written by or to a lawyer, or does it convey a lawyer's legal "
        "advice? Answer no for ordinary business or accounting discussion, even "
        "when the subject is litigation-sensitive."
    ),
    criteria=NoulCriteria(
        true="A named attorney is author or recipient, or it relays legal advice.",
        false="Business or accounting content with no attorney involved.",
    ),
)
```

Before blaming the model, rewrite the question and re-measure.

---

## Auditing an existing agent

To find where a decision model fits, look for these in the codebase — see `references/conversion-playbook.md` for the full walkthrough.

| Signal | What to look for |
|---|---|
| Generate-then-parse | An LLM call whose output is immediately regex'd, `json.loads`'d, or string-matched into a branch |
| Prompted classifiers | Prompts containing "respond with one of", "answer yes or no", "rate from 1 to 5" |
| Sampling for cost | Comments or configs that check only the first N items because checking all is too expensive |
| Brittle rules | Keyword lists or regexes standing in for semantic judgment |
| Re-reading context | The same document re-sent to a model for each separate question |

The last two matter most: cheap semantic judgments change *what you can build*, not just the bill. If evaluating every item became affordable, what would you stop sampling?

---

## Expectations

Measured on a 24-item batch, identical LangGraph graph and routing policy, only the classifier swapped:

| | per item | tokens (6 items) | notes |
|---|---|---|---|
| Jev 1.13.0 | 0.27s | 3,648 in / 318 out | reports usage |
| SemIf 4B | 0.49s | not reported | hosted on the Gateway |
| Claude Sonnet 5 | 2.87s | 7,930 in / 864 out | via structured output |

Routing agreed on 4–5 of 6 items across engines; disagreements clustered on genuinely borderline items. Treat these as shape, not benchmarks — measure on your own workload.

**If you compare against an LLM baseline**, use `method="json_schema"` so the comparison is fair. LangChain's `with_structured_output` defaults to `method="function_calling"`, which injects a tool schema into every request — 556/35 tokens versus 228/12 for the native `output_config.format` path on the same one-field probe.

---

## Batching with Send

Classification is per-item and independent, so fan out with `Send` and let each item route on its own.

<ex-fan-out>
<python>
```python
from langgraph.types import Send

def fan_out(state):
    return [Send("classify_item", {"text": t}) for t in state["items"]]

builder.add_conditional_edges(START, fan_out, ["classify_item"])
```
</python>
</ex-fan-out>

Fan-out hides latency, so it flatters slow classifiers most: in the run above, Sonnet gained 8x from concurrency and Jev only 1.4x — yet Jev still finished first. Compare throughput, not the speedup multiple.

---

## Related skills

- **langgraph-fundamentals** — StateGraph, `Send`, `Command`, conditional edges
- **langgraph-human-in-the-loop** — `interrupt()` for the escalation branch above
- **langchain-middleware** — structured output when you need an LLM, not a classifier
