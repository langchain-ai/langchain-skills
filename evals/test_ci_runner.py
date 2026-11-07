"""Offline checks for the public CI summary."""

from __future__ import annotations

import unittest
from uuid import uuid4

from ci_runner import _summarize_report


class SummaryTests(unittest.TestCase):
    def test_public_summary_keeps_only_aggregate_evidence(self) -> None:
        run_id = str(uuid4())
        report = {
            "profile": "full",
            "run_id": run_id,
            "source_sha": "a" * 40,
            "local": {
                "agent_cost_usd": 1.25,
                "agent_seconds": 60,
                "total_seconds": 80,
                "tool_calls": {"Skill": 2, "Read": 3},
                "skills_invoked": ["private-skill-name"],
                "trial_dir": "private-path",
            },
            "live": {
                "feedback_by_case": [{"feedback": [{"value": "private-feedback-text"}]}],
                "traces": [{"claude_turn_count": 2, "turns_nested_under_agent_start": True}],
            },
            "validators": {
                name: {"passed": True, "evidence": "private-evaluator-prompt"}
                for name in ("evaluator_pair", "chain_configuration", "insights_job")
            },
        }
        summary = _summarize_report(report)
        self.assertEqual(summary["tool_call_count"], 5)
        self.assertEqual(summary["feedback_count"], 1)
        self.assertTrue(summary["trace_parentage_ok"])
        self.assertTrue(all(summary["validators"].values()))
        self.assertNotIn("private", str(summary))

    def test_missing_validators_fail_closed(self) -> None:
        summary = _summarize_report({"profile": "full", "run_id": str(uuid4())})
        self.assertEqual(summary["validators"], {
            "evaluator_pair": False,
            "chain_configuration": False,
            "insights_job": False,
        })
        self.assertFalse(summary["trace_parentage_ok"])

    def test_free_form_metrics_are_not_uploaded(self) -> None:
        summary = _summarize_report({
            "profile": "none",
            "run_id": str(uuid4()),
            "source_sha": "private-source",
            "local": {"agent_cost_usd": "private-cost", "tool_calls": {"x": "private-count"}},
        })
        self.assertIsNone(summary["source_sha"])
        self.assertIsNone(summary["agent_cost_usd"])
        self.assertEqual(summary["tool_call_count"], 0)
        self.assertNotIn("private", str(summary))


if __name__ == "__main__":
    unittest.main()
