---
name: langchain-langgraph-cli
description: Scaffold, run, build, or deploy Agent Server applications with the LangGraph CLI, and create or modify langgraph.json. Use for langgraph new, dev, build, up, deploy, dockerfile, or LangSmith Deployment CLI operations.
---

# LangGraph CLI

Use the LangGraph CLI to package a graph or agent as an Agent Server. The
server exposes threads, runs, assistants, streaming, checkpointing, and store
APIs around the application declared in `langgraph.json`.

Inspect the repository and installed CLI before changing anything. Preserve
the existing language, package manager, graph exports, deployment method, and
configuration conventions. Run `langgraph <command> --help` or the JavaScript
equivalent before using flags because the CLI evolves quickly.

## Choose the path

| Need | Command |
| --- | --- |
| Start from an official template | `langgraph new` |
| Rapid local development without Docker | `langgraph dev` |
| Build the Agent Server image | `langgraph build` |
| Run the production-style stack locally | `langgraph up` |
| Build and deploy directly to LangSmith | `langgraph deploy` |
| Emit a Dockerfile for a custom build flow | `langgraph dockerfile` |

Use `dev` for fast iteration, then use `up` or a built image when behavior
depends on the container, system packages, database, or production server.
Deployment is an operational action: build and validate the concrete artifact
first, then follow the user's existing authorization and deployment workflow.

## Configuration

The CLI defaults to `langgraph.json`. At minimum, declare the dependency root
and one graph export:

```json
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent.py:graph"
  },
  "env": "./.env"
}
```

For JavaScript or TypeScript, point the graph entry at the corresponding source
module and set the supported Node version when the current schema requires it.
The graph value may reference a compiled graph or a supported graph factory.

Keep secrets out of `langgraph.json`, source, images, and logs. A local `env`
path may be used for development and deployment secret ingestion, but the file
must remain uncommitted. Treat inline environment mappings as public
configuration unless the repository's deployment system protects them.

## References

- For command choice, local development, builds, deployment, and troubleshooting,
  read [Commands and lifecycle](references/commands-and-lifecycle.md).
- For graph exports and advanced `langgraph.json` sections such as auth, store,
  checkpointer, HTTP, UI, and image settings, read
  [Configuration](references/configuration.md).

Validate the smallest relevant path. Confirm that the server imports every
graph, starts cleanly, exposes the expected assistant IDs, and can complete a
representative run. Container success does not prove application authorization,
external tools, or production credentials work.
