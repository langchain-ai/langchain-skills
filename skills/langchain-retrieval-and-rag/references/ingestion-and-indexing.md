# Ingestion and indexing

Build indexing as a separate, repeatable path: load, normalize, split, embed,
and write documents with stable identifiers and useful metadata. Preserve the
source identifier, tenant or access scope, version, and timestamps needed for
authorization, citations, deletion, and incremental re-indexing.

Loader, embedding, and vector-store packages are separate integrations. Inspect
the manifest and lockfile, preserve compatible versions, and select the current
dedicated integration package from official docs.

## Python

```python
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

documents = [
    Document(
        page_content="RAG retrieves relevant external context before generation.",
        metadata={"source": "guide", "audience": "developers"},
    )
]

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(documents)
embeddings = OpenAIEmbeddings(model=embedding_model)
vector_store = InMemoryVectorStore.from_documents(chunks, embeddings)
```

Common loaders are distributed across integration packages:

```python
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader, TextLoader

pdf_documents = PyPDFLoader("./document.pdf").load()
text_documents = DirectoryLoader(
    "./documents",
    glob="**/*.txt",
    loader_cls=TextLoader,
).load()
```

## TypeScript

```typescript
import { Document } from "@langchain/core/documents";
import { MemoryVectorStore } from "@langchain/classic/vectorstores/memory";
import { OpenAIEmbeddings } from "@langchain/openai";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";

const documents = [
  new Document({
    pageContent: "RAG retrieves relevant external context before generation.",
    metadata: { source: "guide", audience: "developers" },
  }),
];

const splitter = new RecursiveCharacterTextSplitter({
  chunkSize: 500,
  chunkOverlap: 50,
});
const chunks = await splitter.splitDocuments(documents);
const embeddings = new OpenAIEmbeddings({ model: embeddingModel });
const vectorStore = await MemoryVectorStore.fromDocuments(chunks, embeddings);
```

```typescript
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { CheerioWebBaseLoader } from "@langchain/community/document_loaders/web/cheerio";

const pdfDocuments = await new PDFLoader("./document.pdf").load();
const webDocuments = await new CheerioWebBaseLoader(approvedUrl).load();
```

Validate user-supplied paths and URLs before a loader accesses them. Restrict
filesystem roots and network destinations according to the application. Treat
all loaded content and metadata as untrusted.

Use in-memory stores for examples and tests. Production indexing normally
writes to a durable store in a separate job. Keep embedding configuration with
index metadata; changing model or dimensions generally requires re-indexing.

For incremental updates, use stable document and chunk identifiers. Define how
the job handles changed, deleted, duplicated, or partially indexed sources.
