---
name: deep-agents-core
description: "Retired skill, replaced by `langchain-build-agent`. Use for building agents with Deep Agents create_deep_agent: it tells you to switch to `langchain-build-agent`."
metadata:
  internal: "true"
---

# deep-agents-core (retired)

`deep-agents-core` was retired from langchain-skills. Use the `langchain-build-agent` skill instead.

1. If `langchain-build-agent` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-build-agent --yes
   ```

3. Tell the user that `deep-agents-core` is retired and that they can remove it with
   `npx skills remove deep-agents-core`.
