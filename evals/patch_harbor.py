"""Apply local fixes to the installed Harbor package.

Harbor is pinned to 0.18.0 (see LANGSMITH_SANDBOX_PLAN.md). A few fixes needed for
our runs are not yet in a Harbor release, so this script patches the installed
package in place. It is idempotent and safe to re-run.

  Fix #1: size the snapshot builder from the task's cpu/memory config (the default
          builder is too small to build large images).
  Fix #3: boot the run sandbox by snapshot id (dockerfile-built snapshots are
          stored untagged, so name lookup 404s). Already fixed on upstream main.
  Fix #4: wire a custom OpenAI base URL (the LangSmith LLM Gateway) as a named
          codex provider with supports_websockets=false, so codex uses the HTTP
          Responses transport instead of the WebSocket one the gateway does not
          allow-list (501).
  Fix #5: forward ANTHROPIC_BASE_URL / OPENAI_BASE_URL into the langgraph
          (deepagents) container so the graph's LLM calls route through the
          gateway instead of calling the provider directly (401).
  Fix #6: bridge the harbor-langsmith plugin's per-trial parent-run handle into
          the langgraph container so the deepagents graph's trace nests under the
          experiment run (each example's granular per-step trajectory is visible
          in the experiment view). The plugin only publishes the handle to an
          in-process registry keyed by context_id; nothing reached the subprocess
          adapter's env, so the trace was absent. Only the langgraph agent is
          bridged — claude-code and codex would each need their own mechanism.
  Fix #7: nest the claude-code granular trace under the experiment run. Claude
          Code does not auto-trace, so this delivers the LangSmith tracing plugin
          into the container (upload_dir + --plugin-dir), forces the plugin's
          master switch on, and bridges the per-trial parent handle as
          CC_LANGSMITH_PARENT_DOTTED_ORDER. Gated on parent-handle presence, so
          only --langsmith-experiment trials trace; the plugin host path arrives
          via CC_LANGSMITH_PLUGIN_DIR (set by scripts/sweep.py).

  codex tracing was attempted (fix#8/#8b) but abandoned: the first-party plugin
  (langchain-ai/langsmith-codex-plugins) never emitted a trace under Harbor's
  headless `codex exec`, even with gpt-5.3-codex and --dangerously-bypass-hook-trust.
  Accepted as a known limitation — codex runs are not traced to LangSmith.

Run after installing/upgrading Harbor:

    uv tool install 'harbor[langsmith]' --python 3.13
    uv run python scripts/patch_harbor.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

EXPECTED_VERSION = "0.18.0"

# Each patch: (relative-file, name, marker-if-already-applied, original, replacement).
PATCHES: list[tuple[str, str, str, str, str]] = [
    (
        "environments/langsmith.py",
        "fix#1 builder cpu/memory",
        "vcpus=self._effective_cpus,",
        """                on_build_log=self._log_dockerfile_build_line,
                timeout=max(1, int(self.task_env_config.build_timeout_sec)),
                headers=self._langsmith_client_headers(),
            )""",
        """                on_build_log=self._log_dockerfile_build_line,
                timeout=max(1, int(self.task_env_config.build_timeout_sec)),
                # Size the builder from the task's cpu/memory config; the default
                # builder is too small for large images (matches run-sandbox sizing).
                vcpus=self._effective_cpus,
                mem_bytes=(
                    self._effective_memory_mb * _ONE_MIB
                    if self._effective_memory_mb is not None
                    else None
                ),
                headers=self._langsmith_client_headers(),
            )""",
    ),
    (
        "environments/langsmith.py",
        "fix#3a snapshot_id in payload",
        'payload["snapshot_id"] = self._active_snapshot_id',
        """        if snapshot_name:
            payload["snapshot_name"] = snapshot_name
        if (cpus := self._effective_cpus) is not None:""",
        """        # Boot by snapshot id: dockerfile-built snapshots are stored untagged,
        # but create_sandbox resolves a bare name to "<name>:latest" and 404s.
        # (Backport of the upstream-main fix to the 0.18.0 release.)
        if self._active_snapshot_id:
            payload["snapshot_id"] = self._active_snapshot_id
        elif snapshot_name:
            payload["snapshot_name"] = snapshot_name
        if (cpus := self._effective_cpus) is not None:""",
    ),
    (
        "environments/langsmith.py",
        "fix#3b snapshot_id in create_sandbox",
        'snapshot_id=payload.get("snapshot_id"),',
        """            return client.create_sandbox(
                snapshot_name=payload.get("snapshot_name"),
                name=payload["name"],""",
        """            return client.create_sandbox(
                snapshot_id=payload.get("snapshot_id"),
                snapshot_name=payload.get("snapshot_name"),
                name=payload["name"],""",
    ),
    (
        "agents/installed/codex.py",
        "fix#4 codex gateway provider (no websockets)",
        "supports_websockets",
        """        # codex 0.118.0 only honors openai_base_url from config.toml, not the env var.
        config_toml_block = ""
        if openai_base_url:
            config_toml_block = (
                '\\ncat >>"$CODEX_HOME/config.toml" <<TOML\\n'
                'openai_base_url = "${OPENAI_BASE_URL}"\\n'
                "TOML"
            )""",
        """        # A custom base URL (e.g. the LangSmith LLM Gateway) is configured as a
        # named provider so we can also set supports_websockets=false: codex
        # defaults to the Responses API WebSocket transport, which the gateway
        # does not allow-list (501), so we pin it to HTTP/SSE. codex only honors
        # provider config from config.toml, not env vars.
        config_toml_block = ""
        if openai_base_url:
            config_toml_block = (
                '\\ncat >>"$CODEX_HOME/config.toml" <<TOML\\n'
                'model_provider = "gateway"\\n'
                "[model_providers.gateway]\\n"
                'name = "Gateway"\\n'
                'base_url = "${OPENAI_BASE_URL}"\\n'
                'env_key = "OPENAI_API_KEY"\\n'
                'wire_api = "responses"\\n'
                'supports_websockets = false\\n'
                "TOML"
            )""",
    ),
    (
        "agents/installed/langgraph.py",
        "fix#5 langgraph forward base URLs",
        "ANTHROPIC_BASE_URL",
        """_FORWARDED_ENV_VARS = (
    # Model provider keys
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",""",
        """_FORWARDED_ENV_VARS = (
    # Model provider base URLs (e.g. the LangSmith LLM Gateway)
    "ANTHROPIC_BASE_URL",
    "OPENAI_BASE_URL",
    # Model provider keys
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",""",
    ),
    (
        "agents/installed/langgraph.py",
        "fix#6 langgraph nest trace under experiment run",
        "from harbor_langsmith import nesting",
        """        for var in _FORWARDED_ENV_VARS:
            value = os.environ.get(var)
            if value is not None and var not in env:
                env[var] = value""",
        """        for var in _FORWARDED_ENV_VARS:
            value = os.environ.get(var)
            if value is not None and var not in env:
                env[var] = value

        # Bridge the harbor-langsmith plugin's per-trial parent-run handle into the
        # container env so the graph's trace nests under the experiment run. The
        # plugin publishes it to an in-process registry keyed by context_id (== the
        # trial id); os.environ carries no per-trial handle for subprocess adapters.
        try:
            from harbor_langsmith import nesting

            env.update(nesting.get(self.context_id))
        except ImportError:
            pass""",
    ),
    (
        "agents/installed/claude_code.py",
        "fix#7 claude-code deliver plugin + nest trace under experiment run",
        "cc-langsmith-plugin",
        """        env["CLAUDE_CONFIG_DIR"] = (EnvironmentPaths.agent_dir / "sessions").as_posix()""",
        """        env["CLAUDE_CONFIG_DIR"] = (EnvironmentPaths.agent_dir / "sessions").as_posix()

        # fix#7: nest the claude-code granular trace under the experiment run. The
        # harbor-langsmith plugin publishes a per-trial parent handle only for
        # experiment trials; its presence is the signal to enable + nest CC tracing.
        trace_plugin_flag = ""
        parent_dotted_order = None
        experiment_project = None
        try:
            from harbor_langsmith import nesting

            contributed = nesting.get(self.context_id)
            parent_dotted_order = contributed.get("HARBOR_LANGSMITH_PARENT")
            experiment_project = contributed.get("LANGSMITH_PROJECT")
        except ImportError:
            pass

        plugin_src = os.environ.get("CC_LANGSMITH_PLUGIN_DIR")
        if parent_dotted_order and plugin_src and os.path.isdir(plugin_src):
            remote_plugin_dir = "/installed-agent/cc-langsmith-plugin"
            await environment.upload_dir(plugin_src, remote_plugin_dir)
            trace_plugin_flag = f"--plugin-dir {remote_plugin_dir} "

            # Force the plugin's master switch on for exactly the trials we trace,
            # so the outcome does not depend on ambient TRACE_TO_LANGSMITH state.
            env["TRACE_TO_LANGSMITH"] = "true"
            env["CC_LANGSMITH_PARENT_DOTTED_ORDER"] = parent_dotted_order
            for _var in (
                "CC_LANGSMITH_API_KEY",
                "CC_LANGSMITH_PROJECT",
                "CC_LANGSMITH_DEBUG",
                "CC_LANGSMITH_METADATA",
                "LANGSMITH_API_KEY",
            ):
                _val = os.environ.get(_var)
                if _val:
                    env[_var] = _val
            if experiment_project:
                # Parentage alone is not enough: LangSmith's experiment UI only
                # renders descendants stored in the experiment's own project.
                # The per-trial value must win over any ambient host default.
                env["CC_LANGSMITH_PROJECT"] = experiment_project
            # Route the plugin debug log somewhere Harbor collects, so the first
            # verification can confirm hooks fired.
            if env.get("CC_LANGSMITH_DEBUG", "").lower() == "true" and not os.environ.get(
                "CC_LANGSMITH_LOG_FILE"
            ):
                env["CC_LANGSMITH_LOG_FILE"] = "/logs/agent/cc-langsmith-debug.log\"""",
    ),
    (
        "agents/installed/claude_code.py",
        "fix#8 claude-code capture experiment project for trace routing",
        'experiment_project = contributed.get("LANGSMITH_PROJECT")',
        """        parent_dotted_order = None
        try:
            from harbor_langsmith import nesting

            parent_dotted_order = nesting.get(self.context_id).get(
                "HARBOR_LANGSMITH_PARENT"
            )
        except ImportError:
            pass""",
        """        parent_dotted_order = None
        experiment_project = None
        try:
            from harbor_langsmith import nesting

            contributed = nesting.get(self.context_id)
            parent_dotted_order = contributed.get("HARBOR_LANGSMITH_PARENT")
            experiment_project = contributed.get("LANGSMITH_PROJECT")
        except ImportError:
            pass""",
    ),
    (
        "agents/installed/claude_code.py",
        "fix#8 claude-code route trace to experiment project",
        "per-trial value must win over any ambient host default",
        """                _val = os.environ.get(_var)
                if _val:
                    env[_var] = _val
            # Route the plugin debug log somewhere Harbor collects""",
        """                _val = os.environ.get(_var)
                if _val:
                    env[_var] = _val
            if experiment_project:
                # Parentage alone is not enough: LangSmith's experiment UI only
                # renders descendants stored in the experiment's own project.
                # The per-trial value must win over any ambient host default.
                env["CC_LANGSMITH_PROJECT"] = experiment_project
            # Route the plugin debug log somewhere Harbor collects""",
    ),
    (
        "agents/installed/claude_code.py",
        "fix#7 claude-code inject --plugin-dir into claude command",
        "{trace_plugin_flag}{extra_flags}",
        """                f"claude --verbose --output-format=stream-json "
                f"{extra_flags}"
                f"--print -- {escaped_instruction} 2>&1 </dev/null | tee \"""",
        """                f"claude --verbose --output-format=stream-json "
                f"{trace_plugin_flag}{extra_flags}"
                f"--print -- {escaped_instruction} 2>&1 </dev/null | tee \"""",
    ),
]


def _locate_harbor() -> tuple[Path, str]:
    exe = shutil.which("harbor")
    if not exe:
        sys.exit("harbor executable not found on PATH. Install it first.")
    interp = sys.executable
    try:
        first = Path(exe).read_text().splitlines()[0]
        if first.startswith("#!"):
            interp = first[2:].strip()
    except (UnicodeDecodeError, OSError):
        pass
    probe = (
        "import harbor, os, importlib.metadata as m; "
        "print(os.path.dirname(harbor.__file__)); print(m.version('harbor'))"
    )
    out = subprocess.run([interp, "-c", probe], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"Could not import harbor via {interp}:\n{out.stderr.strip()}")
    pkg_dir, version = out.stdout.split()
    return Path(pkg_dir), version


def main() -> None:
    pkg_dir, version = _locate_harbor()
    if version != EXPECTED_VERSION:
        sys.exit(
            f"Harbor {version} installed, but these patches target {EXPECTED_VERSION}. "
            f"Pin it: uv tool install 'harbor[langsmith]=={EXPECTED_VERSION}' --python 3.13"
        )

    rel_files = sorted({rel for rel, *_ in PATCHES})
    any_written = False
    for rel in rel_files:
        target = pkg_dir / rel
        text = target.read_text()
        original = text
        for _rel, name, marker, old, new in PATCHES:
            if _rel != rel:
                continue
            if marker in text:
                print(f"  skip  {name} (already applied)")
            elif old in text:
                text = text.replace(old, new, 1)
                print(f"  apply {name}")
            else:
                sys.exit(
                    f"  ERROR {name}: anchor not found in {target}. "
                    "The file may have changed; update scripts/patch_harbor.py."
                )
        if text != original:
            target.write_text(text)
            print(f"Patched {target}")
            any_written = True

    if not any_written:
        print("Nothing to do; all patches already present.")


if __name__ == "__main__":
    main()
