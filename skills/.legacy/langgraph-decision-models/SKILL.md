---
name: langgraph-decision-models
description: "Retired skill, replaced by `langchain-build-agent`. Use for routing a LangGraph agent with a decision model instead of an LLM: it tells you to switch to `langchain-build-agent`."
metadata:
  internal: "true"
---

# langgraph-decision-models (retired)

`langgraph-decision-models` was retired from langchain-skills. Use the `langchain-build-agent` skill instead.

1. If `langchain-build-agent` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-build-agent --yes
   ```

3. Tell the user that `langgraph-decision-models` is retired and that they can remove it with
   `npx skills remove langgraph-decision-models`.
