---
name: LangChain Agent Starter Kit
description: "ALWAYS START HERE for any LangChain open source agent project. Invoke this skill before any other skill and before writing any code. Combines framework selection (LangChain vs LangGraph vs Deep Agents) with full dependency setup for Python and TypeScript into a single starting reference."
---

<overview>
**Always load this skill first.** It is the required starting point for any LangChain open source agent project — before choosing other skills, before writing code, before installing packages.

It answers two questions that every project must resolve upfront:

1. **Which framework should I use?** — LangChain, LangGraph, or Deep Agents
2. **What do I need to install?** — packages, versions, and environment setup

> Load this skill first. Once you've made these decisions, invoke the framework-specific skill for implementation details.
</overview>

---

## Step 1 — Pick Your Framework

The three frameworks are **layered**, not competing. Each builds on the one below:

```
┌─────────────────────────────────────────┐
│              Deep Agents                │  ← batteries included
│   (planning, memory, skills, files)     │
├─────────────────────────────────────────┤
│               LangGraph                 │  ← custom orchestration
│    (nodes, edges, state, persistence)   │
├─────────────────────────────────────────┤
│               LangChain                 │  ← foundation
│      (models, tools, prompts, RAG)      │
└─────────────────────────────────────────┘
```

Higher layers depend on lower ones — which means you can mix them. A LangGraph graph can be a subagent inside Deep Agents; LangChain tools work inside both.

<framework-decision>

Answer these questions in order to land on the right choice:

| Question | Yes → | No → |
|----------|-------|-------|
| Need planning, persistent memory, file management, or on-demand skills? | **Deep Agents** | ↓ |
| Need custom control flow — loops, branching, parallel workers, or human-in-the-loop? | **LangGraph** | ↓ |
| Single-purpose agent with a fixed set of tools? | **LangChain** (`create_agent`) | ↓ |
| Pure model call, chain, or retrieval pipeline with no agent loop? | **LangChain** (LCEL / chain) | — |

</framework-decision>

<framework-profiles>

| | LangChain | LangGraph | Deep Agents |
|---|-----------|-----------|-------------|
| **Control flow** | Fixed (tool loop) | Custom (graph) | Managed (middleware) |
| **Planning** | ✗ | Manual | ✓ Built-in |
| **File management** | ✗ | Manual | ✓ Built-in |
| **Persistent memory** | ✗ | With checkpointer | ✓ Built-in |
| **Subagent delegation** | ✗ | Manual | ✓ Built-in |
| **Custom graph edges** | ✗ | ✓ Full control | Limited |
| **Setup complexity** | Low | Medium | Low |
| **Next skill to load** | `langchain-agents` | `langgraph-fundamentals` | `deep-agents-core` |

</framework-profiles>

<mixing-note>
You can combine layers in the same project. The most common pattern: Deep Agents as the top-level orchestrator, with a compiled LangGraph graph registered as a specialized subagent. LangChain tools and chains are usable at every level.
</mixing-note>

---

## Step 2 — Set Up Your Dependencies

### Environment requirements

| | Python | TypeScript / Node |
|---|--------|-------------------|
| Runtime | **Python 3.10+** | **Node.js 20+** |
| LangChain | 1.0+ (LTS) | 1.0+ (LTS) |
| LangSmith SDK | >= 0.1.99 | >= 0.1.99 |

> **Always use LangChain 1.0+.** LangChain 0.3 is maintenance-only until December 2026 — do not start new projects on it.

---

### Core packages — always required

<python-core>
**Python**

| Package | Role | Version |
|---------|------|---------|
| `langchain` | Agents, chains, retrieval | `>=1.0,<2.0` |
| `langchain-core` | Base types & interfaces | `>=1.0,<2.0` |
| `langsmith` | Tracing, evaluation, datasets | `>=0.1.99` |
</python-core>

<typescript-core>
**TypeScript**

| Package | Role | Version |
|---------|------|---------|
| `@langchain/core` | Base types & interfaces (peer dep — install explicitly) | `^1.0.0` |
| `langchain` | Agents, chains, retrieval | `^1.0.0` |
| `langsmith` | Tracing, evaluation, datasets | `^0.1.99` |
</typescript-core>

---

### Orchestration — add based on your framework choice

<orchestration-packages>

| Framework | Python | TypeScript |
|-----------|--------|------------|
| LangGraph | `langgraph>=1.0,<2.0` | `@langchain/langgraph ^1.0.0` |
| Deep Agents | `deepagents` (depends on LangGraph; installs it as a transitive dep) | `deepagents` |

</orchestration-packages>

---

### Model providers — pick the one(s) you use

<provider-packages>

| Provider | Python | TypeScript |
|----------|--------|------------|
| OpenAI | `langchain-openai` | `@langchain/openai` |
| Anthropic | `langchain-anthropic` | `@langchain/anthropic` |
| Google Gemini | `langchain-google-genai` | `@langchain/google-genai` |
| Mistral | `langchain-mistralai` | `@langchain/mistralai` |
| Groq | `langchain-groq` | `@langchain/groq` |
| Cohere | `langchain-cohere` | `@langchain/cohere` |
| AWS Bedrock | `langchain-aws` | `@langchain/aws` |
| Azure AI | `langchain-azure-ai` | `@langchain/azure-openai` |
| Ollama (local) | `langchain-ollama` | `@langchain/ollama` |
| Hugging Face | `langchain-huggingface` | — |
| Fireworks AI | `langchain-fireworks` | — |
| Together AI | `langchain-together` | — |

</provider-packages>

---

### Common tools & retrieval — add as needed

<tool-packages>

| Package | Adds | Notes |
|---------|------|-------|
| `langchain-tavily` / `@langchain/tavily` | Tavily web search | Keep at latest; frequently updated for compatibility |
| `langchain-text-splitters` | Text chunking | Semver; keep current |
| `langchain-chroma` / `@langchain/community` | Chroma vector store | Dedicated integration package; keep at latest |
| `langchain-pinecone` / `@langchain/pinecone` | Pinecone vector store | Dedicated integration package; keep at latest |
| `langchain-qdrant` / `@langchain/qdrant` | Qdrant vector store | Dedicated integration package; keep at latest |
| `faiss-cpu` | FAISS vector store (Python only, local) | Via `langchain-community` |
| `langchain-community` / `@langchain/community` | 1000+ integrations fallback | **Python: NOT semver — pin to minor series** |
| `langsmith[pytest]` | pytest plugin | Requires `langsmith>=0.3.4` |

> Prefer dedicated integration packages over `langchain-community` when one exists — they are independently versioned and more stable. Keep tool packages (Tavily, vector stores) at latest since they release compatibility fixes alongside core updates.

</tool-packages>

---

### Dependency templates

<ex-langgraph-python>
<python>
LangGraph project — provider-agnostic starting point.
```
# requirements.txt
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langgraph>=1.0,<2.0
langsmith>=0.1.99

# Add your model provider:
# langchain-openai | langchain-anthropic | langchain-google-genai | ...

# Add tools/retrieval as needed:
# langchain-tavily | langchain-chroma | langchain-text-splitters | ...
```
</python>
</ex-langgraph-python>

<ex-langgraph-typescript>
<typescript>
LangGraph project — provider-agnostic starting point.
```json
{
  "dependencies": {
    "@langchain/core": "^1.0.0",
    "langchain": "^1.0.0",
    "@langchain/langgraph": "^1.0.0",
    "langsmith": "^0.1.99"
  }
}
```
</typescript>
</ex-langgraph-typescript>

<ex-deepagents-python>
<python>
Deep Agents project — provider-agnostic starting point.
```
# requirements.txt
deepagents
langchain>=1.0,<2.0
langchain-core>=1.0,<2.0
langsmith>=0.1.99

# Add your model provider:
# langchain-openai | langchain-anthropic | langchain-google-genai | ...
```
</python>
</ex-deepagents-python>

<ex-deepagents-typescript>
<typescript>
Deep Agents project — provider-agnostic starting point.
```json
{
  "dependencies": {
    "deepagents": "latest",
    "@langchain/core": "^1.0.0",
    "langchain": "^1.0.0",
    "langsmith": "^0.1.99"
  }
}
```
</typescript>
</ex-deepagents-typescript>

---

## Step 3 — Set Your Environment Variables

<environment-variables>
```bash
# LangSmith — always recommended for observability
LANGSMITH_API_KEY=<your-key>
LANGSMITH_PROJECT=<project-name>    # optional, defaults to "default"

# Model provider — set the one(s) you use
OPENAI_API_KEY=<your-key>
ANTHROPIC_API_KEY=<your-key>
GOOGLE_API_KEY=<your-key>
MISTRAL_API_KEY=<your-key>
GROQ_API_KEY=<your-key>
COHERE_API_KEY=<your-key>
FIREWORKS_API_KEY=<your-key>
TOGETHER_API_KEY=<your-key>
HUGGINGFACEHUB_API_TOKEN=<your-key>

# Common tool/retrieval services
TAVILY_API_KEY=<your-key>
PINECONE_API_KEY=<your-key>
```
</environment-variables>

---

## Step 4 — Load the Right Skill Next

<next-steps>

| Your choice | Invoke next |
|-------------|-------------|
| LangChain agent | `langchain-agents` |
| LangChain RAG | `langchain-rag` |
| LangChain models / streaming | `langchain-models` |
| LangGraph | `langgraph-fundamentals` |
| Deep Agents | `deep-agents-core` |
| Tracing & observability | `langsmith-trace` |
| Evaluation | `langsmith-evaluator` |
| Detailed dependency reference | `langchain-dependencies` |
| Framework choice deep-dive | `framework-selection` |

</next-steps>
