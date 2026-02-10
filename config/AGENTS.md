# LangChain + LangSmith Development Guide

This project uses skills that contain up-to-date patterns and working reference scripts.

## CRITICAL: Invoke Skills BEFORE Writing Code

**ALWAYS** invoke the relevant skill first - skills have the correct imports, patterns, and scripts that prevent common mistakes. The skills available to you are:

- **langchain-agents** - Invoke for ANY LangChain/LangGraph agent code
- **langsmith-trace** - Invoke for ANY trace querying or analysis
- **langsmith-dataset** - Invoke for ANY dataset creation from traces
- **langsmith-evaluator** - Invoke for ANY evaluator creation

Each skill includes reference scripts in `scripts/` - use these instead of writing from scratch.

## Modern LangChain Patterns

Use LangGraph for agent orchestration and `langchain_openai`/`langchain_anthropic` for models:

```python
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

@tool
def my_tool(query: str) -> str:
    """Tool description."""
    return result

model = ChatOpenAI(model="gpt-4o-mini")
agent = create_react_agent(model, tools=[my_tool])
```

## Skill Synergies

### Build → Trace → Dataset → Evaluate Pipeline

1. **Build agent** using `langchain-agents` patterns
2. **Run agent** to generate traces in LangSmith
3. **Query traces** using `langsmith-trace` to find interesting examples
4. **Create dataset** using `langsmith-dataset` from those traces
5. **Build evaluator** using `langsmith-evaluator` to measure quality

### Common Workflows

**Debugging a failing agent:**
1. Use `langsmith-trace` to query recent error traces
2. Examine the trace hierarchy to find where it failed
3. Fix the agent code using `langchain-agents` patterns

**Setting up evaluation:**
1. Generate traces by running your agent on test cases
2. Use `langsmith-dataset` to create a dataset (type: `final_response` for output quality, `trajectory` for step-by-step)
3. Use `langsmith-evaluator` to create metrics (LLM-as-judge for subjective, code-based for objective)

**Iterating on agent quality:**
1. Run evaluation to get baseline scores
2. Analyze low-scoring traces with `langsmith-trace`
3. Improve agent using `langchain-agents` best practices
4. Re-run evaluation to measure improvement

## Environment Setup

Required environment variables:
```bash
LANGSMITH_API_KEY=<your-key>
LANGSMITH_PROJECT=<project-name>  # Optional, defaults to "default"
OPENAI_API_KEY=<your-key>  # For OpenAI models
ANTHROPIC_API_KEY=<your-key>  # For Anthropic models
```

## Reference Scripts

When you invoke a skill, check its `scripts/` directory for working implementations you can adapt. These scripts handle common edge cases and use tested patterns.
