"""Tests for scripts/check_cli_commands.py against a fake `langsmith` binary."""

import importlib.util
import os
import stat
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "check_cli_commands", ROOT / "scripts/check_cli_commands.py"
)
check_cli = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check_cli
SPEC.loader.exec_module(check_cli)

GLOBAL_FLAGS = """
Global Flags:
      --format string      Output format: pretty or json (default "pretty")
      --workspace string   LangSmith workspace ID
"""

# Help text keyed by the command path, in cobra's layout.
HELP = {
    "": """Usage:
  langsmith [command]

Available Commands:
  agents      Manage agents
  api         Make authenticated requests
  traces      Query traces

Flags:
      --format string   Output format
  -h, --help        help for langsmith
  -v, --version     version for langsmith
""",
    "traces": """Usage:
  langsmith traces [command]

Aliases:
  traces, trace

Available Commands:
  list        List traces (wrapped description that continues
on an unindented line)
"""
    + GLOBAL_FLAGS,
    "traces list": """Usage:
  langsmith traces list [flags]

Flags:
      --full             Include everything
  -n, --limit int        Maximum number of results
      --project string   Project name
"""
    + GLOBAL_FLAGS,
    "api": """Usage:
  langsmith api [flags]
  langsmith api [command]

Available Commands:
  ls          List endpoints

Flags:
  -X, --method string   HTTP method (default "GET")
"""
    + GLOBAL_FLAGS,
}

# Commands generated from the API spec print urfave/cli help.
URFAVE_GLOBAL = """
GLOBAL OPTIONS:
   --format string           The format for displaying response data (default: "auto")
   --raw-output, -r          If the result is a string, print it without JSON quotes.
"""
HELP["agents"] = """NAME:
   langsmith agents

USAGE:
   langsmith agents [command [command options]]

COMMANDS:
   list      Lists Agents. Results are sorted by last run time; a wrapped
             description continues here
   retrieve  Returns an Agent
""" + URFAVE_GLOBAL
HELP["agents list"] = """NAME:
   langsmith agents list - Lists Agents

USAGE:
   langsmith agents list [options]

OPTIONS:
   --id string [ --id string ]  Exact Agent ids (repeat the parameter)
   --name string                Case-insensitive partial Agent name
   --help, -h                   show help
""" + URFAVE_GLOBAL
HELP["trace"] = HELP["traces"]

FAKE_BIN = """#!{python}
import json, sys
help_ = json.loads({help!r})
args = [a for a in sys.argv[1:] if a != "--help"]
if args == ["--version"]:
    print("langsmith version 0.0.0-test")
    sys.exit(0)
key = " ".join(args)
if key not in help_:
    print("Error: unknown command", file=sys.stderr)
    sys.exit(1)
print(help_[key])
"""


class CheckCliCommandsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import json

        cls.temp = tempfile.TemporaryDirectory()
        fake = Path(cls.temp.name) / "langsmith"
        fake.write_text(FAKE_BIN.format(python=sys.executable, help=json.dumps(HELP)))
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        cls.old_bin = check_cli.BIN
        check_cli.BIN = str(fake)
        check_cli.get_help.cache_clear()

    @classmethod
    def tearDownClass(cls):
        check_cli.BIN = cls.old_bin
        check_cli.get_help.cache_clear()
        cls.temp.cleanup()

    def errors(self, line):
        argv = check_cli.invocations(line)[0]
        return check_cli.check(check_cli.Command(Path("x.md"), 1, argv))

    def test_extracts_shell_fences_and_inline_code(self):
        doc = textwrap.dedent(
            """\
            Run `langsmith traces list --limit 5` or `langsmith <command> --help`.

            ```bash
            # langsmith traces list --ignored
            langsmith traces list \\
              --project my-app | jq . > out.json
            ids=$(langsmith traces list --format json) && echo done
            ```

            ```python
            langsmith traces list --not-shell
            ```
            """
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(doc)
        self.addCleanup(os.unlink, f.name)
        found = [(c.line, c.argv) for c in check_cli.extract(Path(f.name))]
        self.assertEqual(
            found,
            [
                (1, ["langsmith", "traces", "list", "--limit", "5"]),
                (5, ["langsmith", "traces", "list", "--project", "my-app"]),
                (7, ["langsmith", "traces", "list", "--format", "json"]),
            ],
        )

    def test_valid_command_passes(self):
        self.assertEqual(
            self.errors("langsmith --format json traces list -n 5 --full --project 'my app'"),
            [],
        )

    def test_runnable_group_accepts_positionals(self):
        self.assertEqual(self.errors("langsmith api /api/v2/runs/query -X POST"), [])

    def test_unknown_flag_fails(self):
        self.assertEqual(
            self.errors("langsmith traces list --session-id abc"),
            ["unknown or hidden flag --session-id for `langsmith traces list`"],
        )

    def test_allowed_hidden_flag_passes(self):
        self.assertEqual(self.errors('langsmith traces list --api-key "$KEY"'), [])

    def test_alias_fails_with_listed_name(self):
        self.assertEqual(
            self.errors("langsmith trace list --limit 5"),
            ["`langsmith trace` uses an alias; use `traces`"],
        )

    def test_unknown_command_fails(self):
        self.assertEqual(
            self.errors("langsmith traces query"),
            ["unknown command `langsmith traces query`"],
        )

    def test_generated_command_help_is_read(self):
        self.assertEqual(
            self.errors(
                "langsmith agents list --name support --id a --id b -r --format json"
            ),
            [],
        )

    def test_generated_command_accepts_global_auth_flags(self):
        self.assertEqual(
            self.errors("langsmith agents list --workspace ws --profile p --name x"),
            [],
        )

    def test_generated_command_unknown_flag_and_subcommand_fail(self):
        self.assertEqual(
            self.errors("langsmith agents list --kind AGENT"),
            ["unknown or hidden flag --kind for `langsmith agents list`"],
        )
        self.assertEqual(
            self.errors("langsmith agents description"),
            ["unknown command `langsmith agents description`"],
        )


if __name__ == "__main__":
    unittest.main()
