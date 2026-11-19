"""Offline alignment checks for the experiment-regression verifier."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from langsmith.utils import LangSmithNotFoundError

import harness
from validators import collect_experiment, validate_experiment

TASK = Path(__file__).resolve().parent / "tasks" / "experiment-regression"
EXPECTED = json.loads((TASK / "expected.json").read_text())
CHECKS = ("dataset", "experiment", "app_unchanged", "failures_localized", "no_false_failures")
SHIPPED = {"warranty-length": True, "damaged-order": True}
REQUIREMENT_RESULTS = {
    "returns-unopened": [1, 1],
    "shipping-time": [1, 1],
    "warranty-length": [0, 1],
    "damaged-order": [1, 0],
    "address-change": [1, 1],
    "cancel-subscription": [1, 1],
}


def run(case_id, scores, unchanged=None, errored=False):
    if unchanged is None and case_id in SHIPPED:
        unchanged = True
    return {"case_id": case_id, "errored": errored, "unchanged": unchanged,
            "scores": [{"key": key, "score": float(score)} for key, score in scores.items()]}


def evidence(*experiments):
    return {
        "dataset_id": str(uuid4()),
        "dataset_name": "lcskills-eval-experiment-regression-full-abcd1234",
        "example_cases": sorted(case["id"] for case in EXPECTED["cases"]),
        "experiments": list(experiments),
        "dataset_rule_ids": [],
    }


def experiment(runs, start="2026-11-19T12:00:00+00:00"):
    return {"id": str(uuid4()), "name": "support-baseline", "start_time": start, "runs": runs}


def assertion_runs():
    """Known-good: per-assertion keys named after the claim plus the two summary scores."""
    names = {
        "returns-unopened": ("mentions_30_day_window", "no_ticket"),
        "shipping-time": ("mentions_3_5_days", "no_ticket"),
        "warranty-length": ("mentions_24_months", "links_warranty_page"),
        "damaged-order": ("asks_for_photo", "opens_ticket"),
        "address-change": ("change_until_shipped", "links_orders_page"),
        "cancel-subscription": ("points_to_account_settings", "no_ticket"),
    }
    runs = []
    for case_id, results in REQUIREMENT_RESULTS.items():
        scores = dict(zip(names[case_id], results))
        scores["all_assertions_passed"] = int(all(results))
        scores["assertion_pass_rate"] = sum(results) / len(results)
        runs.append(run(case_id, scores))
    return runs


def passed(result):
    return {name: result[name]["passed"] for name in CHECKS}


class ExperimentValidatorTests(unittest.TestCase):
    def test_known_good_assertion_experiment_passes(self):
        result = validate_experiment(evidence(experiment(assertion_runs())), EXPECTED)
        self.assertTrue(all(passed(result).values()), result)

    def test_positional_judge_keys_with_repetitions_pass(self):
        runs = [
            run(case_id, {"requirement_1": first, "requirement_2": second})
            for case_id, (first, second) in REQUIREMENT_RESULTS.items()
            for _ in range(3)
        ]
        self.assertTrue(all(passed(validate_experiment(evidence(experiment(runs)), EXPECTED)).values()))

    def test_shape_guessing_evaluator_flags_correct_answers(self):
        runs = [run(case_id, {"requirement_1": 0, "requirement_2": 0}) for case_id in REQUIREMENT_RESULTS]
        result = passed(validate_experiment(evidence(experiment(runs)), EXPECTED))
        self.assertFalse(result["no_false_failures"])
        self.assertFalse(result["failures_localized"])

    def test_references_copied_from_app_output_miss_the_bugs(self):
        runs = [run(case_id, {"matches_reference": 1}) for case_id in REQUIREMENT_RESULTS]
        self.assertFalse(passed(validate_experiment(evidence(experiment(runs)), EXPECTED))["failures_localized"])

    def test_overall_score_with_constant_key_does_not_localize(self):
        runs = [
            run(case_id, {"correct": int(all(results)), "has_answer": 1})
            for case_id, results in REQUIREMENT_RESULTS.items()
        ]
        result = passed(validate_experiment(evidence(experiment(runs)), EXPECTED))
        self.assertTrue(result["no_false_failures"])
        self.assertFalse(result["failures_localized"])

    def test_scale_scores_compare_with_the_best_observed(self):
        runs = [
            run(case_id, {"req_a": 5 if first else 2, "req_b": 5 if second else 1})
            for case_id, (first, second) in REQUIREMENT_RESULTS.items()
        ]
        self.assertTrue(all(passed(validate_experiment(evidence(experiment(runs)), EXPECTED)).values()))

    def test_fixed_app_fails_unchanged_check(self):
        runs = assertion_runs()
        runs[2]["unchanged"] = False
        self.assertFalse(passed(validate_experiment(evidence(experiment(runs)), EXPECTED))["app_unchanged"])

    def test_latest_complete_experiment_is_scored(self):
        broken = experiment([run(case_id, {"x": 0}) for case_id in REQUIREMENT_RESULTS], "2026-11-19T11:00:00+00:00")
        fixed = experiment(assertion_runs(), "2026-11-19T12:00:00+00:00")
        partial = experiment(assertion_runs()[:3], "2026-11-19T13:00:00+00:00")
        result = validate_experiment(evidence(broken, fixed, partial), EXPECTED)
        self.assertEqual(result["experiment"]["selected"], fixed["id"])
        self.assertTrue(all(passed(result).values()))

    def test_errored_or_unscored_runs_are_incomplete(self):
        errored = assertion_runs()
        errored[0]["errored"] = True
        unscored = assertion_runs()
        unscored[1]["scores"] = []
        for runs in (errored, unscored):
            self.assertFalse(passed(validate_experiment(evidence(experiment(runs)), EXPECTED))["experiment"])

    def test_dataset_must_hold_each_case_once(self):
        value = evidence(experiment(assertion_runs()))
        value["example_cases"] = value["example_cases"][:-1] + ["unmapped"]
        self.assertFalse(validate_experiment(value, EXPECTED)["dataset"]["passed"])
        value["dataset_id"] = None
        self.assertFalse(validate_experiment(value, EXPECTED)["dataset"]["passed"])


QUESTIONS = {
    "returns-unopened": "I bought a jacket two weeks ago and never opened it. Can I still return it?",
    "shipping-time": "How long does standard shipping take?",
    "warranty-length": "How long is the warranty on my headphones?",
    "damaged-order": "My order arrived damaged. What should I do?",
    "address-change": "Can I change my delivery address after placing an order?",
    "cancel-subscription": "How do I cancel my subscription?",
}
ANSWERS = {
    "warranty-length": {"messages": [{"type": "ai", "content": "Electronics carry a 12-month limited warranty."}]},
    "damaged-order": {"messages": [{"type": "ai", "content": "Please reply with a photo."}]},
}


class FakeExperimentClient:
    def __init__(self, missing=False):
        self.missing = missing
        self.dataset = SimpleNamespace(id=uuid4(), name="lcskills-eval-experiment-regression-full-abcd1234")
        self.examples = [SimpleNamespace(id=uuid4(), inputs={"question": q}) for q in QUESTIONS.values()]
        self.project = SimpleNamespace(id=uuid4(), name="baseline", start_time=datetime.now(timezone.utc))
        self.runs = [
            SimpleNamespace(id=uuid4(), reference_example_id=example.id, error=None,
                            outputs=ANSWERS.get(case_id, {"messages": [{"content": "secret answer text"}]}))
            for case_id, example in zip(QUESTIONS, self.examples)
        ]
        self.rule_id = str(uuid4())

    def read_dataset(self, dataset_name):
        if self.missing:
            raise LangSmithNotFoundError("missing")
        return self.dataset

    def list_examples(self, dataset_id):
        return self.examples

    def list_projects(self, reference_dataset_id):
        return [self.project]

    def list_runs(self, project_id, is_root):
        return self.runs

    def list_feedback(self, run_ids):
        return [SimpleNamespace(run_id=run_id, key="ok", score=True, comment="secret comment") for run_id in run_ids]

    def request_with_retries(self, method, path):
        body = [{"id": self.rule_id, "dataset_id": str(self.dataset.id)}, {"id": "other", "dataset_id": "x"}]
        return SimpleNamespace(json=lambda: body)


class CollectExperimentTests(unittest.TestCase):
    def test_collects_cases_and_scores_without_text(self):
        ls = FakeExperimentClient()
        actual = collect_experiment({"target_dataset_name": ls.dataset.name}, ls, EXPECTED)
        self.assertEqual(actual["example_cases"], sorted(QUESTIONS))
        runs = actual["experiments"][0]["runs"]
        self.assertEqual({r["case_id"] for r in runs}, set(QUESTIONS))
        self.assertTrue(all(r["unchanged"] for r in runs if r["case_id"] in SHIPPED))
        self.assertEqual(actual["dataset_rule_ids"], [ls.rule_id])
        self.assertNotIn("secret", json.dumps(actual))

    def test_missing_dataset_is_recorded(self):
        actual = collect_experiment({"target_dataset_name": "absent"}, FakeExperimentClient(missing=True), EXPECTED)
        self.assertIsNone(actual["dataset_id"])
        self.assertFalse(validate_experiment(actual, EXPECTED)["experiment"]["passed"])


class TaskSettingsTests(unittest.TestCase):
    def test_dataset_name_reaches_the_agent(self):
        settings = harness.task_settings(TASK)
        data = {"target_project_id": "p", "target_dataset_name": "lcskills-eval-x"}
        self.assertEqual(harness.target_env(data, settings)["TARGET_DATASET_NAME"], "lcskills-eval-x")
        harness.validate_task(TASK)

    def test_expected_values_stay_outside_the_environment(self):
        self.assertFalse((TASK / "environment" / "expected.json").exists())
        cases = (TASK / "environment" / "app" / "cases.md").read_text().lower()
        self.assertTrue(all(case["question"] in cases for case in EXPECTED["cases"]))


if __name__ == "__main__":
    unittest.main()
