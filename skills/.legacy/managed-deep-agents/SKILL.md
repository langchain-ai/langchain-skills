---
name: managed-deep-agents
description: "Retired skill, replaced by `langchain-managed-deep-agents`. Use for building, testing, or deploying Managed Deep Agents in LangSmith with the mda CLI: it tells you to switch to `langchain-managed-deep-agents`."
metadata:
  internal: "true"
---

# managed-deep-agents (retired)

`managed-deep-agents` was retired from langchain-skills. Use the `langchain-managed-deep-agents` skill instead.

1. If `langchain-managed-deep-agents` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-managed-deep-agents --yes
   ```

3. Tell the user that `managed-deep-agents` is retired and that they can remove it with
   `npx skills remove managed-deep-agents`.
