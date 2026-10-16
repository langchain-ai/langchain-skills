# Retrieval

Separate ingestion/indexing from querying. Inspect the existing data source,
search system, embedding configuration, and authorization boundaries before
introducing a new index. Existing databases or APIs may already supply retrieval.

Use a required retrieval step when every request must search; expose retrieval as
a tool when the agent should decide when to search. Use explicit workflow control
for bounded query rewriting, validation, or other deterministic steps around it.

Retrieve current integration documentation for the chosen loader, embedding model,
store, and framework. Preserve a compatible existing index unless a migration is
needed. Choose chunking and retrieval settings from measured results rather than
a universal recipe.

Retain the source metadata needed for citations, authorization, deletion, and
freshness. Authorize retrieved content before returning it. Define behavior for
no useful result, and verify grounding separately from whether retrieval ran.

Conversation memory and a knowledge index serve different purposes even if both
use durable storage. Evaluate retrieval with representative queries and inspect
the retrieved material as well as the final answer.
