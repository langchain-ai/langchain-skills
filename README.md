# LangChain Skills

> **⚠️** — This project is in early development. APIs and skill content may change.

Agent skills for building agents with LangChain, LangGraph, and Deep Agents.

> For LangSmith-specific trace and dataset workflows, use [langsmith-skills](https://github.com/langchain-ai/langsmith-skills).

## Supported Coding Agents

These skills can be installed via [`npx skills`](https://github.com/vercel-labs/skills) for any agent that supports the [Agent Skills specification](https://skills.sh), including Claude Code, Cursor, Windsurf, and more.

## Installation

### Quick Install

Using [`npx skills`](https://github.com/vercel-labs/skills):

**Local** (current project):

```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes
```
**Global** (all projects):

```bash
npx skills add langchain-ai/langchain-skills --skill '*' --yes --global
```
To link skills to a specific agent (e.g. Claude Code):

```bash
npx skills add langchain-ai/langchain-skills --agent claude-code --skill '*' --yes --global
```

---

### Claude Code Plugin

Install directly as a [Claude Code plugin](https://code.claude.com/docs/en/plugins):

```bash
/plugin marketplace add langchain-ai/langchain-skills
/plugin install langchain-skills@langchain-skills
```

---

### Install Script (Claude Code & Deep Agents CLI only)

Alternatively, clone the repo and use the install script:

```bash
# Install for Claude Code in current directory (default)
./install.sh

# Install for Claude Code in a specific project directory
./install.sh ~/my-project

# Install for Claude Code globally
./install.sh --global

# Install for Deep Agents CLI in a specific project directory
./install.sh --deepagents ~/my-project

# Install for Deep Agents CLI globally (includes agent persona)
./install.sh --deepagents --global
```

| Flag / Argument | Description |
|------|-------------|
| `DIRECTORY` | Target project directory (default: current directory, ignored with `--global`) |
| `--claude` | Install for Claude Code (default) |
| `--deepagents` | Install for Deep Agents CLI |
| `--global`, `-g` | Install globally instead of current directory |
| `--force`, `-f` | Overwrite skills with same names as this package |
| `--yes`, `-y` | Skip confirmation prompts |

## Usage

After installation, set your API keys:

```bash
export OPENAI_API_KEY=<your-key>      # For OpenAI models
export ANTHROPIC_API_KEY=<your-key>   # For Anthropic models
```

Then run your coding agent from the directory where you installed (for local installs) or from anywhere (for global installs).

### Eval Engineering

To install only the eval-engineering skill:

```bash
npx skills add langchain-ai/langchain-skills --skill eval-engineering --yes
```

Or ask Codex: “Install the `eval-engineering` skill from `langchain-ai/langchain-skills`.”

Eval tasks require [Harbor](https://www.harborframework.com/docs). Run Harbor locally with Docker or use a supported cloud environment.

Then ask your coding agent:

```text
Use the eval-engineering skill to create a new eval Task for this project. Review the current repository and existing evals. Traces for this agent can be found here [optional Tracing Project/Location].
```

## Available Skills (15)

### Getting Started
- **build-agent** - Opinionated architecture guidance for starting and composing LangChain, LangGraph, Deep Agents, and Managed Deep Agents applications
- **langchain-dependencies** - Full package version and dependency management reference (Python + TypeScript)

### Deep Agents
- **deep-agents** - Build or modify applications with the open-source Deep Agents harness; includes routed Python and TypeScript quickstarts
- **managed-deep-agents** - Managed Deep Agents: deploy with the CLI, use the SDKs, stream runs, connect MCP tools, and build React `useStream` UIs

### Shared capabilities
- **memory-and-persistence** - Thread state, durable memory, and filesystem-backed context across supported frameworks
- **human-in-the-loop** - Interrupt, review, approval, edit, rejection, and resumable execution patterns
- **subagents-and-composition** - Delegation and composition among agents, tools, graphs, and specialized workers
- **middleware** - Cross-cutting agent behavior such as prompts, tools, planning, summarization, and guardrails

### LangChain
- **langchain** - Build or modify Python and TypeScript applications with models, tools, agents, and structured output
- **langchain-rag** - RAG pipeline (document loaders, embeddings, vector stores)

### LangGraph
- **langgraph** - Build or modify Python and TypeScript graphs with explicit state, nodes, edges, routing, parallelism, and streaming
- **langgraph-cli** - CLI lifecycle: scaffold, dev, build, deploy, langgraph.json config

### Evaluation
- **eval-engineering** - Design and audit Harbor Tasks while building reusable project World knowledge with human review
- **langsmith-online-eval-engineering** - Build online evaluators from LangSmith traces and production feedback signals

### Utilities
- **swarm** - Dispatch independent work items in parallel and aggregate the results
