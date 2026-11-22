---
name: swarm
description: "Retired skill, replaced by `langchain-build-agent`. Use for fanning work out to many parallel subagents with Deep Agents: it tells you to switch to `langchain-build-agent`."
metadata:
  internal: "true"
---

# swarm (retired)

`swarm` was retired from langchain-skills. Use the `langchain-build-agent` skill instead.
The swarm runtime skill has no direct replacement; `langchain-build-agent` covers subagent and fan-out patterns in Deep Agents.

1. If `langchain-build-agent` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-build-agent --yes
   ```

3. Tell the user that `swarm` is retired and that they can remove it with
   `npx skills remove swarm`.
