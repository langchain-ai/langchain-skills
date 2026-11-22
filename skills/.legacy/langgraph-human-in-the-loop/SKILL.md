---
name: langgraph-human-in-the-loop
description: "Retired skill, replaced by `langchain-build-agent`. Use for LangGraph interrupts and human-in-the-loop approval: it tells you to switch to `langchain-build-agent`."
metadata:
  internal: "true"
---

# langgraph-human-in-the-loop (retired)

`langgraph-human-in-the-loop` was retired from langchain-skills. Use the `langchain-build-agent` skill instead.

1. If `langchain-build-agent` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-build-agent --yes
   ```

3. Tell the user that `langgraph-human-in-the-loop` is retired and that they can remove it with
   `npx skills remove langgraph-human-in-the-loop`.
