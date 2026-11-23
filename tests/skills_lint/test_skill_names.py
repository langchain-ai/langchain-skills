"""Published skill names must keep installing after renames and removals."""

import unittest
from unittest.mock import patch

from scripts import check_skill_names


BASE = "a" * 40


class SkillNameTests(unittest.TestCase):
    def check(self, before: set[str], after: set[str]) -> None:
        with (
            patch.object(check_skill_names, "base_names", return_value=before),
            patch.object(check_skill_names, "head_names", return_value=after),
        ):
            check_skill_names.check(BASE)

    def test_deleted_skill_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "old-skill"):
            self.check({"old-skill", "kept"}, {"kept"})

    def test_skill_moved_to_legacy_stub_passes(self) -> None:
        self.check({"old-skill"}, {"old-skill", "new-skill"})

    def test_reads_skills_and_legacy_stubs(self) -> None:
        self.assertEqual(
            check_skill_names.skill_names(
                [
                    "skills/active/SKILL.md",
                    "skills/.legacy/retired/SKILL.md",
                    "skills/active/references/notes.md",
                    "skills/README.md",
                ]
            ),
            {"active", "retired"},
        )


if __name__ == "__main__":
    unittest.main()
