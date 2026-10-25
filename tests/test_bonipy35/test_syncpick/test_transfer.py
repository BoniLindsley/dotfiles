#!/usr/bin/env python3

# Standard libraries.
import pathlib
import shutil
import sys

from typing import Dict, Iterator, List, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.rc import Daemon, RcError
from bonipy35.syncpick.runner import Runner
from bonipy35.syncpick.transfer import Direction, Result, copy_files

RCLONE = shutil.which("rclone")


class FakeDaemon(Daemon):
    """Records requests, failing for source paths in ``failures``."""

    def __init__(self, failures: Dict[str, RcError]) -> None:
        super().__init__(Runner(executable=sys.executable))
        self.failures = failures
        self.calls = []  # type: List[Dict[str, object]]

    def call(
        self, path: str, parameters: Union[None, Dict[str, object]] = None
    ) -> Dict[str, object]:
        assert path == "operations/copyfile"
        parameters = parameters or {}
        self.calls.append(parameters)
        error = self.failures.get(str(parameters["srcRemote"]))
        if error is not None:
            raise error
        return {}


@pytest.fixture(name="daemon")
def fixture_daemon() -> FakeDaemon:
    return FakeDaemon(
        {
            "missing": RcError(
                "object not found", path="operations/copyfile", status=404
            )
        }
    )


class TestCopyFiles:
    @pytest.mark.parametrize(
        ("direction", "source", "destination"),
        [
            (Direction.LEFT_TO_RIGHT, "left", "right:"),
            (Direction.RIGHT_TO_LEFT, "right:", "left"),
        ],
    )
    def test_direction(
        self,
        daemon: FakeDaemon,
        direction: Direction,
        source: str,
        destination: str,
    ) -> None:
        results = list(
            copy_files(
                daemon, "left", "right:", ["a", "d/b"], direction=direction
            )
        )
        assert results == [
            Result(path="a", error=None),
            Result(path="d/b", error=None),
        ]
        assert daemon.calls == [
            {
                "srcFs": source,
                "srcRemote": path,
                "dstFs": destination,
                "dstRemote": path,
            }
            for path in ["a", "d/b"]
        ]

    def test_failure_does_not_stop_others(self, daemon: FakeDaemon) -> None:
        results = list(
            copy_files(
                daemon,
                "left",
                "right:",
                ["a", "missing", "b"],
                direction=Direction.LEFT_TO_RIGHT,
            )
        )
        assert results == [
            Result(path="a", error=None),
            Result(path="missing", error="object not found"),
            Result(path="b", error=None),
        ]

    def test_copies_lazily(self, daemon: FakeDaemon) -> None:
        results = copy_files(
            daemon,
            "left",
            "right:",
            ["a", "b"],
            direction=Direction.LEFT_TO_RIGHT,
        )
        assert not daemon.calls
        assert next(results) == Result(path="a", error=None)
        assert len(daemon.calls) == 1
        results.close()
        assert len(daemon.calls) == 1


@pytest.fixture(name="real_daemon")
def fixture_real_daemon(tmp_path: pathlib.Path) -> Iterator[Daemon]:
    config = tmp_path / "rclone.conf"
    config.write_text("")
    with Daemon(Runner(config=config)) as daemon:
        yield daemon


def tree(root: pathlib.Path) -> Dict[str, str]:
    return {
        path.relative_to(root).as_posix(): path.read_text()
        for path in root.rglob("*")
        if path.is_file()
    }


def write(root: pathlib.Path, files: Dict[str, str]) -> None:
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)


@pytest.mark.integration
@pytest.mark.skipif(RCLONE is None, reason="Executable not found: rclone")
class TestRealCopyFiles:
    def test_both_directions(
        self, real_daemon: Daemon, tmp_path: pathlib.Path
    ) -> None:
        left = tmp_path / "left"
        right = tmp_path / "new" / "right"
        write(left, {"a": "left a", "d/b": "left b", "unpicked": "u"})
        results = list(
            copy_files(
                real_daemon,
                str(left),
                str(right),
                ["a", "d/b", "missing"],
                direction=Direction.LEFT_TO_RIGHT,
            )
        )
        assert [
            (result.path, result.error is None) for result in results
        ] == [
            ("a", True),
            ("d/b", True),
            ("missing", False),
        ]
        assert tree(right) == {"a": "left a", "d/b": "left b"}

        write(right, {"a": "right a", "c": "right c", "other": "o"})
        assert all(
            result.error is None
            for result in copy_files(
                real_daemon,
                str(left),
                str(right),
                ["a", "c"],
                direction=Direction.RIGHT_TO_LEFT,
            )
        )
        assert tree(left) == {
            "a": "right a",
            "c": "right c",
            "d/b": "left b",
            "unpicked": "u",
        }
        assert tree(right) == {
            "a": "right a",
            "c": "right c",
            "d/b": "left b",
            "other": "o",
        }
