"""Regression tests for the skill linter, including the pinned Claude CLI."""

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("lint_skills", ROOT / "scripts/lint_skills.py")
lint = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = lint
SPEC.loader.exec_module(lint)


class LintTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skills = self.root / "config/skills"
        self.skill = self.skills / "example/SKILL.md"
        self.skill.parent.mkdir(parents=True)
        self.write_skill("example")

    def write_skill(self, name):
        self.skill.write_text(
            f"---\nname: {name}\ndescription: An example skill.\n---\nBody.\n",
            encoding="utf-8",
        )

    def result(self, *, success=True, returncode=0, contents=None, manifest=None):
        return subprocess.CompletedProcess(
            [], returncode,
            json.dumps({"success": success, "contents": contents or [], "manifest": manifest}),
            "",
        )

    def validate_result(self, result):
        with patch.object(lint, "run_claude", return_value=result):
            return lint.check_plugin_validate(self.root, self.skills)

    def assert_blocked(self, findings):
        self.assertTrue(findings)
        self.assertTrue(all(f.severity == lint.BLOCK and f.rule == "validate" for f in findings))


class ValidatorTests(LintTestCase):
    def test_clean_report_passes(self):
        self.assertEqual(self.validate_result(self.result()), [])

    def test_unavailable_cli_blocks(self):
        self.assert_blocked(self.validate_result(None))

    def test_process_launch_failure_blocks(self):
        with patch.object(lint, "run_claude", side_effect=OSError("cannot execute")):
            self.assert_blocked(lint.check_plugin_validate(self.root, self.skills))

    def test_unreadable_report_blocks(self):
        for stdout in ("", "not json"):
            with self.subTest(stdout=stdout):
                self.assert_blocked(self.validate_result(subprocess.CompletedProcess([], 2, stdout, "crashed")))

    def test_invalid_report_structure_blocks(self):
        for report in (None, [], {}, {"success": True, "contents": {}},
                       {"success": True, "contents": [None]},
                       {"success": True, "contents": [], "manifest": []},
                       {"success": True, "contents": [{"errors": ["invalid"]}]}):
            with self.subTest(report=report):
                self.assert_blocked(self.validate_result(subprocess.CompletedProcess([], 0, json.dumps(report), "")))

    def test_unsuccessful_status_or_exit_blocks_without_diagnostics(self):
        for success, code in ((False, 1), (False, 0), (True, 2)):
            with self.subTest(success=success, code=code):
                self.assert_blocked(self.validate_result(self.result(success=success, returncode=code)))

    def test_manifest_errors_and_strict_warnings_block(self):
        for category in ("errors", "warnings"):
            with self.subTest(category=category):
                findings = self.validate_result(self.result(
                    success=False, returncode=1,
                    manifest={"file": ".claude-plugin/plugin.json", category: [{"path": "name", "message": "bad manifest"}]},
                ))
                self.assert_blocked(findings)
                self.assertIn("bad manifest", findings[0].message)
                self.assertEqual(findings[0].path, self.root / ".claude-plugin/plugin.json")

    def test_content_errors_and_strict_warnings_block(self):
        for category in ("errors", "warnings"):
            with self.subTest(category=category):
                findings = self.validate_result(self.result(contents=[{
                    "file": str(self.skill), category: [{"path": "description", "message": "missing description"}],
                }]))
                self.assert_blocked(findings)
                self.assertEqual(findings[0].path, self.skill)

    def test_main_exits_nonzero_when_validator_crashes(self):
        # A clean content tree must not mask a validator infrastructure failure.
        result = subprocess.CompletedProcess([], 2, "", "validator crashed")
        with patch.object(lint, "__file__", str(self.root / "scripts/lint_skills.py")), \
             patch.object(lint, "run_claude", return_value=result), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lint.main(), 1)


class FrontmatterTests(LintTestCase):
    def test_comments_after_plain_and_quoted_names(self):
        for name in ("example # comment", "example\t# comment", "'example' # comment", '"example" # comment'):
            with self.subTest(name=name):
                self.write_skill(name)
                self.assertEqual(lint.check_skill(self.root, self.skill), [])

    def test_hash_inside_quotes_is_not_a_comment(self):
        for name in ("'example # literal' # comment", '"example # literal" # comment'):
            with self.subTest(name=name):
                self.write_skill(name)
                self.assertEqual(lint.parse_frontmatter(self.skill.read_text())["name"], "example # literal")
                self.assertEqual([f.rule for f in lint.check_skill(self.root, self.skill)], ["name"])

    def test_comment_does_not_hide_real_mismatch(self):
        for name in ("wrong # comment", "'wrong' # comment", '"wrong" # comment'):
            with self.subTest(name=name):
                self.write_skill(name)
                self.assertEqual([f.rule for f in lint.check_skill(self.root, self.skill)], ["name"])

    def test_escaped_quotes_and_unicode(self):
        self.assertEqual(lint.parse_frontmatter("---\nname: 'it''s' # comment\n---\n")["name"], "it's")
        self.assertEqual(lint.parse_frontmatter('---\nname: "exampl\\u0065" # comment\n---\n')["name"], "example")

    def test_unclosed_frontmatter_is_not_read_as_fields(self):
        self.assertEqual(lint.parse_frontmatter("---\nname: example\n"), {})


@unittest.skipUnless(shutil.which("claude"), "Claude CLI integration requires the CI-pinned CLI")
class ClaudeIntegrationTests(LintTestCase):
    def test_valid_comments_pass_both_validators(self):
        for name in ("example # comment", "'example' # comment", '"example" # comment'):
            with self.subTest(name=name):
                self.write_skill(name)
                self.assertEqual(lint.check_plugin_validate(self.root, self.skills), [])
                self.assertEqual(lint.check_skill(self.root, self.skill), [])

    def test_missing_description_blocks(self):
        self.skill.write_text("---\nname: example\n---\nMissing description.\n", encoding="utf-8")
        findings = lint.check_plugin_validate(self.root, self.skills)
        self.assert_blocked(findings)
        self.assertTrue(any("description" in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
