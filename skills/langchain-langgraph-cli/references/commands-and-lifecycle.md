# Commands and lifecycle

Python installs expose `langgraph`; JavaScript can use
`npx @langchain/langgraph-cli` or a supported global installation. Preserve the
project's package manager and installed version rather than installing another
copy without need.

## Local development

`langgraph dev` starts a lightweight local server with reload behavior and does
not require Docker. Python development commonly requires the CLI's in-memory
extra. Use `--help` to confirm the current port, reload, browser, debugger,
tunnel, and concurrency flags.

The dev server is for trusted local development. Binding to all interfaces or
opening a tunnel exposes the application beyond the local machine; use the
repository's authentication and network policy before doing so.

## Container path

`langgraph build` produces an Agent Server image from `langgraph.json`.
`langgraph up` runs the containerized stack locally with its persistence
services. Use this path when validating OS packages, Dockerfile additions,
database behavior, or a deployment-like build.

`langgraph dockerfile` emits the generated Dockerfile for a custom build system.
Regenerate it after configuration changes because it is derived from
`langgraph.json`.

Inspect Docker context and ignore rules before building. Do not include `.env`,
credentials, local state, evaluation secrets, or unrelated repository data in
the image. Avoid embedding credentials in Dockerfile lines or build arguments.

## Deployment

`langgraph deploy` builds and deploys directly to LangSmith Deployments. Verify
the workspace, target deployment, deployment type, image architecture, config,
and secret source before running it. Use the installed CLI help for supported
list, log, update, and delete operations.

Wait for the requested terminal status unless the user explicitly wants an
asynchronous deployment. An uploaded image or created revision is not proof
that the deployment became healthy. Inspect build logs for build failures and
runtime logs for startup or request failures.

Deletion and forced replacement are destructive. Do not bypass an interactive
confirmation unless the user has explicitly authorized that exact action.

## Troubleshooting

- Import failure: resolve the graph path from the config directory and confirm
  the exported value or factory exists.
- Missing package: ensure `dependencies` points at the directory containing the
  package manifest; do not point it at the manifest filename.
- Works in `dev`, fails in `up`: inspect system packages, image architecture,
  environment variables, and container-only paths.
- State disappears: confirm which server mode and persistence backend are in
  use and that the request reuses the intended thread.
- Studio cannot connect: distinguish server health, authentication, browser,
  and tunnel problems before changing graph code.
