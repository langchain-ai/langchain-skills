# Managed Deep Agents project setup

## Check suitability

MDA is appropriate when the application needs a managed Deep Agent deployment,
durable threads, Context Hub instructions and skills, managed sandboxes,
schedules, channels, or the `mda` CLI. Confirm that the requested language and
managed capabilities are supported by the installed release.

Before scaffolding, identify the application's purpose, language, model,
required tools, data sources, caller identity, memory isolation, sandbox needs,
scheduled work, messaging channels, and deployment environment.

## Prerequisites

Inspect the project's dependency manifest and lockfile before changing packages.
Preserve its package manager and compatible versions, and verify current runtime
and package requirements against the installed MDA CLI and official docs.

- Python projects use the Python version supported by the installed MDA release
  and require `uv` for `mda dev`.
- TypeScript projects use a supported Node.js release and their existing package
  manager.
- Deployment requires LangSmith workspace access and the relevant provider or
  gateway credentials.

Keep `.env`, `.mda/`, generated build output, and local sandbox artifacts out of
version control.

## Scaffold

```bash
: "${MODEL:?MODEL is required}"
mda init research-assistant --model "$MODEL"
```

`mda init` fails when the destination already exists. In an existing project,
inspect and edit its files rather than scaffolding over them. Use `--gateway`
only when the user wants LangSmith Gateway, and `--no-sandbox` when the agent
does not need a shell or isolated filesystem.

## Project layout

```text
agent.py | agent.ts             required agent definition
instructions.md                 always-on system instructions
skills/<name>/SKILL.md          deploy-owned, on-demand procedures
memory.py | memory.ts           optional durable agent memory declaration
identity.py | identity.ts       caller authentication and ownership
tools/mcp.py | tools/mcp.ts     managed MCP server declaration
sandbox/*                       managed sandbox declaration
schedules/*                     managed schedules
channels/*                      managed messaging channels
.env                            local secrets; never archived
evals/harbor-job.json           user-owned Harbor job configuration
evals/<task>/*                  Harbor tasks; never deployed
```

Only the agent entry is required. MDA copies ordinary project modules, so local
`tools/` and `middleware/` folders are conventions except for the managed MCP
declaration at `tools/mcp.py` or `tools/mcp.ts`.

## Define the agent

### Python

```python
import os

from managed_deepagents import define_deep_agent
from tools.search import web_search

agent = define_deep_agent(
    name="research-assistant",
    model=os.environ["MODEL"],
    tools=[web_search],
)
```

### TypeScript

```typescript
import { defineDeepAgent } from "managed-deepagents";
import { webSearch } from "./tools/search";

const model = process.env.MODEL;
if (!model) throw new Error("MODEL is required");

export const agent = defineDeepAgent({
  name: "research-assistant",
  model,
  tools: [webSearch],
});
```

`name` is required and becomes the LangGraph assistant ID and default deployment
name. Set `MODEL` to a supported `provider:model-id`. Python and TypeScript may use
different provider slugs for the same integration; verify the current language
docs. Gateway model slugs use `provider/model-id` instead.

Do not set managed fields such as backend, store, checkpointer, managed memory,
deployed skills, or system prompt in the agent definition.

## Instructions and skills

Put standing behavior in project-root `instructions.md`. Deploy syncs it to
Context Hub, where it can be edited without changing source code.

Put reusable procedures under `skills/<name>/SKILL.md` with `name` and
`description` frontmatter. The agent sees discovery metadata at startup and
loads the full procedure only when relevant. A skill may include referenced
scripts, documentation, and templates.

Deployment treats instructions and skills as deploy-owned context: removed
local skill files are removed from the deployed copy on the next successful
sync. Keep agent-written knowledge in managed memory instead.
