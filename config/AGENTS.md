# LangGraph + LangSmith Agent Development

## CRITICAL: Read This BEFORE Writing ANY Code

You have access to skills for building agents with LangGraph and observing/evaluating them with LangSmith.


### CORRECT Modern Patterns 
Prefer to use modern patterns when building with LangChain or LangGraph. Some examples include:

```python
from langchain_anthropic import ChatAnthropic  # CORRECT
from langchain_openai import ChatOpenAI  # CORRECT
from langchain.agents import create_agent  # CORRECT
from langchain_core.tools import tool  # CORRECT

@tool
def my_tool(input: str) -> str:
    """Tool description here."""
    return result

model = ChatAnthropic(model="claude-sonnet-4-5")
agent = create_agent(model=model, tools=[my_tool])
```
For more details, see the **langchain-agents** skill.

AVOID using the patterns below - they are deprecated and outdated. Always prefer the modern patterns under all circumstances.

```python
from langchain.agents import create_sql_agent  # use create_agent
from langchain.agents import create_react_agent  # use create_agent
from langchain.agents import create_tool_calling_agent  # use create_agent
```

### Skill rules

BEFORE writing code, ALWAYS consult the appropriate skill:

1. **langchain-agents** - For ANY coding involving LangChain/LangGraph
2. **langsmith-trace** - For ANY observability questions involving LangChain, LangGraph, or LangSmith
3. **langsmith-dataset** - For ANY questions around creating test datasets 
4. **langsmith-evaluator** - For ANY questions around evaluating agents

The skill will show you the CORRECT modern patterns with examples.

## When Building Agents

**Start simple.** Use `create_agent` or basic ReAct loops before adding complexity.

**Manage context early.** If your agent handles long conversations or large state, consult `langchain-agents` section 2:
- Subagent delegation (offload work, return summaries)
- Filesystem context (store paths not content)
- Message trimming (keep recent only)
- Compression (summarize old context)

**Track execution.** Ensure `LANGSMITH_API_KEY` is set. Traces appear automatically at https://smith.langchain.com

## When Debugging/Evaluating

**Investigate failures:** Use `langsmith-trace` to query recent runs, filter by error status, export to JSON

**Create test sets:** Use `langsmith-dataset` to generate datasets from production traces (final_response, trajectory, single_step, RAG types)

**Define metrics:** Use `langsmith-evaluator` for custom evaluation (LLM as Judge for subjective quality, custom code for objective checks)

## Common Patterns

**Research agent:** Subagent delegation + filesystem + LLM as Judge

**SQL agent:** Simple ReAct loop + exact match evaluation

**Multi-agent:** Supervisor pattern + compressed outputs + trajectory datasets

**Long-running:** Hierarchical state + checkpointing + message trimming
