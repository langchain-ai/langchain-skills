# LangChain RAG in TypeScript

Inspect installed package versions and current integration docs before editing
an existing application. Preserve the project's package manager and module
style.

## End-to-end in-memory pipeline

```typescript
import { Document } from "@langchain/core/documents";
import { MemoryVectorStore } from "@langchain/classic/vectorstores/memory";
import { ChatOpenAI, OpenAIEmbeddings } from "@langchain/openai";
import { RecursiveCharacterTextSplitter } from "@langchain/textsplitters";

const chatModel = process.env.CHAT_MODEL;
const embeddingModel = process.env.EMBEDDING_MODEL;
if (!chatModel) throw new Error("CHAT_MODEL is required");
if (!embeddingModel) throw new Error("EMBEDDING_MODEL is required");

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
const retriever = vectorStore.asRetriever({ k: 4 });

const query = "What does RAG do?";
const matches = await retriever.invoke(query);
const context = matches.map((document) => document.pageContent).join("\n\n");

const model = new ChatOpenAI({ model: chatModel });
const response = await model.invoke([
  {
    role: "system",
    content: `Answer only from the supplied context. Say when it is insufficient.\n\n${context}`,
  },
  { role: "user", content: query },
]);
```

Use an in-memory store for examples and tests. Separate indexing from query
serving and choose a durable integration for production.

## Common loaders

```typescript
import { PDFLoader } from "@langchain/community/document_loaders/fs/pdf";
import { CheerioWebBaseLoader } from "@langchain/community/document_loaders/web/cheerio";

const pdfDocuments = await new PDFLoader("./document.pdf").load();
const webDocuments = await new CheerioWebBaseLoader(
  "https://docs.langchain.com",
).load();
```

Validate user-supplied paths and URLs before loading. Preserve source metadata
and treat all loaded content as untrusted.

## Persistent store example

```typescript
import { Chroma } from "@langchain/community/vectorstores/chroma";
import { OpenAIEmbeddings } from "@langchain/openai";

const embeddingModel = process.env.EMBEDDING_MODEL;
if (!embeddingModel) throw new Error("EMBEDDING_MODEL is required");

const embeddings = new OpenAIEmbeddings({ model: embeddingModel });
const vectorStore = await Chroma.fromDocuments(chunks, embeddings, {
  collectionName: "knowledge-base",
  url: "http://localhost:8000",
});
```

Keep the embedding model and dimensions consistent between indexing and query
serving. Re-index when changing an incompatible embedding configuration.

## Retrieval and agent tool

```typescript
import { createAgent } from "langchain";
import { tool } from "@langchain/core/tools";
import * as z from "zod";

const chatModel = process.env.CHAT_MODEL;
if (!chatModel) throw new Error("CHAT_MODEL is required");

const searchKnowledgeBase = tool(
  async ({ query }) => {
    const documents = await retriever.invoke(query);
    return documents.map((document) => document.pageContent).join("\n\n");
  },
  {
    name: "search_knowledge_base",
    description: "Search internal documentation relevant to a question.",
    schema: z.object({ query: z.string() }),
  },
);

const agent = createAgent({
  model: chatModel,
  tools: [searchKnowledgeBase],
  systemPrompt: "Use the knowledge base for questions about internal documentation.",
});
```

Vector-store filter syntax varies. Apply tenant and document authorization
filters during search and re-check every returned document before adding it to
model context. Return source metadata when the application needs citations.
