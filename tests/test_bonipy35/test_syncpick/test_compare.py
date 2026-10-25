#!/usr/bin/env python3

# Standard libraries.
import datetime
import os
import pathlib
import shutil
import sys

from typing import Dict, Iterator, List, Tuple, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.compare import (
    Entry,
    Side,
    State,
    compare,
    format_entry,
    format_side,
    list_files,
    parse_time,
)
from bonipy35.syncpick.rc import Daemon, RcError
from bonipy35.syncpick.runner import Runner

RCLONE = shutil.which("rclone")

UTC = datetime.timezone.utc

# Responses recorded from rclone v1.75.2, trimmed to the fields used.
_LEFT = {
    "list": [
        {
            "Path": "diff",
            "Size": 2,
            "ModTime": "2026-10-23T21:03:35.919882737Z",
        },
        {"Path": "same", "Size": 2, "ModTime": "2026-10-23T21:03:35Z"},
        {"Path": "d/onlya", "Size": 2, "ModTime": "2026-10-23T21:03:35Z"},
    ]
}  # type: Dict[str, object]
_RIGHT = {
    "list": [
        {"Path": "diff", "Size": 3, "ModTime": "2026-10-24T00:00:00+02:00"},
        {"Path": "same", "Size": 2, "ModTime": "2026-10-23T21:03:35Z"},
        {"Path": "e/onlyb", "Size": -1, "ModTime": "2026-10-23T21:03:35Z"},
    ]
}  # type: Dict[str, object]
_CHECK = {
    "combined": ["- e/onlyb", "* diff", "+ d/onlya", "= same", "! gone"],
    "differ": ["diff"],
    "error": ["gone"],
    "missingOnDst": ["d/onlya"],
    "missingOnSrc": ["e/onlyb"],
    "status": "4 differences found",
    "success": False,
}  # type: Dict[str, object]

Response = Union[Dict[str, object], RcError]


class FakeDaemon(Daemon):
    """Answers requests from recorded responses, keyed by path and ``fs``."""

    def __init__(self, responses: Dict[Tuple[str, str], Response]) -> None:
        super().__init__(Runner(executable=sys.executable))
        self.responses = responses
        self.calls = []  # type: List[Tuple[str, Dict[str, object]]]

    def call(
        self, path: str, parameters: Union[None, Dict[str, object]] = None
    ) -> Dict[str, object]:
        parameters = parameters or {}
        self.calls.append((path, parameters))
        response = self.responses[
            (path, str(parameters.get("fs", parameters.get("srcFs"))))
        ]
        if isinstance(response, RcError):
            raise response
        return response


def missing(path: str) -> RcError:
    return RcError(
        "error in ListJSON: directory not found", path=path, status=404
    )


@pytest.fixture(name="daemon")
def fixture_daemon() -> FakeDaemon:
    return FakeDaemon(
        {
            ("operations/list", "left"): _LEFT,
            ("operations/list", "right:"): _RIGHT,
            ("operations/check", "left"): _CHECK,
        }
    )


class TestCompare:
    def test_merges_listing_and_check(self, daemon: FakeDaemon) -> None:
        same = Side(
            size=2,
            modified=datetime.datetime(2026, 10, 23, 21, 3, 35, tzinfo=UTC),
        )
        assert compare(daemon, "left", "right:") == [
            Entry(
                path="d/onlya", state=State.LEFT_ONLY, left=same, right=None
            ),
            Entry(
                path="diff",
                state=State.DIFFERENT,
                left=Side(
                    size=2,
                    modified=datetime.datetime(
                        2026, 10, 23, 21, 3, 35, 919882, tzinfo=UTC
                    ),
                ),
                right=Side(
                    size=3,
                    modified=datetime.datetime(
                        2026, 10, 23, 22, 0, tzinfo=UTC
                    ),
                ),
            ),
            Entry(
                path="e/onlyb",
                state=State.RIGHT_ONLY,
                left=None,
                right=same._replace(size=-1),
            ),
            Entry(path="gone", state=State.ERROR, left=None, right=None),
            Entry(path="same", state=State.SAME, left=same, right=same),
        ]
        assert daemon.calls[-1] == (
            "operations/check",
            {"srcFs": "left", "dstFs": "right:", "combined": True},
        )

    def test_keeps_spaces_in_paths(self, daemon: FakeDaemon) -> None:
        daemon.responses[("operations/check", "left")] = {
            "combined": ["=  two  spaces "]
        }
        assert [
            entry.path for entry in compare(daemon, "left", "right:")
        ] == [" two  spaces "]

    @pytest.mark.parametrize(
        ("combined", "message"),
        [
            (None, "Unexpected response: None"),
            (["= ok", 1], "Unexpected response: ['= ok', 1]"),
            (["? odd"], "Unexpected check line: '? odd'"),
        ],
    )
    def test_unexpected_check(
        self, daemon: FakeDaemon, combined: object, message: str
    ) -> None:
        daemon.responses[("operations/check", "left")] = {
            "combined": combined
        }
        with pytest.raises(RcError) as raised:
            compare(daemon, "left", "right:")
        assert str(raised.value) == message
        assert raised.value.path == "operations/check"


class TestListFiles:
    def test_lists_recursively(self, daemon: FakeDaemon) -> None:
        assert sorted(list_files(daemon, "left")) == [
            "d/onlya",
            "diff",
            "same",
        ]
        assert daemon.calls == [
            (
                "operations/list",
                {
                    "fs": "left",
                    "remote": "",
                    "opt": {"recurse": True, "filesOnly": True},
                },
            )
        ]

    def test_missing_is_empty(self, daemon: FakeDaemon) -> None:
        daemon.responses[("operations/list", "left")] = missing(
            "operations/list"
        )
        assert not list_files(daemon, "left")

    def test_other_errors_raise(self, daemon: FakeDaemon) -> None:
        error = RcError("no remote", path="operations/list", status=500)
        daemon.responses[("operations/list", "left")] = error
        with pytest.raises(RcError) as raised:
            list_files(daemon, "left")
        assert raised.value is error

    @pytest.mark.parametrize(
        "response",
        [
            {},
            {"list": [1]},
            {"list": [{"Path": "p", "Size": "2", "ModTime": "x"}]},
            {"list": [{"Path": "p", "Size": 2}]},
            {"list": [{"Path": "p", "Size": 2, "ModTime": "yesterday"}]},
        ],
    )
    def test_unexpected(
        self, daemon: FakeDaemon, response: Dict[str, object]
    ) -> None:
        daemon.responses[("operations/list", "left")] = response
        with pytest.raises(RcError, match="Unexpected response") as raised:
            list_files(daemon, "left")
        assert raised.value.path == "operations/list"
        assert raised.value.status == 200


class TestFormatSide:
    def test_converts_to_utc(self) -> None:
        offset = datetime.timezone(datetime.timedelta(hours=2))
        side = Side(
            size=12,
            modified=datetime.datetime(
                2026, 10, 24, 0, 0, 1, 999999, tzinfo=offset
            ),
        )
        assert format_side(side) == "12\t2026-10-23T22:00:01Z"

    def test_missing(self) -> None:
        assert format_side(None) == "-\t-"


class TestFormatEntry:
    def test_ends_with_path(self) -> None:
        side = Side(
            size=-1,
            modified=datetime.datetime(2026, 10, 23, 21, 3, 35, tzinfo=UTC),
        )
        assert (
            format_entry(
                Entry(
                    path="d/a file",
                    state=State.LEFT_ONLY,
                    left=side,
                    right=None,
                )
            )
            == "+\t-1\t2026-10-23T21:03:35Z\t-\t-\td/a file"
        )


class TestParseTime:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            (
                "2026-10-23T21:03:35Z",
                datetime.datetime(2026, 10, 23, 21, 3, 35, tzinfo=UTC),
            ),
            (
                "2026-10-23T21:03:35.123456789Z",
                datetime.datetime(
                    2026, 10, 23, 21, 3, 35, 123456, tzinfo=UTC
                ),
            ),
            (
                "2026-10-23T21:03:35.5Z",
                datetime.datetime(
                    2026, 10, 23, 21, 3, 35, 500000, tzinfo=UTC
                ),
            ),
            (
                "2026-10-23T21:03:35+05:30",
                datetime.datetime(2026, 10, 23, 15, 33, 35, tzinfo=UTC),
            ),
            (
                "2026-10-23T21:03:35-01:00",
                datetime.datetime(2026, 10, 23, 22, 3, 35, tzinfo=UTC),
            ),
        ],
    )
    def test_parses(self, text: str, expected: datetime.datetime) -> None:
        parsed = parse_time(text)
        assert parsed == expected
        assert parsed.utcoffset() is not None

    @pytest.mark.parametrize(
        "text", ["2026-10-23T21:03:35", "2026-10-23 21:03:35Z", ""]
    )
    def test_rejects(self, text: str) -> None:
        with pytest.raises(ValueError, match="Not an RFC 3339 time"):
            parse_time(text)


@pytest.fixture(name="real_daemon")
def fixture_real_daemon(tmp_path: pathlib.Path) -> Iterator[Daemon]:
    config = tmp_path / "rclone.conf"
    config.write_text("")
    with Daemon(Runner(config=config)) as daemon:
        yield daemon


def write(path: pathlib.Path, content: str, *, mtime_ns: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    os.utime(str(path), ns=(mtime_ns, mtime_ns))


@pytest.mark.integration
@pytest.mark.skipif(RCLONE is None, reason="Executable not found: rclone")
class TestRealCompare:
    def test_states(
        self, real_daemon: Daemon, tmp_path: pathlib.Path
    ) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        mtime_ns = 1792789415123456789
        write(left / "same", "s", mtime_ns=mtime_ns)
        write(right / "same", "s", mtime_ns=mtime_ns)
        write(left / "diff", "x", mtime_ns=mtime_ns)
        write(right / "diff", "yy", mtime_ns=mtime_ns + 10**9)
        write(left / "samesize", "a", mtime_ns=mtime_ns)
        write(right / "samesize", "b", mtime_ns=mtime_ns)
        write(left / "d" / "onlyleft", "l", mtime_ns=mtime_ns)
        write(right / "e" / "onlyright", "r", mtime_ns=mtime_ns)
        entries = compare(real_daemon, str(left), str(right))
        assert [(entry.path, entry.state) for entry in entries] == [
            ("d/onlyleft", State.LEFT_ONLY),
            ("diff", State.DIFFERENT),
            ("e/onlyright", State.RIGHT_ONLY),
            ("same", State.SAME),
            ("samesize", State.DIFFERENT),
        ]
        modified = datetime.datetime(
            2026, 10, 23, 21, 3, 35, 123456, tzinfo=UTC
        )
        by_path = {entry.path: entry for entry in entries}
        assert by_path["diff"].left == Side(size=1, modified=modified)
        assert by_path["diff"].right == Side(
            size=2, modified=modified + datetime.timedelta(seconds=1)
        )
        assert by_path["d/onlyleft"].right is None
        assert by_path["e/onlyright"].left is None

    def test_missing_side(
        self, real_daemon: Daemon, tmp_path: pathlib.Path
    ) -> None:
        left = tmp_path / "left"
        write(left / "file", "f", mtime_ns=0)
        missing_path = str(tmp_path / "missing")
        assert [
            (entry.path, entry.state)
            for entry in compare(real_daemon, str(left), missing_path)
        ] == [("file", State.LEFT_ONLY)]
        assert [
            (entry.path, entry.state)
            for entry in compare(real_daemon, missing_path, str(left))
        ] == [("file", State.RIGHT_ONLY)]

    @pytest.mark.skipif(
        not hasattr(os, "geteuid") or os.geteuid() == 0,
        reason="Needs a user that file permissions apply to",
    )
    def test_unreadable_is_error(
        self, real_daemon: Daemon, tmp_path: pathlib.Path
    ) -> None:
        left = tmp_path / "left"
        right = tmp_path / "right"
        write(left / "file", "a", mtime_ns=0)
        write(right / "file", "b", mtime_ns=0)
        (left / "file").chmod(0)
        try:
            entries = compare(real_daemon, str(left), str(right))
        finally:
            (left / "file").chmod(0o644)
        assert [(entry.path, entry.state) for entry in entries] == [
            ("file", State.ERROR)
        ]
