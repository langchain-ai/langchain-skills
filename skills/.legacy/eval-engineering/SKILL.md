---
name: eval-engineering
description: "Retired skill, replaced by `langchain-eval-engineering`. Use for agent evals, Harbor tasks, Task Specs, and benchmark design: it tells you to switch to `langchain-eval-engineering`."
metadata:
  internal: "true"
---

# eval-engineering (retired)

`eval-engineering` was retired from langchain-skills. Use the `langchain-eval-engineering` skill instead.

1. If `langchain-eval-engineering` is available, use it for this task.
2. Otherwise, install it, then use it:

   ```bash
   npx skills add langchain-ai/langchain-skills --skill langchain-eval-engineering --yes
   ```

3. Tell the user that `eval-engineering` is retired and that they can remove it with
   `npx skills remove eval-engineering`.
