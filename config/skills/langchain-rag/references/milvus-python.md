# Persistent Milvus retrieval in Python

Use Milvus Lite for local persistence, or connect to an existing Milvus server.
Install `langchain-milvus>=0.4,<0.5`, `milvus-lite>=3.2.2,<4`, and
`langchain-openai` in the project environment (Python 3.10+). The example uses
`OPENAI_API_KEY` for embeddings; the local database requires no service account.

```python
import os

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small", dimensions=512)
connection_args = {"uri": os.environ.get("MILVUS_DB_URI", "./langchain_milvus.db")}
if os.environ.get("MILVUS_TOKEN"):
    connection_args["token"] = os.environ["MILVUS_TOKEN"]

config = dict(
    embedding_function=embeddings,
    collection_name="langchain_milvus_demo",
    connection_args=connection_args,
    index_params={"index_type": "AUTOINDEX", "metric_type": "COSINE", "params": {}},
    consistency_level="Strong",
    enable_dynamic_field=True,
    auto_id=False,
    drop_old=False,
)
docs = [
    Document(page_content="Milvus Lite stores vectors locally between runs.",
             metadata={"source": "guide"}),
    Document(page_content="Milvus server supports multiple concurrent clients.",
             metadata={"source": "guide"}),
    Document(page_content="Bread is made from flour, water, and yeast.",
             metadata={"source": "recipe"}),
]

vectorstore = Milvus(**config)
try:
    # Stable IDs let the example update the same records on repeated runs.
    ids = ["guide:lite", "guide:server", "recipe:bread"]
    if vectorstore.client.has_collection(collection_name=config["collection_name"]):
        vectorstore.upsert(ids=ids, documents=docs)
    else:
        vectorstore.add_documents(documents=docs, ids=ids)
    vectorstore.client.flush(collection_name=config["collection_name"])
finally:
    vectorstore.client.close()

# Reopen the collection without dropping it or rebuilding its contents.
vectorstore = Milvus(**config)
try:
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 2, "expr": 'source == "guide"'},
    )
    results = retriever.invoke("How can I persist vectors locally?")
    for doc in results:
        print(doc.page_content, doc.metadata["source"])
finally:
    vectorstore.client.close()
```

Keep the embedding model and dimension unchanged when reopening a collection.
Use a fresh collection when changing embedding models, and avoid `drop_old=True`
for persisted data. A server URI selects a different database; moving local data
requires export/import or reingestion, not only a connection change. Lite 2.x
database files require migration before use with Lite 3.x.

See the [Milvus integration guide](https://docs.langchain.com/oss/python/integrations/vectorstores/milvus)
for deployment-specific options. This example covers the Python Lite workflow;
TypeScript clients connect to a Milvus server.
