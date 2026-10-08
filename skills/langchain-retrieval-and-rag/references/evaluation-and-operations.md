# Evaluation and operations

Evaluate retrieval separately from answer generation. Build a representative
set of questions with relevant source documents and measure whether authorized,
useful chunks appear near the top. Inspect failures caused by loading,
normalization, chunk boundaries, embeddings, filters, query formulation,
ranking, or context selection before changing the generation prompt.

Track metrics appropriate to the application, such as recall at `k`, precision
at `k`, ranking quality, citation correctness, no-answer behavior, latency, and
cost. Include adversarial documents containing instructions, unauthorized
sources, stale versions, and near-duplicates in evaluation.

Production operation should define:

- durable vector-store ownership, tenant isolation, encryption, backup, and
  recovery;
- source authorization, retention, deletion, and regional requirements;
- embedding and schema versions, migration, rollback, and re-indexing;
- freshness targets and handling for partial indexing failures;
- observability for ingestion, retrieval, empty results, and filter failures;
- limits on document size, query rate, result count, and model context use.

Changing an embedding model or dimensions usually requires a new index or a
controlled re-index. Avoid mixing vectors created by incompatible
configurations. Prefer versioned collections and an explicit cutover when the
application must remain available during migration.

## Serialized index safety

Some local vector stores serialize executable or object metadata. Python FAISS
metadata is pickle-backed. Never enable dangerous deserialization for an index
downloaded from a user, URL, artifact store, shared drive, or third party.

```python
from langchain_community.vectorstores import FAISS

vector_store = FAISS.from_documents(chunks, embeddings)
vector_store.save_local("./faiss_index")

# Only when this application created the directory and it remained under
# trusted control:
trusted_store = FAISS.load_local(
    "./faiss_index",
    embeddings,
    allow_dangerous_deserialization=True,
)
```

Do not deserialize LangChain objects with permissive class allowlists. Use an
explicit minimal allowlist and disable reading secrets from the environment
during deserialization. Prefer reconstructing integrations from trusted
configuration over loading serialized application objects.
