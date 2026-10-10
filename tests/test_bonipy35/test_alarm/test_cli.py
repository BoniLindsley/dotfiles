#!/usr/bin/env python3

# Standard libraries.
import datetime
import time

from typing import Iterator
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.cli import (
    display,
    format_snapshot,
    main,
    make_parser,
    parse_alarm_time,
    parse_duration,
    request_fields,
)
from bonipy35.alarm.cmd import execute_line


@pytest.fixture(name="utc_timezone")
def fixture_utc_timezone(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    with monkeypatch.context() as patch:
        patch.setenv("TZ", "UTC")
        time.tzset()
        yield
    time.tzset()


class TestParseAlarmTime:
    @pytest.mark.usefixtures("utc_timezone")
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("13:00", "2026-10-11 13:00"),
            ("11:00", "2026-10-12 11:00"),
            ("12:00", "2026-10-11 12:00"),
            ("2026-10-10 08:00", "2026-10-10 08:00"),
        ],
    )
    def test_resolves_local_time(
        self, now: datetime.datetime, value: str, expected: str
    ) -> None:
        assert parse_alarm_time(value, now) == datetime.datetime.strptime(
            expected, "%Y-%m-%d %H:%M"
        ).replace(tzinfo=datetime.timezone.utc)

    @pytest.mark.parametrize("value", ["2026-10-11", "24:00", "garbage"])
    def test_invalid_input(self, now: datetime.datetime, value: str) -> None:
        with pytest.raises(ValueError, match="Expected"):
            parse_alarm_time(value, now)

    @pytest.mark.parametrize(
        "value", ["2026-03-08 02:30", "2026-11-01 01:30"]
    )
    def test_rejects_dst_gap_and_fold(
        self,
        now: datetime.datetime,
        value: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with monkeypatch.context() as patch:
            patch.setenv("TZ", "EST5EDT,M3.2.0,M11.1.0")
            time.tzset()
            try:
                with pytest.raises(
                    ValueError, match="ambiguous or nonexistent"
                ):
                    parse_alarm_time(value, now)
            finally:
                patch.undo()
                time.tzset()


class TestParseDuration:
    @pytest.mark.parametrize(
        "value,seconds",
        [("1h30m", 5400), ("2d 1h 2m 3s", 176523), ("45s", 45)],
    )
    def test_valid(self, value: str, seconds: int) -> None:
        assert parse_duration(value) == datetime.timedelta(seconds=seconds)

    @pytest.mark.parametrize(
        "value", ["", "0s", "-1s", "garbage", "1hgarbage", "1m1h"]
    )
    def test_rejects_invalid_or_nonpositive(self, value: str) -> None:
        with pytest.raises(ValueError):
            parse_duration(value)


class TestRequestFields:
    def test_timer(self) -> None:
        args = make_parser().parse_args(["timer", "1m", "--name", "Tea"])
        assert request_fields(args) == {"duration": 60, "name": "Tea"}

    @pytest.mark.usefixtures("utc_timezone")
    def test_reschedule(self) -> None:
        args = make_parser().parse_args(
            ["reschedule", "4", "2026-10-12 12:00"]
        )
        assert request_fields(args) == {
            "id_": 4,
            "end_time": "20261012T120000.000000Z",
        }


class TestDisplay:
    def test_notification_kind_and_items(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        snapshot = {
            "items": [
                {
                    "id_": 0,
                    "name": "Tea",
                    "state": "active",
                    "remaining": 5,
                    "end_time": "deadline",
                }
            ],
            "notifications": [
                {"id_": 0, "name": "Tea", "missed": True},
                {"id_": 1, "name": "Wake", "missed": False},
            ],
        }
        lines = format_snapshot(snapshot)
        assert "remaining 5s" in lines[0]
        assert lines[1:] == [
            "Notification 0: Tea (missed)",
            "Notification 1: Wake (expired)",
        ]
        display(snapshot)
        assert capsys.readouterr().out == "\n".join(lines) + "\n"


class TestMain:
    def test_missing_command(self) -> None:
        assert main(["alarm"]) == 1

    def test_invalid_input_does_not_start_server(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        constructor = Mock()
        monkeypatch.setattr("bonipy35.alarm.client.Client", constructor)
        assert main(["alarm", "timer", "garbage"]) == 1
        constructor.assert_not_called()


class TestExecuteLine:
    @pytest.mark.parametrize("line", ["exit", "quit"])
    def test_quit(self, line: str) -> None:
        assert not execute_line(Mock(), line)

    @pytest.mark.parametrize(
        "line", ["", "invalid", "timer garbage", "timer 'unclosed"]
    )
    def test_invalid_input_keeps_shell_running(self, line: str) -> None:
        assert execute_line(Mock(), line)


class TestShellCommands:
    def test_status_and_watch_display_current_state(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        connection = Mock()
        connection.snapshot = {"items": [], "notifications": []}
        connection.request.return_value = connection.snapshot
        assert execute_line(connection, "status")
        assert execute_line(connection, "watch")
        connection.request.assert_called_once_with("status")
        assert capsys.readouterr().out == ""

    def test_shutdown_exits(self) -> None:
        connection = Mock()
        connection.request.return_value = {"items": [], "notifications": []}
        assert not execute_line(connection, "shutdown")
