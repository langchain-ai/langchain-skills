# Reference: keep experiment traces in a tracing project too

By default, every run an experiment produces is recorded only in the
experiment's project. Teams sometimes also want those runs in their usual
tracing project, for example to search them alongside production or staging
traffic, or to run the same dashboards over them. Use trace replicas: the SDK
writes a copy of each run to every listed destination.

Leave this off unless someone needs it. Copies double the trace volume for
experiment traffic, and the experiment's own results never need them.

## Rules that are easy to get wrong

- **Replicas replace the default destination.** When `replicas` is set, runs go
  only to the listed destinations. A single replica pointing at the tracing
  project moves the runs out of the experiment, so its results lose their
  traces. Always list the experiment's own project as well.
- **Keep the experiment copy primary.** The primary replica keeps the original
  run IDs, which the experiment's results and evaluator feedback refer to.
  Every other replica gets new, deterministic run IDs.
- **Feedback goes to the run ID it names.** The experiment's evaluators score
  the original run IDs, so their feedback lands on the primary copy. To also
  attach feedback to a secondary copy, compute its run ID with
  `compute_run_id_for_secondary_replica`.
- **Reroot copies whose parent lives elsewhere.** If the copied runs start
  below the experiment's root (as in a remote agent service), mark that
  replica with `"updates": {"reroot": True}` so it becomes a standalone trace
  in the tracing project.

Replica options change between SDK versions; check the trace replicas docs and
the replica type in `langchain-reference` against the installed `langsmith`
version before writing this. The examples below pass replicas as dicts.

## When the experiment runs the agent in process

Wrap the `evaluate()` call. A primary replica with no project name falls back
to the experiment's project.

```python
from langsmith import Client, tracing_context

with tracing_context(
    replicas=[
        {"primary": True},                        # experiment copy
        {"project_name": "my-tracing-project"},   # extra copy
    ]
):
    Client().evaluate(target, data="my-dataset", evaluators=[...])
```

## When the target calls a deployed agent

The agent service applies the experiment's trace headers (see
[remote-agent-tracing.md](remote-agent-tracing.md)), so its runs nest under the
experiment's target run. To also keep a copy in the service's own project, set
replicas where the service applies those headers, behind a flag that is off by
default:

```python
import os
import langsmith as ls
from langsmith.run_trees import RunTree

def experiment_replicas(trace_headers: dict) -> list[dict] | None:
    if os.getenv("MIRROR_EXPERIMENT_TRACES", "false") != "true":
        return None
    parent = RunTree.from_headers(trace_headers)
    if parent is None:
        return None
    return [
        {"project_name": parent.session_name},  # experiment copy, unchanged
        {"project_name": os.environ["LANGSMITH_PROJECT"], "updates": {"reroot": True}},
    ]

with ls.tracing_context(parent=trace_headers, replicas=experiment_replicas(trace_headers)):
    return await graph.ainvoke(payload)
```

Here the experiment's project comes from the incoming `baggage` header, so the
service does not need to know it. The service-project copy is rerooted at the
agent's root run, because its parent exists only in the experiment project.
Requests without trace headers are unaffected.

## Verify

1. Run the experiment on one example.
2. The experiment looks the same as without replicas: same trace, scores, and
   token and cost columns.
3. The tracing project has a new trace for that example, rooted where you
   expect (the target in process, or the agent's root run when rerooted).
4. With the flag off, no new trace appears in the tracing project.
