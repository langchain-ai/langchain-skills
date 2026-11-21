# Reference: build a graph evaluator

Use this when an evaluator needs several chained checks (code checks, LLM
judges, and decision models wired together) or the user asks for a graph or
multi-step evaluator. For a single judge or code check, follow the main skill
instead.

`openevals.graph` is experimental; its API may change between releases. Python
only. Never write a key into the evaluator file.

## Workflow

1. [Gather context](#gather-context): the agent's code and recent traces.
2. [Decide what to measure](#decide-what-to-measure): use the user's goal, or
   suggest one from the agent's type and confirm it.
3. [Choose models](#choose-models): code, a decision model, or an LLM judge for
   each node.
4. [Write the graph](#write-the-graph): one Python file.
5. [Test it locally](#test-it-locally) on real runs.
6. [Run it inside LangSmith](#run-it-inside-langsmith).

## Gather context

The agent or dataset decides the kind of evaluator:

- **Agent and environment** (or a tracing project): an online evaluator on that
  project's runs. The environment's `project_id` is its tracing project.
- **Dataset:** an offline evaluator on experiments over that dataset.

Read the agent code in the user's repo and a sample of its recent traces in
LangSmith (see `langchain-agent-tracing`), or, for a dataset, its examples and
recent experiment runs. Reuse any agent, environment, tracing project, dataset,
trace link, or code location already supplied in the conversation, the
selected agent or dataset, or local project configuration. Note what is still
missing:

- **Code:** its repository path or entry point.
- **Traces:** the agent and environment, or a representative trace link.

From the traces, note the fields the evaluator could read and how many tokens
they hold; input size decides the model (see Choose models):

- **The whole conversation** (a transcript, `all_messages`, or a trajectory):
  use the largest `prompt_tokens` among the trace's `llm` runs, from
  `token_usage` with `--include-metadata`. Don't use the root run's count: it
  adds up every model call in the trace, so it overstates the size.
- **Narrower fields** (a final answer, retrieved sources): estimate from their
  length, about 4 characters per token.

## Decide what to measure

Agree on two things before writing the evaluator: **what to measure** and
whether to score **each run or whole threads** (conversations).

If the user has said what to measure, use it. If not, suggest a starting
evaluator instead of only asking. Classify the agent from its code (system
prompt, tools, entry point) and traces or dataset examples (what users ask,
what it returns), then suggest the default for that type:

| Agent type | Examples | Default evaluator |
| --- | --- | --- |
| Customer service | Support chatbots, help desks | User satisfaction / frustration |
| Research & data analysis | Report writers, SQL or data Q&A, RAG over documents | Hallucination |
| Internal productivity | Ops assistants, ticket triage, workflow automation | Task completion |
| Code generation | Coding agents, code review, text-to-code | Code correctness |
| Content generation | Copywriting, summaries, drafts | User satisfaction / frustration |
| Sales / marketing automation | Lead research, outreach, CRM updates | Task completion |
| Other | Anything else | Hallucination |

- **User satisfaction / frustration:** a decision model reads the conversation
  and scores how frustrated the user is (`Score`, with levels such as "Calm,
  just stating facts", "Frustrated but civil", and "Very angry, strong language
  or threatening to leave") and whether they ended satisfied (`Noul`). Usually
  scores threads or trajectories. Use code when needed, such as trimming the
  conversation to fit the decision model's input size.
- **Hallucination:** whether every factual claim in the output is supported by
  the sources the agent had: retrieved documents, tool outputs, and query
  results. Usually scores trajectories, whose messages include those tool
  results. Pass the trajectory to a decision model, sized by input tokens (see
  Choose models), or to an LLM judge when checking claims takes reasoning, such
  as numbers or calculations. Use code only to trim the trajectory to fit the
  model.
- **Task completion:** whether the agent did what was asked. A decision model
  by default; an LLM judge with a reasoning model when completion means
  checking several steps or tool results.
- **Code correctness:** code checks first (the generated code parses; test,
  lint, or build tool calls in the trace succeeded), then an LLM judge with a
  reasoning model on whether the change does what was asked. A failed code
  check scores 0.

Ask one question that includes the suggestion and why it fits (the agent type
and the evidence), runs or threads, and any missing code or tracing context
from Gather context. Wait for the answer before writing the evaluator.

Then pin down the data:

- **Runs:** confirm the exact fields in `run.inputs` and `run.outputs`.
- **Threads:** prefer `trajectory` over the default `all_messages` when it's
  available: its messages include tool calls and tool results. It needs LangSmith Cloud or self-hosted
  v0.17 or later with queries switched to SmithDB. Otherwise, choose raw
  `thread`, `all_messages`, `human_ai_pairs`, or `first_human_last_ai`. An
  evaluator can't switch between `trajectory` and the other inputs once it's
  saved. Inspect representative data in the chosen format. For raw `thread`,
  confirm the fields needed in each root run's `inputs` and `outputs` in
  `thread.runs`.
- **Dataset:** also confirm its `example.outputs`.

## Choose models

Pick the cheapest node type that can make each judgment:

1. **Code** for anything deterministic: parsing, matching, counting, tool-call
   checks.
2. **Decision model** for yes/no, scale, and choice judgments. Cheaper and
   faster than an LLM judge, with calibrated probabilities. Choose by the size
   of the state each question reads:
   - **Under 32K tokens** (and the whole request under 64K): Jev,
     `model="typesafe:jev-latest"`.
   - **Over 32K tokens:** Jev with the long-context header (up to 262K tokens;
     slower and somewhat less accurate) or OpenAI Decisions. First, consider
     trimming the state in a code node (for example, by dropping tool schemas
     or repeated content).
3. **LLM judge** when the judgment needs reasoning: multi-step checks, math,
   comparing code against a request, or a written rationale. Use a reasoning
   model from whichever provider the user has keys for, such as
   `openai:gpt-5.5` or `anthropic:claude-sonnet-5-5`. Step up to a stronger
   model like `anthropic:claude-opus-5-5` when a test run shows the judge
   misjudging. It's highly unlikely you'll need a top-tier model like
   `claude-fable-5-1`: an evaluator runs on every run it scores, so pick the
   cheapest model that reasons well enough.

Optimize for cost throughout. If the user cares most about cost, build on
decision models and code. Keep LLM judges to the nodes that need reasoning.

Jev with the long-context header:

```python
import httpx2
from langchain_typesafe import TypeSafeClassifier
from openevals.graph import DecisionModel, Noul, Trajectory

grounded = DecisionModel(
    model=TypeSafeClassifier(
        model="jev-latest",
        client=httpx2.Client(timeout=120, headers={"TypeSafe-Danger-Zone-Long-Context": "true"}),
    ),
    inputs={"messages": Trajectory.messages},
    questions={"grounded": Noul(instructions="Is every factual claim in the final answer supported by the tool results?")},
    description="Checks the final answer's claims against the tool results",
)
```

For OpenAI Decisions, pass `model=OpenAIClassifier(model="gpt-6-luna")` instead
(`from langchain_openai.decisions import OpenAIClassifier`), with
`OPENAI_API_KEY` set.

## Write the graph

```bash
pip install "openevals==0.2.5"   # openevals[typesafe] for Jev; langchain-openai>=1.8.1 for OpenAI Decisions; langchain-<provider> for judges other than OpenAI
```

Set the provider keys the graph calls (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`TYPESAFE_API_KEY` for Jev). Never write a key into the evaluator file.

### Nodes

Make a node only for a meaningful step; keep small helpers as plain functions.
An evaluator with just a single node is fine and preferred if it can reliably
accomplish the user's goals. Every node is a top-level name in the file, so
LangSmith can read the graph from the source.

- **Code:** a function decorated with `@node` that returns a dict. A parameter
  named `run`, `thread`, `trajectory`, or `example` (or annotated `Run`,
  `Thread`, `Trajectory`, or `Example`) gets that context. To use another
  node's outputs, name a parameter after that node; the graph runs it first and
  passes its outputs dict.
- **LLM judge:** `LLM(model="<provider>:<model>", prompt=..., inputs={...},
  output_schema=...)`. `prompt` is a string or a list of `(role, content)`
  messages with `{{name}}` placeholders. `output_schema` is a TypedDict or
  Pydantic class defined in the file, or a JSON schema; without one, the node
  returns `{"score": number}`, and `feedback_key` renames that key.
- **Decision model:** `DecisionModel(model=..., inputs={...}, questions={...})`.
  `model` is required: `"typesafe:jev-latest"` or any
  `langchain_core.decisions.BaseDecisionModel` instance (see Choose models). It
  takes no prompt; its inputs are the state it judges, so each question names
  the inputs it compares. Each question key is an output of the node.

Questions are `langchain_core.decisions` types, re-exported by
`openevals.graph`, and take keyword arguments only:

```python
Noul(instructions="Does the answer address the question?")          # probability of yes
Score(instructions="How helpful is it?", criteria=["poor", "ok", "great"])  # index into criteria
Choice(instructions="Tone", criteria={"calm": None, "rude": None})   # chosen label
```

`inputs` maps each name to a typed reference, never a string:
`Run.inputs.question`, `Run.outputs.answer`, `Example.outputs.reference`, or
another node's output like `tool_usage.calls`.

### Rules for LangSmith

- Give each `LLM` and `DecisionModel` a `description="..."` and a code node a
  docstring so LangSmith can label the nodes; add `display_name="..."` when a
  name doesn't read well as a label.
- Write `LLM` and `DecisionModel` arguments as literal values, not computed
  ones like f-strings. The exceptions: `prompt` can name a string or list
  defined at the top of the file, `output_schema` can name a class defined in
  the file, and `model` can be a decision model instance (see Choose models).
- List every node in one `Graph([...])`.
- Define `evaluate(ctx)` and have it return a `score` and optional `comment`,
  so the feedback is named after the evaluator.
- LangSmith's sandbox proxy adds each selected workspace secret as a header on
  requests to that secret's allowed hosts, so the key never enters the sandbox
  or the file. The provider clients still need a key to start, so set a
  placeholder at the top of the file. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  and `TYPESAFE_API_KEY` have default hosts; other providers need an admin to
  configure allowed hosts first.
- To call the LangSmith API from the evaluator, use the `langsmith` SDK
  (`Client()`), not raw HTTP. LangSmith sets its endpoint and authenticates the
  calls in the sandbox, so the file needs no key. They run as whoever last
  saved the evaluator, so save production evaluators with a workspace service
  key.

### Example

A complete file that runs both locally and inside LangSmith:

```python
import os

for key in ("ANTHROPIC_API_KEY", "TYPESAFE_API_KEY"):
    os.environ.setdefault(key, "set-by-langsmith")

from openevals.graph import Choice, DecisionModel, Graph, LLM, Noul, Run, node

judge = LLM(
    model="anthropic:claude-sonnet-5-5",
    prompt="Check each step of this answer's reasoning. Score 0 to 1 for how sound it is: {{answer}}",
    inputs={"answer": Run.outputs.answer},
    description="Judges whether the answer's reasoning holds up",
)
checks = DecisionModel(
    model="typesafe:jev-latest",
    inputs={"question": Run.inputs.question, "answer": Run.outputs.answer},
    questions={
        "on_topic": Noul(instructions="Does the answer address the question?"),
        "tone": Choice(instructions="Tone", criteria={"calm": None, "rude": None}),
    },
    description="Checks the answer is on topic and calm",
)


@node
def answer(judge, checks):
    """Scores 0 unless the answer is on topic and calm."""
    ok = checks["on_topic"] > 0.5 and checks["tone"] == "calm"
    return {"score": judge["score"] if ok else 0}


graph = Graph([judge, checks, answer])


def evaluate(ctx):
    results = graph.run(ctx)
    return {"score": results[answer]["score"]}
```

`Graph([...])` checks the wiring when it is built: a parameter that names no
listed node, an output a node does not produce, or a cycle raises `ValueError`
before any model is called. Nodes run after the nodes they read, whatever order
they are listed in.

### Threads

To score whole threads, read the thread instead of `Run`. For the folded
formats (`all_messages`, `human_ai_pairs`, `first_human_last_ai`), read the
selected string through a code node's `ctx` parameter (for example,
`ctx.all_messages`). For `trajectory`, read its messages, including tool calls
and tool results, with `Trajectory.messages`. For raw `thread`, a code node's
`thread` parameter gets `thread_id`, `session_id`, and `runs`, the thread's
root runs in order, each with its `inputs` and `outputs`. Build what a judge
needs in a code node:

```python
@node
def transcript(thread):
    """Joins the thread's turns in order."""
    turns = [f"User: {r.inputs.question}\nAssistant: {r.outputs.answer}" for r in thread.runs]
    return {"text": "\n\n".join(turns)}


frustration = DecisionModel(
    model="typesafe:jev-latest",
    inputs={"conversation": transcript.text},
    questions={
        "frustration": Score(
            instructions="How frustrated is the user?",
            criteria=[
                "Calm, just stating facts",
                "Frustrated but civil",
                "Very angry, strong language or threatening to leave",
            ],
        ),
        "satisfied": Noul(instructions="Did the user end the conversation satisfied?"),
    },
    description="Reads the user's frustration and satisfaction",
)
```

## Test it locally

```python
graph_evaluator = graph.as_evaluator(answer)
```

`as_evaluator(node)` returns a `(run, example)` evaluator that runs the graph
and reports that node's `score` (and `comment`, if it returns one) under the
node's name; `key="..."` renames it. A node with exactly one output reports
that output instead. `run` and `example` can be LangSmith objects or dicts, and
`example` is optional for online evaluators.

Test it on a few real runs before attaching it anywhere: save each with
`langsmith runs get <run-id> --full --format json -o run.json`, load it
with `run = json.load(open("run.json"))`, call `graph_evaluator(run)`, and
check each node's output with `graph.run(run=run)`. With tracing on, the whole
graph is traced as a single evaluator trace that includes each node's output,
so a wrong final score can be traced to the node that produced it.

Use `graph_evaluator` offline by passing it to
`evaluate(..., evaluators=[graph_evaluator])` (see the main skill for run
functions and datasets).

## Run it inside LangSmith

Create it with the LangSmith CLI (`langsmith` 0.5.0 or later). Don't use
`langsmith evaluators upload`: it can't declare the packages a graph needs. The CLI reads `LANGSMITH_API_KEY`. Pass
`--workspace` with the workspace ID, and `--api-url` for a non-US or
self-hosted LangSmith, before `online-evaluators`. `@` reads a file's contents:

```bash
langsmith --workspace <workspace id> online-evaluators create --type code --name "Answer quality" \
  --code-evaluator.code @answer_quality.py \
  --code-evaluator.advanced-features-enabled \
  --code-evaluator.dependencies $'openevals[typesafe]==0.2.5\nlangchain-anthropic' \
  --code-evaluator.workspace-secrets-keys '[ANTHROPIC_API_KEY, TYPESAFE_API_KEY]'
```

- `--code-evaluator.dependencies` is one package per line: pin
  `openevals==0.2.5` (`openevals[typesafe]==0.2.5` when the file has a Jev
  decision model, as in this example), add `langchain-<provider>` for each
  judge provider other than OpenAI, and `langchain-openai>=1.8.1` for OpenAI
  Decisions. A graph evaluator needs its packages, so the workspace must
  support advanced code evaluators.
- `--code-evaluator.workspace-secrets-keys` takes a list, such as
  `'[ANTHROPIC_API_KEY, TYPESAFE_API_KEY]'`, naming the provider keys the file
  calls and matching the placeholders at the top of the file.
- **Runs** (the default): leave out `--code-evaluator.code-evaluator-input`.
- **Threads:** set `--code-evaluator.code-evaluator-input` to `thread`,
  `trajectory`, `all_messages`, `human_ai_pairs`, or `first_human_last_ai`.
  Only the selected representation is populated. A thread evaluator can only
  be attached to threads, and a run evaluator only to runs.

Then attach the evaluator to the tracing project (online) or dataset
(offline). To change it later, run
`langsmith --workspace <workspace id> online-evaluators update --evaluator-id <id> --code-evaluator.code @answer_quality.py`.

## Examples

[Use advanced code evaluators](https://docs.langchain.com/langsmith/advanced-code-evaluators)
has more examples of evaluators that run inside LangSmith:

- [Write the evaluator function](https://docs.langchain.com/langsmith/advanced-code-evaluators#write-the-evaluator-function):
  the `evaluate(ctx)` function and what `ctx` holds.
- [Score runs with a decision model](https://docs.langchain.com/langsmith/advanced-code-evaluators#score-runs-with-a-decision-model):
  trims a run's inputs and outputs in code, then asks Jev whether the output
  answers the input.
- [Evaluate threads](https://docs.langchain.com/langsmith/advanced-code-evaluators#evaluate-threads):
  each thread input (`thread`, `trajectory`, `all_messages`, `human_ai_pairs`,
  `first_human_last_ai`) and how to read it.
