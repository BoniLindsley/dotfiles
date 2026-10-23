#!/usr/bin/env python3

# Standard libraries.
import json
import pathlib
import shutil
import sys

from typing import List

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.runner import (
    Completed,
    RcloneError,
    Runner,
    argument_parser,
    runner_from_arguments,
)

RCLONE = shutil.which("rclone")

# Reports its arguments, standard input and configuration as JSON,
# then exits with the code given by a `--exit=N` argument.
# Run by the Python interpreter with `-c`, so that no file needs executing.
_FAKE_RCLONE = """
import json
import os
import sys

code = 0
for argument in sys.argv[1:]:
    if argument.startswith("--exit="):
        code = int(argument[len("--exit="):])
if "--bad-json" in sys.argv:
    sys.stdout.write("not json")
else:
    json.dump(
        {
            "arguments": sys.argv[1:],
            "config": os.environ.get("RCLONE_CONFIG"),
            "stdin": sys.stdin.read(),
        },
        sys.stdout,
    )
sys.stderr.write("fake stderr")
sys.exit(code)
"""


@pytest.fixture(name="runner")
def fixture_runner() -> Runner:
    return Runner(executable=sys.executable)


def fake(*arguments: str) -> List[str]:
    """Arguments making the interpreter behave as a fake rclone."""
    return ["-c", _FAKE_RCLONE] + list(arguments)


class TestRunner:
    class TestInit:
        def test_searches_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
            searched = []  # type: List[str]

            def which(name: str) -> str:
                searched.append(name)
                return "/found/rclone"

            monkeypatch.setattr(shutil, "which", which)
            assert Runner().executable == "/found/rclone"
            assert searched == ["rclone"]

        def test_missing_executable(
            self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
        ) -> None:
            monkeypatch.setenv("PATH", str(tmp_path))
            with pytest.raises(RcloneError, match="not found"):
                Runner()

    class TestRun:
        def test_passes_arguments_and_stdin(self, runner: Runner) -> None:
            completed = runner.run(fake("copy", "a b", "ü"), stdin="x\ny\n")
            assert completed.returncode == 0
            assert completed.stderr == "fake stderr"
            assert json.loads(completed.stdout) == {
                "arguments": ["copy", "a b", "ü"],
                "config": None,
                "stdin": "x\ny\n",
            }

        def test_sets_config(
            self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
        ) -> None:
            monkeypatch.delenv("RCLONE_CONFIG", raising=False)
            config = tmp_path / "rclone.conf"
            runner = Runner(executable=sys.executable, config=config)
            output = json.loads(runner.run(fake()).stdout)
            assert output["config"] == str(config)

        def test_unexpected_exit_code(self, runner: Runner) -> None:
            with pytest.raises(RcloneError, match="code 1") as raised:
                runner.run(fake("check", "--exit=1"))
            assert raised.value.returncode == 1
            assert raised.value.stderr == "fake stderr"
            assert raised.value.command == [runner.executable] + fake(
                "check", "--exit=1"
            )

        def test_accepted_exit_code(self, runner: Runner) -> None:
            completed = runner.run(fake("check", "--exit=1"), accepted=(0, 1))
            assert completed.returncode == 1

        def test_unrunnable_executable(self, tmp_path: pathlib.Path) -> None:
            runner = Runner(executable=str(tmp_path / "missing"))
            with pytest.raises(RcloneError) as raised:
                runner.run([])
            assert raised.value.returncode is None

    class TestRunJson:
        def test_parses_output(self, runner: Runner) -> None:
            output = runner.run_json(fake("lsjson"))
            assert isinstance(output, dict)
            assert output["arguments"] == ["lsjson"]

        def test_invalid_output(self, runner: Runner) -> None:
            with pytest.raises(RcloneError, match="Invalid JSON") as raised:
                runner.run_json(fake("--bad-json"))
            assert raised.value.returncode == 0


class TestRunnerFromArguments:
    def test_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(shutil, "which", lambda name: "/found/" + name)
        parser = argument_parser(description="")
        runner = runner_from_arguments(parser.parse_args([]))
        assert runner.executable == "/found/rclone"
        assert runner.config is None

    def test_options(self) -> None:
        parser = argument_parser(description="")
        runner = runner_from_arguments(
            parser.parse_args(["--rclone", "/x/rclone", "--config", "a.conf"])
        )
        assert runner.executable == "/x/rclone"
        assert runner.config == pathlib.Path("a.conf")


@pytest.mark.integration
@pytest.mark.skipif(RCLONE is None, reason="Executable not found: rclone")
class TestRealRclone:
    def test_lsjson(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "rclone.conf"
        config.write_text("")
        tree = tmp_path / "tree"
        (tree / "d").mkdir(parents=True)
        (tree / "d" / "file").write_text("content")
        runner = Runner(config=config)
        output = runner.run_json(["lsjson", "-R", "--files-only", str(tree)])
        assert isinstance(output, list)
        assert [(item["Path"], item["Size"]) for item in output] == [
            ("d/file", 7)
        ]

    def test_completed_type(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "rclone.conf"
        config.write_text("")
        completed = Runner(config=config).run(["version"])
        assert isinstance(completed, Completed)
        assert completed.stdout.startswith("rclone v")
