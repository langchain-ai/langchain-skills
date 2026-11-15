"""Configuration checks do not depend on asynchronous evaluator execution."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import validators
from validators import validate


PROJECT = "77777777-7777-4777-8777-777777777777"


def evidence():
    return {
        "rules": [
            {"rule_id": "dm-rule", "evaluator_id": "dm-eval", "evaluator_type": "llm",
             "decision_model": True, "type_evidence": "playground_settings.decision_model",
             "feedback_keys": ["unsupported_capability"], "filter": "", "trace_filter": ""},
            {"rule_id": "judge-rule", "evaluator_id": "judge-eval", "evaluator_type": "llm",
             "decision_model": False, "type_evidence": "no decision-model marker",
             "feedback_keys": ["unsupported_capability_confirmed", "capability_requested"],
             "filter": 'and(eq(feedback_key, "unsupported_capability"), gte(feedback_score, 0.5))',
             "trace_filter": ""},
        ],
        "insights_configs": [{"id": "config", "project_id": PROJECT, "job_id": "job", "name": "Patterns",
                              "filter": 'and(eq(feedback_key, "unsupported_capability_confirmed"), eq(feedback_score, 1))'}],
        "insights_jobs": [{"id": "job", "project_id": PROJECT, "config_id": None, "name": "Patterns", "status": "pending"}],
    }


class ValidatorTests(unittest.TestCase):
    def test_valid_chain_with_pending_job(self):
        result = validate(evidence(), PROJECT)
        self.assertTrue(all(result[name]["passed"] for name in ("evaluator_pair", "chain_configuration", "insights_job")))

    def test_duplicate_decision_model_fails_pair(self):
        value = evidence()
        value["rules"].append({**value["rules"][0], "rule_id": "another"})
        self.assertFalse(validate(value, PROJECT)["evaluator_pair"]["passed"])

    def test_trace_filter_does_not_count_as_run_filter(self):
        value = evidence()
        value["rules"][1]["trace_filter"] = value["rules"][1]["filter"]
        value["rules"][1]["filter"] = ""
        self.assertFalse(validate(value, PROJECT)["chain_configuration"]["passed"])

    def test_insights_requires_judge_key_and_exact_score_one(self):
        value = evidence()
        value["insights_configs"][0]["filter"] = 'and(eq(feedback_key, "unsupported_capability"), gte(feedback_score, 0.5))'
        self.assertFalse(validate(value, PROJECT)["insights_job"]["passed"])

    def test_insights_requires_persisted_job(self):
        value = evidence()
        value["insights_jobs"] = []
        self.assertFalse(validate(value, PROJECT)["insights_job"]["passed"])

    def test_collector_uses_nested_insights_filter_and_model_marker(self):
        dm_id = "11111111-1111-4111-8111-111111111111"
        judge_id = "22222222-2222-4222-8222-222222222222"
        rules = [
            {"id": "dm-rule", "session_id": PROJECT, "is_enabled": True, "evaluator_id": dm_id,
             "evaluator_type": "llm", "evaluators": [{"structured": {"model": {"kwargs": {"decision_model": True}}}}]},
            {"id": "judge-rule", "session_id": PROJECT, "is_enabled": True, "evaluator_id": judge_id,
             "evaluator_type": "llm", "filter": 'eq(feedback_key, "stage_one")',
             "evaluators": [{"structured": {"model": {"kwargs": {}}}}]},
        ]
        responses = {
            f"/runs/rules?session_id={PROJECT}": rules,
            f"/v1/platform/evaluators/{dm_id}": {"feedback_keys": ["stage_one"], "secret_prompt": "omit"},
            f"/v1/platform/evaluators/{judge_id}": {"feedback_keys": ["confirmed"]},
        }

        class FakeClient:
            def request_with_retries(self, method, path):
                return SimpleNamespace(json=lambda: responses[path])

        configs = [{"id": "config", "name": "Patterns", "online_taxonomy_job_id": "job",
                    "config": {"filter": 'and(eq(feedback_key, "confirmed"), eq(feedback_score, 1))',
                               "summary_prompt": "omit"}}]
        jobs = [{"id": "job", "name": "Patterns", "status": "pending"}]
        with patch.object(validators, "_cli_json", side_effect=[configs, jobs]):
            actual = validators.collect({"target_project_id": PROJECT, "workspace_id": PROJECT}, FakeClient())
        self.assertTrue(all(validate(actual, PROJECT)[name]["passed"] for name in
                            ("evaluator_pair", "chain_configuration", "insights_job")))
        self.assertNotIn("omit", str(actual))


if __name__ == "__main__":
    unittest.main()
