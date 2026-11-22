---
name: langchain-typescript-quickstart
description: "Retired skill, replaced by `langchain-build-agent`. Use for starting a new LangChain agent in TypeScript: it tells you to switch to `langchain-build-agent`."
metadata:
  internal: "true"
---

# langchain-typescript-quickstart (retired)

`langchain-typescript-quickstart` was retired from langchain-skills. Use the `langchain-build-agent` skill instead.

1. If `langchain-build-agent` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-build-agent --yes
   ```

3. Tell the user that `langchain-typescript-quickstart` is retired and that they can remove it with
   `npx skills remove langchain-typescript-quickstart`.
