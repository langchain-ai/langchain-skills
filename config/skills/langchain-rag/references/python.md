# LangChain RAG in Python

Inspect installed packages and current LangChain integration docs before
editing an existing application. Loader, embedding, and vector-store packages
are separate integrations and should be installed only when selected.

## End-to-end in-memory pipeline

```python
import os

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

documents = [
    Document(
        page_content="RAG retrieves relevant external context before generation.",
        metadata={"source": "guide", "audience": "developers"},
    )
]

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(documents)

embeddings = OpenAIEmbeddings(model=os.environ["EMBEDDING_MODEL"])
vector_store = InMemoryVectorStore.from_documents(chunks, embeddings)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

query = "What does RAG do?"
matches = retriever.invoke(query)
context = "\n\n".join(document.page_content for document in matches)

model = ChatOpenAI(model=os.environ["CHAT_MODEL"])
response = model.invoke(
    [
        {
            "role": "system",
            "content": "Answer only from the supplied context. "
            "Say when the context is insufficient.\n\n" + context,
        },
        {"role": "user", "content": query},
    ]
)
```

Use this in-memory shape for tests or a minimal example. Production systems
usually separate indexing from query serving and use a durable vector store.

## Common loaders

```python
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader

pdf_documents = PyPDFLoader("./document.pdf").load()
text_documents = DirectoryLoader(
    "./documents",
    glob="**/*.txt",
    loader_cls=TextLoader,
).load()
```

Loader output is untrusted content. Preserve source metadata, validate user
supplied paths and URLs, and enforce the application's ingestion permissions.

## Persistent stores

```python
import os

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model=os.environ["EMBEDDING_MODEL"])
vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db",
    collection_name="knowledge-base",
)

reopened = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="knowledge-base",
)
```

Keep the embedding configuration with the index metadata. Changing models or
dimensions normally requires re-indexing.

## FAISS safety

```python
from langchain_community.vectorstores import FAISS

vector_store = FAISS.from_documents(chunks, embeddings)
vector_store.save_local("./faiss_index")

# Only opt in when this directory was created by this application and has
# remained under trusted control. FAISS metadata is pickle-backed.
trusted_store = FAISS.load_local(
    "./faiss_index",
    embeddings,
    allow_dangerous_deserialization=True,
)
```

Never enable dangerous deserialization for an index downloaded from a user,
artifact store, shared drive, URL, or third party.

## Retrieval and filtering

```python
results = vector_store.similarity_search(query, k=5)
scored = vector_store.similarity_search_with_score(query, k=5)

retriever = vector_store.as_retriever(
    search_type="mmr",
    search_kwargs={"k": 5, "fetch_k": 20, "lambda_mult": 0.5},
)
```

Vector-store filter syntax varies. Apply tenant and document authorization
filters in the supported store query, then verify every returned document
before including it in model context.

## Retrieval as an agent tool

```python
import os

from langchain.agents import create_agent
from langchain_core.tools import tool


@tool
def search_knowledge_base(query: str) -> str:
    """Search the internal knowledge base for information relevant to a question."""
    documents = retriever.invoke(query)
    return "\n\n".join(document.page_content for document in documents)


agent = create_agent(
    model=os.environ["CHAT_MODEL"],
    tools=[search_knowledge_base],
    system_prompt="Use the knowledge base for questions about internal documentation.",
)
```

Return citations or structured source metadata when the caller must show which
documents supported the answer.
