# LangGraph + LangSmith Skills for DeepAgents CLI

Agent skills for building, observing, and evaluating LangGraph agents with LangSmith.

## Installation

Install as a custom agent in [DeepAgents CLI](https://github.com/langchain-ai/deepagents/tree/master/libs/deepagents-cli):

```bash
./install.sh
```

The script will:
1. Prompt for agent name (defaults to `langchain_agent`)
2. Prompt for installation directory (defaults to `~/.deepagents`)
3. Ask for confirmation
4. Create agent directory with AGENTS.md and skills/
5. Error if the agent already exists

## Usage

Once installed, use the agent with:

```bash
deepagents --agent langchain_agent  # or your custom name
```

Set your LangSmith API key:

```bash
export LANGSMITH_API_KEY=<your-key>
```

## Available Skills

- **langgraph-code** - Building agents with LangGraph (primitives, context management, multi-agent patterns)
- **langsmith-trace** - Query and inspect agent execution traces
- **langsmith-dataset** - Generate evaluation datasets from traces
- **langsmith-evaluator** - Create custom evaluation metrics

## Development

The agent configuration lives in `config/`:

```
config/
├── AGENT.md           # Agent personality/instructions (copied as AGENTS.md)
└── skills/            # Skill modules
    ├── langgraph-code/
    ├── langsmith-trace/
    ├── langsmith-dataset/
    └── langsmith-evaluator/
```

To update an existing installation:

```bash
# Remove old installation (replace with your agent name)
rm -rf ~/.deepagents/langchain_agent

# Reinstall
./install.sh
```

## Testing

Validation tests are in `tests/` and verify that a fresh Claude Code instance can use the skills correctly:

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_trace_query.py
```
