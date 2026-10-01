# Managed Deep Agents operations

## Local lifecycle

| Command | Purpose |
|---|---|
| `mda init <name>` | Scaffold a new project; fails if the destination exists |
| `mda build [path]` | Compile a managed LangGraph build without deployment |
| `mda dev [path]` | Compile and run a local development server |
| `mda deploy [path]` | Build, sync context, deploy, and reconcile schedules |
| `mda logs [path]` | Read or follow deployed Agent Server logs |
| `mda delete [path]` | Delete the deployment and MDA-owned resources |
| `mda evals init|compile` | Scaffold or package Harbor evaluation tasks |

Inspect `mda <command> --help` before relying on flags. The public beta's docs
may describe features that are newer than the installed CLI.

`mda delete` is destructive. Ask for confirmation immediately before running
it and never add `--yes` without explicit authorization.

## Secrets

Authentication keys are resolved from the project `.env` and then the shell,
according to current CLI precedence. Platform keys authenticate and route the
deployment; provider keys, tool credentials, and database URLs may become hosted
secrets when supported.

Keep `.env` gitignored and outside the build archive. Do not write live keys on
the user's behalf or expose them in logs, prompts, skill files, source, or
Context Hub. Verify which variables are reserved and which are uploaded before
deployment.

## Build and deploy flow

```text
instructions.md + skills/**  -> deploy-owned Context Hub content
memory declaration           -> runtime-owned durable memory tree
.env                         -> local auth and hosted-secret inputs; not archived
project source               -> managed build archive and deployment
schedules/**                 -> reconciled schedules after deployment becomes live
```

Context Hub instructions and deployed skills are resynced from the project.
Runtime-owned memory persists across ordinary deployments. Verify conflicts and
ownership before changing content through another interface.

Build locally first. On deployment failure, use the printed revision URL and
logs rather than retrying blindly. A successful upload is not a successful live
deployment; wait for the requested terminal status unless the user explicitly
asked for asynchronous deployment.

## Evals

MDA uses Harbor tasks under `evals/tasks/`; it does not define a separate eval
format. `mda evals compile` packages the agent and produces a Harbor handoff. It
does not itself run trials.

Evaluation files are not deployed. Harbor's default environment requires
Docker and does not automatically load the project `.env`; supply permitted
variables through the evaluation runner. Use `eval-engineering` for task and
verifier design.

## Troubleshooting

- Missing agent entry: add the supported root `agent.py` or `agent.ts` export.
- 401 or 403: verify workspace beta access, caller identity, and resource
  ownership rather than changing application permissions.
- Context conflict: inspect which surface owns the file, then resync deliberately.
- Oversized build: remove generated artifacts and confirm ignore rules.
- Newly added managed file not discovered: restart `mda dev`; declarations are
  found at compile time.
- Schedule changes absent: confirm deployment waited through reconciliation and
  did not use `--no-wait`.
- Tool approval absent: confirm the exposed tool name, including MCP prefixes,
  matches the interrupt policy.

## Version-sensitive gotchas

- Agent names are required and must match current naming rules.
- Set `MODEL` to a supported provider-qualified identifier in the form
  `provider:model-id`; Gateway uses a slash form.
- Do not pass managed backend, store, checkpointer, memory, skills, or system
  prompt fields into the agent definition.
- Memory is enabled by the current declaration file, not legacy constructor
  flags.
- Schedule declarations must remain statically extractable.
- Verify sandbox imports and identity/channel flags against the installed
  release rather than copying documentation for a newer version.
