---
name: langsmith
description: "This skill shows you how to use LangSmith. You should load this skill anytime the user is working on an LLM-backed AI agent or LLM application, or mentions anything remotely related to tracing, evaluation, experiments, or LangSmith. IMPORTANT: When this skill is loaded, you MUST immediately and thoroughly read the entire SKILL.md file before taking any action. Do not skim or skip sections — read every section in full, as each contains critical instructions, API patterns, and workflows you need to follow precisely. Use the bundled MCP tools (list_traces, get_trace, list_runs, get_run, list_datasets, show_dataset, list_experiments, show_experiment) to query LangSmith data directly."
---

# What is LangSmith

LangSmith is a platform that helps AI teams use live production data for continuous testing and improvement. Part of your job is to use LangSmith to help the user trace and evaluate their application or agent. Based on information you get from LangSmith traces — you can infer how to improve the agent or application you are working on towards the desired behavior.

1. **Observability**: LangSmith stores detailed traces of agent and LLM applications. LangSmith gives you crucial visibility into exactly what your AI agent or LLM application is doing, and helps you understand their behavior so you can update your prompts or agent architecture in general to improve behavior.
2. **Evaluation**: LangSmith allows you to run experiments and fetch experiment statistics. This is great for regression testing and testing behavioral edge cases for your agent. This is a critical part of agent engineering in order to ensure that your agent gets better over time between changes.

This skill enables two core flows:
1. **Understand what your agent is doing** by fetching and analyzing traces after every run
2. **Lock in good behavior** with regression tests (pytest/vitest/jest) that sync to LangSmith experiments

---

## Setup

### Environment Variables

> **IMPORTANT — Check this first:** Before doing ANY LangSmith work, verify that `LANGSMITH_API_KEY` is set by checking `.env`, the shell environment (`echo $LANGSMITH_API_KEY`), or asking the user. If it is missing or empty, **stop and tell the user** — all MCP tools and SDK calls will fail without it. Direct them to https://smith.langchain.com/settings to create an API key, then have them set it:
> ```bash
> export LANGSMITH_API_KEY=lsv2_pt_...
> ```
> `LANGSMITH_ENDPOINT` is optional and only needed for self-hosted or local LangSmith instances. If unset, the SDK defaults to `https://api.smith.langchain.com`. **The MCP tools bundled with this skill also respect `LANGSMITH_ENDPOINT`** — if it points to a local instance (e.g., `http://localhost:1980`), all MCP tool calls (`list_traces`, `get_trace`, etc.) will query the local LangSmith, not cloud. Do not assume MCP tools only work with cloud LangSmith.

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here   # Required — check for this before doing any LangSmith work
LANGSMITH_TRACING=true                          # Enables tracing
LANGSMITH_PROJECT=your-project-name             # Names the project traces go to (defaults to "default")
```

If `LANGSMITH_PROJECT` is not set, set it in the project's `.env` file so traces are organized by project. The MCP tools use `LANGSMITH_PROJECT` by default when no project is specified.

### Dependencies

Install the following packages using whatever package manager your project uses.

**Python** — install `langsmith` (or `langsmith[pytest]` if you plan to write pytest evaluations):
```bash
# Examples — use whichever package manager the project already uses
pip install langsmith
pip install "langsmith[pytest]"    # includes pytest plugin

uv add langsmith
uv add "langsmith[pytest]"

poetry add langsmith
poetry add "langsmith[pytest]"
```

**JavaScript/TypeScript** — install `langsmith`:
```bash
# Examples — use whichever package manager the project already uses
npm install langsmith
yarn add langsmith
pnpm add langsmith
bun add langsmith
```

---

## Adding Tracing

### LangChain/LangGraph Apps

If the user's code uses LangChain dependencies (e.g. langchain, langgraph, etc.), just set environment variables — tracing is automatic:

```bash
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY=<your-api-key>
```

Optional variables:
- `LANGSMITH_PROJECT` — specify project name (defaults to "default")
- `LANGCHAIN_CALLBACKS_BACKGROUND=false` — use for serverless to ensure traces complete before function exit

### Non-LangChain/LangGraph Apps

> **Check the codebase first:** If using OpenTelemetry, prefer the OTel integration (https://docs.langchain.com/langsmith/trace-with-opentelemetry). For Vercel AI SDK, LlamaIndex, Instructor, DSPy, or LiteLLM, see native integrations at https://docs.langchain.com/langsmith/integrations.

If not using an integration, use the `@traceable` decorator/wrapper and wrap your LLM client:

**Python:**
```python
from langsmith import traceable
from langsmith.wrappers import wrap_openai
from openai import OpenAI

client = wrap_openai(OpenAI())

@traceable
def my_llm_pipeline(question: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}],
    )
    return resp.choices[0].message.content
```

**TypeScript:**
```typescript
import { traceable } from "langsmith/traceable";
import { wrapOpenAI } from "langsmith/wrappers/openai";
import OpenAI from "openai";

const client = wrapOpenAI(new OpenAI());

const myLlmPipeline = traceable(async (question: string): Promise<string> => {
  const resp = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: question }],
  });
  return resp.choices[0].message.content || "";
}, { name: "my_llm_pipeline" });
```

Traces automatically appear in your LangSmith workspace.

### Best Practices

- **Apply `@traceable`/`traceable()` to all nested functions** you want visible in LangSmith. Only decorated/wrapped functions appear as separate spans in the trace hierarchy.
- **Wrapped clients auto-trace all calls** — `wrap_openai()`/`wrapOpenAI()` automatically records every LLM call without additional decorators.
- **Name your traces** for easier filtering: `@traceable(name="retrieve_docs")` or `traceable(myFunc, { name: "retrieve_docs" })`
- **Add metadata** for searchability: `@traceable(metadata={"user_id": "123", "feature": "chat"})`

**Python:**
```python
@traceable
def rag_pipeline(question: str) -> str:
    docs = retrieve_docs(question)  # traced if @traceable applied
    return generate_answer(question, docs)  # traced if @traceable applied

@traceable(name="retrieve_docs")
def retrieve_docs(query: str) -> list[str]:
    # retrieval logic
    return docs

@traceable(name="generate_answer")
def generate_answer(question: str, docs: list[str]) -> str:
    # LLM calls via wrapped client are auto-traced
    return client.chat.completions.create(...)
```

**TypeScript:**
```typescript
const retrieveDocs = traceable(async (query: string): Promise<string[]> => {
  // retrieval logic
  return docs;
}, { name: "retrieve_docs" });

const generateAnswer = traceable(async (question: string, docs: string[]): Promise<string> => {
  const resp = await client.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [{ role: "user", content: `${question}\nContext: ${docs.join("\n")}` }],
  });
  return resp.choices[0].message.content || "";
}, { name: "generate_answer" });

const ragPipeline = traceable(async (question: string): Promise<string> => {
  const docs = await retrieveDocs(question);
  return await generateAnswer(question, docs);
}, { name: "rag_pipeline" });
```

---

## Analyzing Traces

This is the core observability workflow. **After every agent run, you should fetch and analyze the trace.**

### Traces vs Runs

**Understanding the difference is critical:**

- **Trace** = A complete execution tree (root run + all child runs). A trace represents one full agent invocation with all its LLM calls, tool calls, and nested operations.
- **Run** = A single node in the tree (one LLM call, one tool call, etc.)

### MCP Tools Reference

This plugin provides the following MCP tools for querying LangSmith. Call them directly — no scripts or file paths needed.

**Trace tools:**
- `list_traces` — List traces matching filters (filters apply to root run)
- `get_trace` — Get a specific trace by ID with full run hierarchy

**Run tools:**
- `list_runs` — List individual runs matching filters (flat list)
- `get_run` — Get a specific run by ID

**Dataset tools:**
- `list_datasets` — List all LangSmith datasets
- `show_dataset` — Show examples from a dataset

**Experiment tools:**
- `list_experiments` — List experiments for a dataset with aggregate metrics
- `show_experiment` — Show detailed stats for a specific experiment

Key difference: `list_traces` filters apply to the ROOT RUN and return full hierarchy; `list_runs` filters apply to ANY run and return a flat list.

### The Analysis Workflow

**Do this after every agent run — it should be second nature:**

1. **Fetch the latest trace** using the `list_traces` MCP tool with `limit=1`

2. **Drill into it** using the `get_trace` MCP tool with the trace_id from step 1 (include_io=true for full details)

3. **Analyze the trace:**
   - Look at the LLM inputs and outputs — what prompts were sent? What did the model respond?
   - Check the tool call sequence — did the agent call the right tools in the right order?
   - Look at the decisions the agent made — does the reasoning make sense?
   - Check for errors, hallucinations, or unexpected behavior

4. **Report to the user:**
   - Explain what the agent did step by step
   - Highlight anything that looks wrong or suboptimal
   - Call out the specific LLM calls or tool calls that are interesting

5. **Ask the user:** "Does this look right? Is this the behavior you want?"

6. **If not right** → make prompt or agent code changes → run the agent again → fetch the new trace → repeat

### Common Filtering Patterns

```
# 5 most recent traces
list_traces(limit=5)

# Traces with errors in the last hour
list_traces(error=true, last_n_minutes=60)

# Slow traces (>= 5 seconds)
list_traces(min_latency=5.0)

# Traces with full hierarchy expanded
list_traces(limit=3, show_hierarchy=true)

# Only LLM runs (flat list)
list_runs(run_type="llm", limit=20)

# Failed tool calls
list_runs(run_type="tool", error=true)

# Runs from a specific trace
list_runs(trace_ids="<trace_id>", run_type="tool")
```

---

## Discovering What to Evaluate

When the user generically asks to "write evals" or "test my agent" **without specifying what to test**, don't write generic placeholder tests. Instead, use their tracing project to discover real problems and scope evals from actual agent behavior.

**Two paths into evals:**
1. **User tells you something specific** — write targeted evals for that issue directly.
2. **Generic request** — follow the discovery steps below first, then write evals for what you find.

**Discovery steps:**

1. **Find the tracing project** — check `LANGSMITH_PROJECT` in `.env` or environment. If not set, **ask the user** for the name of their LangSmith tracing project so you can look at existing traces.
2. **Look for problems** — prioritize errored traces (`list_traces(error=true)`), slow traces (`list_traces(min_latency=10.0)`), and failed tool calls (`list_runs(run_type="tool", error=true)`).
3. **Drill into interesting traces** — use `get_trace(trace_id="<id>", include_io=true)` and look for: errors, wrong tool selection, hallucinations, loops/retries, poor output quality, edge case inputs.
4. **Propose evals to the user** — group findings into categories (error handling, correctness, tool use, regression, edge cases) and describe what you'll test and why before writing code.
5. **Write targeted tests** — each eval should be tied to a real problem from the traces, use realistic inputs inspired by actual trace data, and assert against the specific failure mode observed.

---

## Querying Datasets

Use the `list_datasets` and `show_dataset` MCP tools to inspect LangSmith datasets.

### Common Patterns

```
# List all datasets in the workspace
list_datasets()

# Show first 5 examples from a dataset
show_dataset(dataset_name="My Agent Tests", limit=5)
```

---

## Testing & Experiments

Once agent behavior looks good based on manual testing and user feedback, lock it in with regression tests. Every time you make a change to the agent, you should be able to run all regression tests to make sure nothing broke. Tests sync to LangSmith as experiments so you can track results over time.

### Pytest (Python)

Based on `langsmith[pytest]` — the recommended way to write LangSmith regression tests in Python.

#### Setup

Ensure `langsmith[pytest]` is installed (e.g. `pip install "langsmith[pytest]"`, `uv add "langsmith[pytest]"`, `poetry add "langsmith[pytest]"`, etc.).

#### Environment Variables

```bash
LANGSMITH_TEST_SUITE="My Agent Tests"   # Names the test suite (creates a dataset in LangSmith)
LANGSMITH_EXPERIMENT="experiment-name"   # Optional: names the experiment run
```

#### Writing Tests

```python
import pytest
from langsmith import testing as t

@pytest.mark.langsmith
def test_agent_answers_correctly():
    # Log what you're testing with
    t.log_inputs({"question": "What is the capital of France?"})

    # Run your agent/LLM app
    result = my_agent("What is the capital of France?")

    # Log the output
    t.log_outputs({"answer": result})

    # Log what the correct answer should be (for future reference)
    t.log_reference_outputs({"answer": "Paris"})

    # Assert correctness
    assert "Paris" in result
```

#### The `expect()` API

Use `expect()` for fuzzy matching that logs feedback scores to LangSmith:

```python
from langsmith import expect

@pytest.mark.langsmith
def test_agent_response_quality():
    t.log_inputs({"question": "Explain quantum computing"})
    result = my_agent("Explain quantum computing")
    t.log_outputs({"answer": result})

    # String containment — logs a 0/1 feedback score
    expect(result).to_contain("qubit")
    expect(result).to_contain("superposition")

    # Embedding distance — logs a continuous similarity score
    expect(result).embedding_distance(
        "Quantum computing uses qubits and superposition",
        config={"threshold": 0.3}
    )

    # Edit distance — logs a string distance score
    expect(result).edit_distance("expected output", config={"threshold": 0.5})
```

#### Parametrized Tests

Use `@pytest.mark.parametrize` to test multiple cases. Set `output_keys` to tell LangSmith which params are outputs vs inputs:

```python
@pytest.mark.langsmith(output_keys=["expected"])
@pytest.mark.parametrize(
    "question, expected",
    [
        ("What is 2+2?", "4"),
        ("Capital of Japan?", "Tokyo"),
        ("Who wrote Hamlet?", "Shakespeare"),
    ],
)
def test_agent_multiple_cases(question, expected):
    t.log_inputs({"question": question})
    result = my_agent(question)
    t.log_outputs({"answer": result})
    t.log_reference_outputs({"answer": expected})
    assert expected.lower() in result.lower()
```

#### Async Tests

```python
import pytest

@pytest.mark.langsmith
@pytest.mark.asyncio
async def test_async_agent():
    t.log_inputs({"query": "async test"})
    result = await my_async_agent("async test")
    t.log_outputs({"result": result})
    assert result is not None
```

#### LLM-as-Judge in Tests

Use `t.trace_feedback()` to run an LLM judge and log its score as feedback:

```python
@pytest.mark.langsmith
def test_with_llm_judge():
    t.log_inputs({"question": "Explain relativity simply"})
    result = my_agent("Explain relativity simply")
    t.log_outputs({"answer": result})

    # Run an LLM judge — its trace is logged as feedback
    with t.trace_feedback():
        score = llm_judge(result, criteria="clarity and accuracy")

    t.log_feedback(key="judge_score", score=score)
```

#### Running Tests

```bash
# Basic run — test suite name sets the dataset
LANGSMITH_TEST_SUITE="My Agent" pytest tests/test_evals.py

# With a named experiment
LANGSMITH_TEST_SUITE="My Agent" LANGSMITH_EXPERIMENT="v2-prompt-change" pytest tests/test_evals.py

# Parallel execution
LANGSMITH_TEST_SUITE="My Agent" pytest tests/test_evals.py -n auto

# Rich output showing LangSmith results
LANGSMITH_TEST_SUITE="My Agent" pytest tests/test_evals.py --langsmith-output
```

### Vitest/Jest (JavaScript/TypeScript)

Based on the `langsmith` JS SDK (`>= 0.3.1`) — the recommended way to write LangSmith regression tests in JS/TS. Tests use a dedicated `ls` namespace that handles dataset sync, run tracking, and feedback logging automatically.

> **Important:** JSDom is NOT supported. Use `"node"` environment or omit the `environment` field entirely.

#### Setup

Ensure `langsmith` is installed along with your test runner (`vitest` or `jest`) and `dotenv`. For example:
```bash
# Vitest — use whichever package manager the project already uses
npm install -D vitest dotenv && npm install langsmith
yarn add -D vitest dotenv && yarn add langsmith
pnpm add -D vitest dotenv && pnpm add langsmith

# Jest — same idea
npm install -D jest dotenv && npm install langsmith
yarn add -D jest dotenv && yarn add langsmith
pnpm add -D jest dotenv && pnpm add langsmith
```

#### Config Files

Test files **must** end with `.eval.ts` (or `.eval.js`, `.eval.mts`, `.eval.cts`, `.eval.mjs`, `.eval.cjs`).

**Vitest — `ls.vitest.config.ts`:**
```typescript
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["**/*.eval.?(c|m)[jt]s"],
    reporters: ["langsmith/vitest/reporter"],
    setupFiles: ["dotenv/config"],
    testTimeout: 30000,
  },
});
```

**Jest — `ls.jest.config.cjs`:**
```javascript
module.exports = {
  testMatch: ["**/*.eval.?(c|m)[jt]s"],
  reporters: ["langsmith/jest/reporter"],
  setupFiles: ["dotenv/config"],
  testTimeout: 30000,
};
```

Add a script to `package.json`:
```json
{
  "scripts": {
    "eval": "vitest run --config ls.vitest.config.ts"
  }
}
```

Use `vitest run` (not `vitest`) to disable watch mode — recommended since LLM calls are slow.

#### Environment Variables

```bash
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here   # Required
LANGSMITH_TRACING=true                          # Enables tracing
LANGSMITH_PROJECT=your-project-name             # Names the project
LANGSMITH_TEST_TRACKING=false                   # Optional: dry-run mode (no sync to LangSmith)
```

#### The `ls` Namespace API

Import the `ls` namespace — all test declarations and logging go through it:

```typescript
import * as ls from "langsmith/vitest";
// OR for Jest:
import * as ls from "langsmith/jest";
```

**Test declaration:**
- `ls.describe(name, callback, options?)` — define a test suite (all tests must be inside one)
- `ls.test(name, example, callback)` — define a test case
- `ls.test.each(examples)(name, callback)` — parametrized tests over an array
- `ls.test.skip()` / `ls.test.only()` — skip or isolate tests
- `ls.describe.skip()` / `ls.describe.only()` — skip or isolate suites

**Logging:**
- `ls.logOutputs(outputs)` — record outputs for the run (also appears in LangSmith)
- `ls.logFeedback({ key, score })` — manually log a feedback metric
- `ls.wrapEvaluator(fn)` — wrap a custom evaluator so its result is auto-logged as feedback and traced separately

**Assertions:** Use the standard `expect` from vitest or jest — LangSmith does NOT provide its own `expect()`. Every test automatically gets a `pass` feedback key tracking assertion pass/fail.

#### Writing Tests

Each test receives an **example object** with `inputs` and optional `referenceOutputs`:

```typescript
import * as ls from "langsmith/vitest";
import { expect } from "vitest";

ls.describe("My Agent Tests", () => {
  ls.test(
    "agent answers correctly",
    {
      inputs: { question: "What is the capital of France?" },
      referenceOutputs: { answer: "Paris" },
    },
    async ({ inputs, referenceOutputs }) => {
      const result = await myAgent(inputs.question);

      // Log outputs — appears in LangSmith
      ls.logOutputs({ answer: result });

      // Standard vitest assertions
      expect(result).toContain(referenceOutputs?.answer);
    }
  );
});
```

**Returning outputs directly:** If the test callback returns a value, it is treated as the run's outputs (alternative to `ls.logOutputs()`):

```typescript
ls.test(
  "agent answers correctly",
  { inputs: { question: "What is 2+2?" }, referenceOutputs: { answer: "4" } },
  async ({ inputs }) => {
    const result = await myAgent(inputs.question);
    expect(result).toContain("4");
    return { answer: result }; // automatically logged as outputs
  }
);
```

#### Parametrized Tests

Use `ls.test.each()` with an array of example objects:

```typescript
const DATASET = [
  {
    inputs: { question: "What is 2+2?" },
    referenceOutputs: { answer: "4" },
  },
  {
    inputs: { question: "Capital of Japan?" },
    referenceOutputs: { answer: "Tokyo" },
  },
  {
    inputs: { question: "Who wrote Hamlet?" },
    referenceOutputs: { answer: "Shakespeare" },
  },
];

ls.describe("My Agent Tests", () => {
  ls.test.each(DATASET)(
    "agent handles question correctly",
    async ({ inputs, referenceOutputs }) => {
      const result = await myAgent(inputs.question);
      ls.logOutputs({ answer: result });
      expect(result.toLowerCase()).toContain(referenceOutputs?.answer.toLowerCase());
    }
  );
});
```

#### Using Existing LangSmith Datasets

Pull examples from a LangSmith dataset and run them as parametrized tests:

```typescript
import * as ls from "langsmith/vitest";
import { expect } from "vitest";
import { Client, type Example } from "langsmith";

const client = new Client();

const examples: Example[] = [];
for await (const example of client.listExamples({ datasetName: "My Agent Tests" })) {
  examples.push(example);
}

ls.describe("My Agent Tests", () => {
  ls.test.each(examples)(
    "agent handles dataset example",
    async ({ inputs, referenceOutputs }) => {
      const result = await myAgent(inputs.question);
      ls.logOutputs({ answer: result });
      expect(result).toContain(referenceOutputs?.answer);
    }
  );
});
```

#### Custom Evaluators

**Wrapped evaluators** — auto-logged as feedback and traced separately:

```typescript
const correctnessEvaluator = async (params: {
  outputs: { answer: string };
  referenceOutputs: { answer: string };
}) => {
  const isCorrect = params.outputs.answer
    .toLowerCase()
    .includes(params.referenceOutputs.answer.toLowerCase());
  return { key: "correctness", score: isCorrect ? 1 : 0 };
};

// Inside a test:
ls.test(
  "evaluated test",
  { inputs: { question: "Capital of France?" }, referenceOutputs: { answer: "Paris" } },
  async ({ inputs, referenceOutputs }) => {
    const result = await myAgent(inputs.question);
    ls.logOutputs({ answer: result });

    const wrapped = ls.wrapEvaluator(correctnessEvaluator);
    await wrapped({ outputs: { answer: result }, referenceOutputs });
  }
);
```

**Manual feedback logging:**

```typescript
ls.logFeedback({ key: "relevance", score: 0.9 });
```

**Using `openevals` prebuilt evaluators:**

```typescript
import { createLLMAsJudge, CORRECTNESS_PROMPT } from "openevals";

const judge = createLLMAsJudge({
  prompt: CORRECTNESS_PROMPT,
  feedbackKey: "correctness",
  model: "openai:o3-mini",
});

// Inside a test — feedback is auto-logged:
await judge({ inputs, outputs: { answer: result }, referenceOutputs });
```

#### LLM-as-Judge in Tests

```typescript
import { createLLMAsJudge, CORRECTNESS_PROMPT } from "openevals";

const judge = createLLMAsJudge({
  prompt: CORRECTNESS_PROMPT,
  feedbackKey: "judge_score",
  model: "openai:gpt-4o-mini",
});

ls.describe("Quality Tests", () => {
  ls.test(
    "response quality check",
    {
      inputs: { question: "Explain quantum computing simply" },
      referenceOutputs: { answer: "Quantum computing uses qubits and superposition" },
    },
    async ({ inputs, referenceOutputs }) => {
      const result = await myAgent(inputs.question);
      ls.logOutputs({ answer: result });

      // LLM judge — feedback auto-logged to LangSmith
      await judge({ inputs, outputs: { answer: result }, referenceOutputs });

      expect(result.length).toBeGreaterThan(0);
    }
  );
});
```

#### Suite-Level Configuration

`ls.describe` accepts an optional third argument for metadata and overrides:

```typescript
ls.describe("My Agent Tests", () => {
  // tests here
}, {
  testSuiteName: "custom-suite-name",   // Override suite name in LangSmith
  metadata: { version: "2.0" },         // Custom metadata on the experiment
});
```

#### Running Tests

```bash
# Vitest
vitest run --config ls.vitest.config.ts
# or via package.json script:
npm run eval

# Jest
jest --config ls.jest.config.cjs
```

#### Automatic Behaviors

Every `ls.test()` call automatically:
1. Syncs `inputs`/`referenceOutputs` as a **dataset example** in LangSmith
2. Traces the test execution as a **run**
3. Records `ls.logOutputs()` (or the return value) as run outputs
4. Records `ls.logFeedback()` / `ls.wrapEvaluator()` results as feedback
5. Tracks assertion pass/fail under the `pass` feedback key

### Checking Experiment Results

After running tests, use the `list_experiments` and `show_experiment` MCP tools to inspect the results.

#### Listing Experiments

List all experiments for a test suite / dataset:

```
list_experiments(dataset_name="My Agent Tests")
```

This returns all experiment runs against that dataset, including run counts, latency, cost, error rates, and feedback scores.

#### Showing Detailed Stats

Get full details for a specific experiment:

```
show_experiment(dataset_name="My Agent Tests", experiment_name="v2-prompt-change")
```

Shows latency (p50/p99), token usage, total cost, error rate, and all feedback keys with aggregate scores.

#### Comparing Experiments

After making a change and re-running tests, compare experiments:

```
list_experiments(dataset_name="My Agent Tests", limit=5)
```

Look at:
- **Run counts** — did all test cases run?
- **Error rate** — did more tests fail?
- **Feedback scores** — did quality improve?
- **Latency** — did the change make things slower?

#### Drilling Into Experiment Traces

> **Key concept: each experiment IS a tracing project.** When LangSmith runs an experiment, it creates a tracing project whose name is the experiment name (e.g., `"ample-bibliography-31"`). This means you use the experiment name as the `project` parameter when querying traces. Do NOT search for traces using your `LANGSMITH_PROJECT` value — that's the main application project, not the experiment project.

To find the experiment name, first call `list_experiments(dataset_name="...")` — each returned experiment has a name. Then use that name to query traces:

```
# Step 1: Find experiment names for a dataset
list_experiments(dataset_name="My Agent Tests")
# Returns experiments like: "v2-prompt-change", "ample-bibliography-31", etc.

# Step 2: List traces from a specific experiment (use experiment name as project)
list_traces(project="v2-prompt-change", limit=10)

# Find failed test cases
list_traces(project="v2-prompt-change", error=true)

# Get full details of a specific test case trace
get_trace(trace_id="<trace_id>")
```

### Test File Organization

**Python:**
```
tests/
├── conftest.py
├── test_evals/
│   ├── test_basic.py         # Core functionality tests
│   ├── test_edge_cases.py    # Edge cases found during manual testing
│   └── test_regression.py    # Tests added after fixing specific issues
```

**TypeScript:**
```
evals/
├── basic.eval.ts             # Core functionality tests
├── edge-cases.eval.ts        # Edge cases found during manual testing
├── regression.eval.ts        # Tests added after fixing specific issues
└── ls.vitest.config.ts       # Vitest config (or ls.jest.config.cjs for Jest)
```

---

## The Development Loop

This is the core autonomous workflow you should follow when helping a user build and improve their agent or LLM application.

### 1. SETUP
- Ensure tracing is enabled (env vars set, `@traceable`/`traceable()` if non-LangChain)
- Set `LANGSMITH_PROJECT` in `.env` if not already set
- Install dependencies using whatever package manager the project uses — Python: `langsmith` / `langsmith[pytest]`; JS/TS: `langsmith` + vitest or jest

### 2. RUN & OBSERVE
- Run the user's agent
- **Immediately** fetch the latest trace using `list_traces(limit=1)`
- Drill into the trace using `get_trace(trace_id="<id>", include_io=true)`
- Explain to the user: "Here's what your agent did..." — walk through the LLM calls, tool calls, and decisions

### 3. GET USER FEEDBACK
- Ask the user: "Does this look right? Is this the behavior you want?"
- Understand what the user wants changed
- This step is heavily driven by user feedback — don't skip it

### 4. ITERATE
- Make prompt or agent code changes based on user feedback
- Run the agent again
- Fetch the new trace, analyze it, compare to the previous trace
- Repeat until the user is happy with the behavior

### 5. LOCK IN WITH TESTS
- Once behavior is good, write regression tests (pytest for Python, vitest/jest for JS/TS)
- Each test captures a scenario that should keep working
- Python: `LANGSMITH_TEST_SUITE="My Agent" pytest tests/test_evals.py`
- JS/TS: `vitest run --config ls.vitest.config.ts` (or `jest --config ls.jest.config.cjs`)
- Check results using `list_experiments(dataset_name="My Agent")`
- **Even when all tests pass, analyze the traces.** A passing test only means assertions passed — it does not mean the agent behaved correctly. The agent may have taken unnecessary steps, made redundant LLM calls, used the wrong tools before arriving at the right answer, or produced correct output through flawed reasoning. Always drill into experiment traces after a test run to verify that the agent's actual execution path is what you expect, not just that the final output is correct.

### 6. ONGOING
- Next time a change is made, run the test suite to catch regressions
- If a test fails, inspect the experiment using `show_experiment(dataset_name="My Agent", experiment_name="<experiment-name>")`
- Remember: each experiment IS a tracing project — use the experiment name as the `project` parameter when querying traces
- Drill into failing traces using `list_traces(project="<experiment-name>", error=true)` then `get_trace(trace_id="<id>", include_io=true)`
- **Don't stop at failing traces — also spot-check passing ones.** Tests can pass for the wrong reasons (e.g., the agent hallucinated but happened to include the right keyword, or took a wildly inefficient path). After each test run, pick a few passing traces and review them with `get_trace(trace_id="<id>", include_io=true)` to confirm the agent's reasoning and execution path are sound.
- Fix, re-run, iterate
