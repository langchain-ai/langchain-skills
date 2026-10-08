# LangGraph CLI configuration

Treat the installed CLI schema as the contract. The current schema supports
more than graph paths, and fields are version-sensitive.

## Required sections

- `dependencies`: package names or directories containing the project manifest.
  `"."` uses the current package. Do not name `requirements.txt` or
  `pyproject.toml` directly.
- `graphs`: stable assistant IDs mapped to compiled graph exports or supported
  graph factory functions.

Keep graph IDs stable after clients depend on them. Confirm that a factory's
accepted arguments and return type match the installed Agent Server contract.

## Common optional sections

- `env`: local environment file path or mapping.
- `python_version` / `node_version`: deployment runtime.
- `auth`: authentication handler and Studio or LangSmith-key behavior.
- `store`: semantic indexing and retention for the runtime store.
- `checkpointer`: backend, TTL, and serialization settings.
- `http`: custom app, CORS, request headers, logging, middleware order, route
  authentication, and endpoint controls.
- `ui`: named frontend components emitted by the agent.
- `base_image`, `image_distro`, `dockerfile_lines`: container customization.
- Python packaging options such as `pip_config_file` and the supported
  installer selection.

Read the exact current schema before adding an advanced section. Keep changes
focused on the requested capability rather than copying a full sample config.

## Security boundaries

Authentication proves caller identity; authorization handlers must still
scope access to threads, assistants, runs, store namespaces, and custom routes.
If custom routes should be protected, enable their supported auth integration
and test an unauthorized request.

Restrict CORS origins, methods, headers, and credentials to the frontend that
needs them. Exclude credentials and sensitive request headers from logs. If the
server exposes selected headers to graph configuration, use a narrow allowlist.

Use supported serialization defaults. Do not enable permissive pickle fallback
or broad module allowlists for data an attacker can influence. Keep store and
checkpoint TTLs aligned with retention requirements and verify that expiration
does not silently break durable workflows.

Treat `dockerfile_lines`, custom package indexes, graph imports, custom apps,
and auth handlers as executable build or server code. Review their sources and
never interpolate untrusted values into them.
