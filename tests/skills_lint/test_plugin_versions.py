"""Release checks that keep cached marketplace plugins current."""

import subprocess
import unittest
from unittest.mock import patch

from scripts import check_plugin_versions


BASE = "a" * 40


class PluginVersionTests(unittest.TestCase):
    def test_changed_skill_requires_new_version(self) -> None:
        with (
            patch.object(check_plugin_versions, "current_version", return_value="0.1.0"),
            patch.object(
                check_plugin_versions,
                "git",
                side_effect=[
                    subprocess.CompletedProcess([], 0, stdout=b"skills/example/SKILL.md\n"),
                    subprocess.CompletedProcess([], 0, stdout=b'{"version":"0.1.0"}'),
                ],
            ),
        ):
            with self.assertRaisesRegex(ValueError, "did not increase"):
                check_plugin_versions.check(BASE)

    def test_changed_skill_with_new_version_passes(self) -> None:
        with (
            patch.object(check_plugin_versions, "current_version", return_value="0.2.0"),
            patch.object(
                check_plugin_versions,
                "git",
                side_effect=[
                    subprocess.CompletedProcess([], 0, stdout=b"skills/example/SKILL.md\n"),
                    subprocess.CompletedProcess([], 0, stdout=b'{"version":"0.1.0"}'),
                ],
            ),
        ):
            check_plugin_versions.check(BASE)


if __name__ == "__main__":
    unittest.main()
