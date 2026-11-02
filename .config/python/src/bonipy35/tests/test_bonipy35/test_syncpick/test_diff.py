#!/usr/bin/env python3

# Standard libraries.
import pathlib
import shutil
import sys

from typing import Dict, List, Tuple, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.diff import (
    CONTEXT,
    Diff,
    Line,
    Reason,
    diff,
    diff_contents,
    hunks,
    text_lines,
)
from bonipy35.syncpick.rc import Daemon, RcError
from bonipy35.syncpick.runner import Runner

RCLONE = shutil.which("rclone")


class FakeDaemon(Daemon):
    """Reads files from ``files``, keyed by ``fs`` and path."""

    def __init__(self, files: Dict[Tuple[str, str], bytes]) -> None:
        super().__init__(Runner(executable=sys.executable))
        self.files = files
        self.error = None  # type: Union[None, RcError]
        self.reads = []  # type: List[Tuple[str, str, int]]

    def read(self, fs: str, path: str, *, limit: int) -> bytes:
        self.reads.append((fs, path, limit))
        if self.error is not None:
            raise self.error
        try:
            return self.files[(fs, path)][:limit]
        except KeyError:
            raise RcError(
                "object not found",
                path="[{}]/{}".format(fs, path),
                status=404,
            ) from None


class TestDiff:
    def test_compares_contents(self) -> None:
        daemon = FakeDaemon(
            {("l", "d/p"): b"a\nb\n", ("r:", "d/p"): b"a\nc\n"}
        )
        assert diff(daemon, "l", "r:", "d/p", limit=10) == Diff(
            hunks=[
                [
                    Line(kind=" ", left=1, right=1, text="a"),
                    Line(kind="-", left=None, right=2, text="c"),
                    Line(kind="+", left=2, right=None, text="b"),
                ]
            ],
            reason=None,
        )
        assert daemon.reads == [("l", "d/p", 11), ("r:", "d/p", 11)]

    def test_too_large(self) -> None:
        daemon = FakeDaemon({("l", "p"): b"12345", ("r:", "p"): b"12345"})
        assert diff(daemon, "l", "r:", "p", limit=4) == Diff(
            hunks=[], reason=Reason.TOO_LARGE
        )

    def test_left_missing(self) -> None:
        daemon = FakeDaemon({("r:", "p"): b"a"})
        assert diff(daemon, "l", "r:", "p") == Diff(
            hunks=[], reason=Reason.LEFT_MISSING
        )
        assert len(daemon.reads) == 1

    def test_right_missing(self) -> None:
        daemon = FakeDaemon({("l", "p"): b"a"})
        assert diff(daemon, "l", "r:", "p") == Diff(
            hunks=[], reason=Reason.RIGHT_MISSING
        )

    def test_error(self) -> None:
        daemon = FakeDaemon({})
        daemon.error = RcError("is a directory", path="[l]/p", status=500)
        with pytest.raises(RcError, match="is a directory"):
            diff(daemon, "l", "r:", "p")


class TestDiffContents:
    def test_same(self) -> None:
        assert diff_contents(b"a\n", b"a\n") == Diff(
            hunks=[], reason=Reason.SAME
        )

    @pytest.mark.parametrize(
        ("left", "right"),
        [(b"a\r\nb\r\n", b"a\nb\n"), (b"a\rb", b"a\nb"), (b"a\n", b"a")],
    )
    def test_line_endings(self, left: bytes, right: bytes) -> None:
        assert diff_contents(left, right) == Diff(
            hunks=[], reason=Reason.LINE_ENDINGS
        )

    def test_ignores_line_endings_in_hunks(self) -> None:
        assert diff_contents(b"a\r\nb\r\n", b"a\nc\n").hunks == [
            [
                Line(kind=" ", left=1, right=1, text="a"),
                Line(kind="-", left=None, right=2, text="c"),
                Line(kind="+", left=2, right=None, text="b"),
            ]
        ]

    @pytest.mark.parametrize(
        ("left", "right"), [(b"a\0", b"a"), (b"a", b"\xff")]
    )
    def test_binary(self, left: bytes, right: bytes) -> None:
        assert diff_contents(left, right) == Diff(
            hunks=[], reason=Reason.BINARY
        )

    @pytest.mark.parametrize(
        ("left", "right"),
        [(b"12345", b"1234"), (b"1234", b"12345"), (b"12345", b"12345")],
    )
    def test_too_large(self, left: bytes, right: bytes) -> None:
        assert diff_contents(left, right, limit=4) == Diff(
            hunks=[], reason=Reason.TOO_LARGE
        )

    def test_at_limit(self) -> None:
        assert diff_contents(b"123\n", b"124\n", limit=4).reason is None


class TestTextLines:
    @pytest.mark.parametrize(
        ("content", "lines"),
        [
            (b"", []),
            (b"\n", [""]),
            (b"a", ["a"]),
            (b"a\n", ["a"]),
            (b"a\n\n", ["a", ""]),
            (b"a\r\nb\rc\nd", ["a", "b", "c", "d"]),
            ("ü x\n".encode("utf-8"), ["ü x"]),
        ],
    )
    def test_splits(self, content: bytes, lines: List[str]) -> None:
        assert text_lines(content) == lines

    @pytest.mark.parametrize("content", [b"a\0b", b"\xff", b"\xc3"])
    def test_binary(self, content: bytes) -> None:
        with pytest.raises(ValueError):
            text_lines(content)


class TestHunks:
    def test_same(self) -> None:
        assert not hunks(["a"], ["a"])

    def test_numbers_both_sides(self) -> None:
        assert hunks(["x", "a", "b"], ["a", "c", "b", "y"]) == [
            [
                Line(kind="+", left=1, right=None, text="x"),
                Line(kind=" ", left=2, right=1, text="a"),
                Line(kind="-", left=None, right=2, text="c"),
                Line(kind=" ", left=3, right=3, text="b"),
                Line(kind="-", left=None, right=4, text="y"),
            ]
        ]

    def test_context_splits_hunks(self) -> None:
        right = ["{}".format(index) for index in range(20)]
        left = list(right)
        left[1] = "one"
        left[18] = "eighteen"
        result = hunks(left, right)
        assert len(result) == 2
        assert [line.right for line in result[0]] == [1, 2, None] + list(
            range(3, 3 + CONTEXT)
        )
        assert result[1][-1] == Line(kind=" ", left=20, right=20, text="19")


@pytest.mark.integration
@pytest.mark.skipif(RCLONE is None, reason="Executable not found: rclone")
class TestRealDiff:
    def test_diff(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "rclone.conf"
        config.write_text("")
        left = tmp_path / "left dir"
        right = tmp_path / "right"
        (left / "d").mkdir(parents=True)
        (right / "d").mkdir(parents=True)
        (left / "d" / "a #1").write_bytes(b"one\r\ntwo\r\n")
        (right / "d" / "a #1").write_bytes(b"one\nthree\n")
        (left / "big").write_bytes(b"x" * 11)
        (right / "big").write_bytes(b"y")
        with Daemon(Runner(config=config)) as daemon:
            assert diff(daemon, str(left), str(right), "d/a #1").hunks == [
                [
                    Line(kind=" ", left=1, right=1, text="one"),
                    Line(kind="-", left=None, right=2, text="three"),
                    Line(kind="+", left=2, right=None, text="two"),
                ]
            ]
            assert (
                diff(daemon, str(left), str(right), "big", limit=10).reason
                is Reason.TOO_LARGE
            )
            assert (
                diff(daemon, str(left), str(right), "missing").reason
                is Reason.LEFT_MISSING
            )
