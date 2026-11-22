---
name: langchain-middleware
description: "Retired skill, replaced by `langchain-build-agent`. Use for LangChain agent middleware: it tells you to switch to `langchain-build-agent`."
metadata:
  internal: "true"
---

# langchain-middleware (retired)

`langchain-middleware` was retired from langchain-skills. Use the `langchain-build-agent` skill instead.

1. If `langchain-build-agent` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-build-agent --yes
   ```

3. Tell the user that `langchain-middleware` is retired and that they can remove it with
   `npx skills remove langchain-middleware`.
