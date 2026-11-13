"""Harbor LangSmith plugin variant that writes every trial to one experiment project.

Version-bound to harbor-langsmith 0.2.0. The stock plugin creates a new session
for every job, which prevents a single searchable project and cross-job trace
nesting. This subclass reuses a dataset-linked project while preserving the
stock lifecycle, feedback, usage, and parent-handle logic.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, override

from harbor_langsmith.plugin import LangSmithPlugin


class SharedProjectPlugin(LangSmithPlugin):
    @override
    def _setup(self, job: Any) -> None:
        project_id = os.environ.get("EVAL_TRACE_PROJECT_ID")
        if not project_id:
            raise RuntimeError("EVAL_TRACE_PROJECT_ID is required")
        if not self.api_key:
            raise RuntimeError("LANGSMITH_API_KEY is required")

        endpoint = (self.endpoint or "https://api.smith.langchain.com").rstrip("/")
        self._base_url = endpoint if endpoint.endswith("/api/v1") else f"{endpoint}/api/v1"
        self._session.headers.update({"x-api-key": self.api_key})
        if self.workspace_id:
            self._session.headers.update({"X-Tenant-Id": self.workspace_id})

        if not self.sync_dataset:
            raise RuntimeError("shared project requires dataset sync")
        self._dataset_id = self._get_or_create_dataset(job)
        self._example_ids = self._get_or_create_examples(job)
        response = self._request("GET", f"/sessions/{project_id}", ok_statuses={200})
        project = response.json()
        if str(project.get("reference_dataset_id")) != str(self._dataset_id):
            raise RuntimeError(
                "shared trace project must reference the harness dataset; "
                "choose a dataset-linked experiment project"
            )
        name = project.get("name")
        if not isinstance(name, str) or not name:
            raise RuntimeError("shared trace project has no name")
        self._experiment_id = project_id
        self._experiment_session_name = name

    @override
    async def on_job_end(self, job_result: Any) -> None:
        # The shared project remains active for future tasks and profiles.
        return None

    @override
    def _create_root_run(self, event: Any) -> None:
        super()._create_root_run(event)
        path = os.environ.get("EVAL_ROOT_RUNS_FILE")
        run_id = self._run_ids.get(event.config.trial_name)
        if path and run_id:
            with Path(path).open("a") as stream:
                stream.write(json.dumps({"trial_name": event.config.trial_name, "run_id": run_id}) + "\n")

    @override
    def _trial_metadata(self, event: Any) -> dict[str, Any]:
        metadata = super()._trial_metadata(event)
        for env_name, key in (
            ("EVAL_RUN_ID", "eval_run_id"),
            ("EVAL_TASK", "eval_task"),
            ("EVAL_PROFILE", "eval_profile"),
            ("EVAL_SKILL_SHA", "eval_skill_sha"),
        ):
            value = os.environ.get(env_name)
            if value:
                metadata[key] = value
        return metadata
