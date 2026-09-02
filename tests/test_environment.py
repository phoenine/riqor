from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools.cli import main
from tools.environment import (
    ENV_GROUPS,
    EnvironmentFileError,
    environment_group_status,
    load_project_environment,
)


ROOT = Path(__file__).resolve().parents[1]


class EnvironmentTests(unittest.TestCase):
    def test_loads_dotenv_without_overriding_process_environment(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env").write_text(
                "# local values\n"
                "ZENTAO_BASE_URL=https://local.example\n"
                "export ZENTAO_USERNAME='local user'\n"
                "ZENTAO_PASSWORD=local#password\n"
                "ZENTAO_API_TOKEN=local-token # comment\n",
                encoding="utf-8",
            )
            environment = {"ZENTAO_USERNAME": "from-process"}

            loaded = load_project_environment(root, environ=environment)

        self.assertEqual(environment["ZENTAO_BASE_URL"], "https://local.example")
        self.assertEqual(environment["ZENTAO_USERNAME"], "from-process")
        self.assertEqual(environment["ZENTAO_PASSWORD"], "local#password")
        self.assertEqual(environment["ZENTAO_API_TOKEN"], "local-token")
        self.assertNotIn("ZENTAO_USERNAME", loaded)

    def test_missing_file_is_optional_and_malformed_file_fails_closed(self) -> None:
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(load_project_environment(root, environ={}), [])
            (root / ".env").write_text("NOT AN ASSIGNMENT\n", encoding="utf-8")
            with self.assertRaisesRegex(EnvironmentFileError, r"line 1"):
                load_project_environment(root, environ={})

    def test_example_declares_every_supported_variable(self) -> None:
        example_environment: dict[str, str] = {}
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".env").write_text(
                (ROOT / ".env.example").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            load_project_environment(root, environ=example_environment)

        expected = {name for variables in ENV_GROUPS.values() for name in variables}
        self.assertEqual(set(example_environment), expected)

    def test_group_status_and_cli_never_print_values(self) -> None:
        status = environment_group_status(
            "ZENTAO",
            environ={
                "ZENTAO_BASE_URL": "https://private.example",
                "ZENTAO_API_TOKEN": "sensitive",
            },
        )
        self.assertIn(("ZENTAO_BASE_URL", True), status)
        self.assertIn(("ZENTAO_PASSWORD", False), status)

        with TemporaryDirectory() as temporary, patch.dict("os.environ", {}, clear=True):
            root = Path(temporary)
            (root / ".env").write_text(
                "ZENTAO_BASE_URL=https://private.example\nZENTAO_API_TOKEN=sensitive\n",
                encoding="utf-8",
            )
            output = StringIO()
            with redirect_stdout(output):
                exit_code = main(["env", "--group", "ZENTAO", "--root", str(root)])

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("SET ZENTAO_BASE_URL", rendered)
        self.assertIn("EMPTY ZENTAO_PASSWORD", rendered)
        self.assertNotIn("private.example", rendered)
        self.assertNotIn("sensitive", rendered)

    def test_git_ignores_local_env_but_tracks_example(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env\n", ignore)
        self.assertIn("!.env.example", ignore)


if __name__ == "__main__":
    unittest.main()
