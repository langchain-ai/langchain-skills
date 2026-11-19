# Reference: trace a deployed agent into an experiment

Use this when the experiment's target function calls the agent over HTTP
instead of running it in process.

## The problem

The experiment and the agent service record two unrelated traces. The
experiment's trace has only the target's root run, with no model runs under
it, so:

- token and cost columns stay empty (they add up the model runs inside each
  example's trace), while feedback and latency still show;
- evaluators and anyone reviewing the experiment cannot see the agent's steps.

Join the two with distributed tracing. Both sides change: the caller sends the
trace context, and the service applies it.

## Caller: the target function

Inside the target, get the current run tree and merge its trace headers into
the request, following the distributed tracing docs. Merge them with existing
headers such as auth rather than replacing them. Read them in the target itself
and pass them along if the request is made elsewhere: a standard thread pool
does not carry tracing context, and on Python older than 3.11 async code may
not either.

## Service: apply the incoming context

When a request carries `langsmith-trace` (and `baggage`), run the agent inside
`tracing_context(parent=<those headers>)`. Requests without them behave as
before. The `baggage` header carries the experiment's project, so the service
does not need to know it.

```python
import langsmith as ls

trace_headers = {
    k: request.headers[k] for k in ("langsmith-trace", "baggage") if k in request.headers
}
if "langsmith-trace" in trace_headers and is_trusted_internal_caller(request):
    with ls.tracing_context(parent=trace_headers):
        return await graph.ainvoke(payload)
return await graph.ainvoke(payload)
```

An agent deployed on LangSmith Agent Server has its own setup; search the docs
for Agent Server distributed tracing. For a plain ASGI service where all
inbound traffic is trusted, the SDK's tracing middleware does the same for every
request.

**Trust:** these headers decide where runs are recorded and what metadata they
carry. Apply them only for trusted internal callers, such as the experiment
runner, using the service's existing service-to-service auth. Strip both
headers from public or end-user traffic at the gateway.

## Where the runs land

Once the service applies the headers, experiment requests are recorded only in
the experiment project; normal traffic still goes to the service's project.
If the service's project must also keep experiment traffic, follow
[experiment-trace-replicas.md](experiment-trace-replicas.md).

## Verify

1. Run the experiment on one example.
2. Open that example's trace: it should nest the target, the agent, its nodes,
   and the model calls.
3. The experiment's token and cost columns should fill in.
4. No new trace for that request should appear in the service's project.

If the service still records a separate root trace, the headers are not
arriving or the agent is not invoked inside the `tracing_context` block (for
example, it was handed to a background worker). Tokens without cost usually
means the model name has no pricing entry in the workspace.
