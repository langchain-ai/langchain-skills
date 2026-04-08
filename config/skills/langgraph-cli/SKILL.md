---
name: langgraph-cli
description: "INVOKE THIS SKILL when using the langgraph CLI to scaffold, develop, build, or deploy LangGraph applications. Covers langgraph new, dev, build, up, deploy, and langgraph.json configuration."
---

<overview>
The `langgraph` CLI manages the full lifecycle of LangGraph applications — from scaffolding a new project to deploying it to LangGraph Platform (LangSmith Deployments).

Key commands:
- **`langgraph new`** — Scaffold a project from a template
- **`langgraph dev`** — Run locally with hot reload (no Docker)
- **`langgraph build`** — Build a Docker image
- **`langgraph up`** — Launch locally via Docker Compose
- **`langgraph deploy`** — Ship to LangGraph Platform
- **`langgraph dockerfile`** — Generate a Dockerfile

All commands (except `new`) read from a `langgraph.json` config file in the project root.
</overview>

## When to use

Use this skill when the user wants to:
- Scaffold a new LangGraph project
- Run a local development or production-like server
- Build or deploy a LangGraph application
- Understand or edit `langgraph.json` configuration
- Manage LangSmith Deployments (list, delete, view logs)

## Installation

```bash
# Python
pip install 'langgraph-cli[inmem]'   # includes langgraph dev support
pip install langgraph-cli             # without dev server (build/up/deploy only)

# JavaScript
npx @langchain/langgraph-cli         # use on demand
npm install -g @langchain/langgraph-cli  # install globally (available as langgraphjs)
```

## Commands

### `langgraph new [PATH]`

Scaffold a new project from a template.

```bash
langgraph new                          # interactive template selection
langgraph new ./my-agent               # create in specific directory
langgraph new --template agent-python  # skip prompt, use template directly
```

Available templates: `deep-agent-python`, `deep-agent-js`, `agent-python`, `new-langgraph-project-python`, `new-langgraph-project-js`

### `langgraph dev`

Run a local development server with hot reloading. No Docker required.

```bash
langgraph dev                              # default: localhost:2024
langgraph dev --port 8000                  # custom port
langgraph dev --config ./langgraph.json    # explicit config path
langgraph dev --no-reload                  # disable hot reload
langgraph dev --no-browser                 # don't auto-open LangGraph Studio
langgraph dev --host 0.0.0.0              # bind to all interfaces (trusted networks only)
langgraph dev --tunnel                     # expose via Cloudflare tunnel for remote access
langgraph dev --debug-port 5678            # enable remote debugger (requires debugpy)
langgraph dev --n-jobs-per-worker 20       # max concurrent jobs per worker (default: 10)
```

### `langgraph build`

Build a Docker image for the LangGraph API server.

```bash
langgraph build -t my-image                # required: tag the image
langgraph build -t my-image --no-pull      # use locally-built base images
langgraph build -t my-image -c langgraph.json  # explicit config
langgraph build -t my-image --base-image langchain/langgraph-server:0.2.18  # pin base version
```

### `langgraph up`

Launch the LangGraph API server via Docker Compose (includes Postgres).

```bash
langgraph up                               # default port 8123
langgraph up --port 8000                   # custom port
langgraph up --watch                       # restart on file changes
langgraph up --recreate                    # force fresh build (useful for pre-deploy validation)
langgraph up --postgres-uri postgresql://...  # external Postgres
langgraph up --no-pull                     # use local images (after langgraph build)
langgraph up --image my-image              # skip build, use pre-built image
langgraph up -d docker-compose.yml         # add extra Docker services
langgraph up --debugger-port 8124          # serve debugger UI
langgraph up --wait                        # block until services are healthy
```

### `langgraph deploy`

Build and deploy to LangGraph Platform (LangSmith Deployments). Requires Docker. On Apple Silicon (M1/M2/M3), Docker Buildx is also required for cross-compiling to `linux/amd64`.

```bash
langgraph deploy                           # deploy, name defaults to directory name
langgraph deploy --name my-agent           # explicit deployment name
langgraph deploy --deployment-type prod    # production deployment (default: dev)
langgraph deploy --tag v1.2.0              # custom image tag (default: latest)
langgraph deploy --deployment-id <id>      # update an existing deployment by ID
langgraph deploy --config ./langgraph.json # explicit config path
langgraph deploy --no-wait                 # don't wait for deployment status
langgraph deploy --verbose                 # show detailed server logs
```

Prereq: `LANGSMITH_API_KEY` in environment or `.env`.

`langgraph deploy` also accepts build flags: `--base-image`, `--pull`/`--no-pull`.

#### `langgraph deploy list`

```bash
langgraph deploy list                      # list all deployments
langgraph deploy list --name-contains bot  # filter by name
```

#### `langgraph deploy delete`

```bash
langgraph deploy delete <deployment-id>          # interactive confirmation
langgraph deploy delete <deployment-id> --force  # skip confirmation
```

#### `langgraph deploy logs`

```bash
langgraph deploy logs                                  # runtime logs, last 100
langgraph deploy logs --name my-agent                  # by deployment name
langgraph deploy logs --deployment-id <id>             # by deployment ID
langgraph deploy logs --type build                     # build logs instead of runtime
langgraph deploy logs -f                               # follow/stream logs
langgraph deploy logs --level error                    # filter by level (debug|info|warning|error|critical)
langgraph deploy logs -q "timeout"                     # search filter
langgraph deploy logs --limit 500                      # more entries
langgraph deploy logs --start-time 2026-03-08T00:00:00Z  # time range
```

### `langgraph dockerfile <SAVE_PATH>`

Generate a Dockerfile (and optionally Docker Compose files) without building.

```bash
langgraph dockerfile ./Dockerfile                      # generate Dockerfile
langgraph dockerfile ./Dockerfile --add-docker-compose # also generate compose + .env + .dockerignore
```

## `langgraph.json` reference

The configuration file used by all CLI commands (`dev`, `build`, `up`, `deploy`). Defaults to `langgraph.json` in the current directory.

### Minimal config (Python)

```json
{
    "dependencies": ["."],
    "graphs": {
        "agent": "./my_agent/agent.py:graph"
    },
    "env": "./.env"
}
```

### Minimal config (JavaScript)

```json
{
    "dependencies": ["."],
    "graphs": {
        "agent": "./src/agent.js:graph"
    },
    "env": "./.env"
}
```

### Full config with all keys

```json
{
    "dependencies": [".", "langchain_openai", "./local_package"],
    "graphs": {
        "agent": "./my_agent/agent.py:graph",
        "retriever": "./my_agent/rag.py:rag_graph"
    },
    "env": "./.env",
    "python_version": "3.12",
    "pip_config_file": "./pip.conf",
    "dockerfile_lines": [
        "RUN apt-get update && apt-get install -y ffmpeg"
    ]
}
```

### Key reference

| Key | Required | Description |
|-----|----------|-------------|
| `dependencies` | Yes | Array of dependencies. `"."` looks for local packages via `pyproject.toml`, `setup.py`, `requirements.txt`, or `package.json`. Can also be paths to subdirectories (`"./my_pkg"`) or package names (`"langchain_openai"`). |
| `graphs` | Yes | Mapping of graph ID to path. Format: `./path/to/file.py:variable` (Python) or `./path/to/file.js:function` (JS). The variable must be a `CompiledGraph` or a function returning one. Multiple graphs supported. |
| `env` | No | Path to a `.env` file (string) OR an inline mapping of env var names to values (object). For production deployments, prefer managing env vars in the LangSmith UI. |
| `python_version` | No | `"3.11"`, `"3.12"`, or `"3.13"`. Defaults to `"3.11"`. |
| `node_version` | No | Node.js version for JS projects. |
| `pip_config_file` | No | Path to a pip config file for custom package indexes. |
| `dockerfile_lines` | No | Array of additional Dockerfile lines appended after the base image import. Use for system packages, binaries, or custom setup. |

## Typical workflow

1. **Scaffold** — `langgraph new` to create a project from a template.
2. **Configure** — Edit `langgraph.json`: set dependencies, point `graphs` at your compiled graph(s), add `.env`.
3. **Develop** — `langgraph dev` for rapid local iteration with hot reload (no Docker, port 2024).
4. **Validate** — `langgraph up --recreate` to test in a production-like Docker stack (port 8123, includes Postgres).
5. **Deploy** — `langgraph deploy` to ship to LangGraph Platform (LangSmith Deployments).
6. **Monitor** — `langgraph deploy logs -f` to tail runtime logs; `--type build` for build logs.

## `langgraph dev` vs `langgraph up`

| Feature | `langgraph dev` | `langgraph up` |
|---------|----------------|----------------|
| Docker required | No | Yes |
| Install | `pip install 'langgraph-cli[inmem]'` | `pip install langgraph-cli` |
| Primary use | Rapid development & testing | Production-like validation |
| State persistence | In-memory / pickled to local dir | PostgreSQL |
| Hot reloading | Yes (default) | Optional (`--watch`) |
| Default port | 2024 | 8123 |
| Resource usage | Lightweight | Heavier (Docker containers for server, Postgres, Redis) |
| IDE debugging | Built-in DAP support (`--debug-port`) | Container debugging |

## Gotchas

- **`langgraph deploy` requires Docker** — On Apple Silicon (M1/M2/M3), Docker Buildx is also required for cross-compiling to `linux/amd64`.
- **`langgraph deploy` can only update its own deployments** — Deployments created through the LangSmith UI or GitHub integration cannot be updated with `langgraph deploy`. Use the UI for those.
- **`dependencies` must include all packages** — The `dependencies` array in `langgraph.json` must point to where your package config lives (e.g., `"."` for root). The actual packages are resolved from `pyproject.toml`, `requirements.txt`, or `package.json` at that location.
- **`env` is for local development only** — For production deployments, manage environment variables and secrets through the LangSmith UI after the deployment is created.
- **`langgraph dev` runs without Docker** — It runs directly in your environment. If your code depends on system packages (e.g., `ffmpeg`), they must be installed locally. Use `langgraph up` to validate Docker builds.
- **JavaScript CLI** — Use `npx @langchain/langgraph-cli <command>` (or `langgraphjs` if installed globally via `npm install -g @langchain/langgraph-cli`).
- **API key** — `LANGSMITH_API_KEY` is required for `langgraph deploy`. For `langgraph dev`, it is optional — the server runs without it, but you won't get traces in LangSmith. Can also be set via `LANGGRAPH_HOST_API_KEY` or `LANGCHAIN_API_KEY`.
