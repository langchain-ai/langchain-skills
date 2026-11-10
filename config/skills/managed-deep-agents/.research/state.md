# Research state

- **Outcome:** Updated `SKILL.md` to replace the obsolete Slack-only channel claim with current provider guidance: Slack is supported; GitHub and Linear are experimental. Added current channel scaffolding/setup guidance and documented the supported `routes` filesystem-backend option on `define_deep_agent` / `defineDeepAgent`.
- **Content changed:** `SKILL.md` (capability map, limits, agent-definition fields, channels, CLI reference).
- **Processed sources:**
  - https://github.com/langchain-ai/managed-deepagents-sdk/blob/main/packages/pypi/README.md#github-channels
  - https://github.com/langchain-ai/managed-deepagents-sdk/blob/main/packages/pypi/README.md#linear-channels
  - https://github.com/langchain-ai/managed-deepagents-sdk/blob/main/packages/pypi/src/managed_deepagents/define_deep_agent.py
  - https://github.com/langchain-ai/managed-deepagents-sdk/blob/main/crates/mda/src/channel/mod.rs
- **Unresolved:** No published documentation page for the `routes` API was found in this snapshot; the SDK's public function signature and docstring were used.
