#!/usr/bin/env python3

# Standard libraries.
import concurrent.futures
import datetime
import fcntl
import os
import pty
import pathlib
import selectors
import socket
import subprocess
import struct
import sys
import termios
import time
import threading

from typing import Any, Dict, List, cast

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.client import Client, connect_socket, ensure_server
from bonipy35.alarm.clock import DeadlineClock
from bonipy35.alarm.data import Datetime, State, UserData, utc_now
from bonipy35.alarm.paths import default_directory, prepare_directory
from bonipy35.alarm.protocol import Decoder, MAX_FRAME, encode
from bonipy35.alarm.server import Server


def next_event(connection: Client) -> Dict[str, Any]:
    while True:
        message = connection.receive()
        if message.get("event") == "snapshot":
            return cast(Dict[str, Any], message["snapshot"])


class TestServerLifecycle:
    def test_stop_before_run_returns_and_cleans_up(
        self, tmp_path: pathlib.Path
    ) -> None:
        service = Server(directory=tmp_path)
        service.stop()
        service.run()
        assert not (tmp_path / "socket").exists()
        service.close()

    def test_stop_wakes_idle_server(self, service: Server) -> None:
        service.stop()

    def test_live_server_cannot_be_replaced(
        self, service: Server, connection: Client
    ) -> None:
        with pytest.raises(BlockingIOError):
            Server(directory=service.directory)
        assert connection.request("status") == {
            "items": [],
            "notifications": [],
        }
        assert (service.directory / "socket").exists()

    def test_stale_socket_replaced(self, tmp_path: pathlib.Path) -> None:
        endpoint = tmp_path / "socket"
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stale:
            stale.bind(str(endpoint))
        service = Server(directory=tmp_path)
        service.close()
        assert not endpoint.exists()

    def test_corrupt_state_not_overwritten(
        self, tmp_path: pathlib.Path
    ) -> None:
        path = tmp_path / "state.json"
        path.write_text("broken", encoding="utf-8")
        with pytest.raises(ValueError):
            Server(directory=tmp_path)
        assert path.read_text(encoding="utf-8") == "broken"
        assert not (tmp_path / "socket").exists()


class TestServerCommands:
    def test_create_pause_resume_restart_stop_delete_and_unique_ids(
        self, connection: Client, service: Server
    ) -> None:
        snapshot = connection.request("timer", duration=60, name="Tea")
        assert snapshot["items"][0]["name"] == "Tea"
        assert snapshot["items"][0]["id_"] == 0
        snapshot = connection.request("pause", id_=0)
        paused_remaining = snapshot["items"][0]["remaining"]
        assert snapshot["items"][0]["state"] == "paused"
        assert (
            connection.request("status")["items"][0]["remaining"]
            == paused_remaining
        )
        assert (
            connection.request("resume", id_=0)["items"][0]["state"]
            == "active"
        )
        assert (
            connection.request("stop", id_=0)["items"][0]["state"]
            == "stopped"
        )
        snapshot = connection.request("restart", id_=0)
        assert snapshot["items"][0]["remaining"] > 59
        assert connection.request("delete", id_=0)["items"] == []
        assert connection.request("timer", duration=1)["items"][0]["id_"] == 1
        state = UserData.model_validate_json(
            service.state_path.read_text(encoding="utf-8")
        )
        assert state.next_id == 2
        assert not list(service.directory.glob("state-*.tmp"))
        assert service.state_path.stat().st_mode & 0o077 == 0

    def test_alarm_reschedule_and_invalid_restart(
        self, connection: Client
    ) -> None:
        deadline = utc_now() + datetime.timedelta(hours=1)
        connection.request(
            "alarm", end_time=Datetime.model_dump(deadline), name="Wake"
        )
        later = deadline + datetime.timedelta(hours=1)
        snapshot = connection.request(
            "reschedule", id_=0, end_time=Datetime.model_dump(later)
        )
        assert snapshot["items"][0]["end_time"] == Datetime.model_dump(later)
        with pytest.raises(ValueError, match="Only timers"):
            connection.request("restart", id_=0)

    @pytest.mark.parametrize(
        "command,fields",
        [
            ("delete", {"id_": 99}),
            ("timer", {"duration": -1}),
            ("timer", {"duration": float("inf")}),
            ("alarm", {"end_time": "bad"}),
            ("pause", {}),
            ("unknown", {"id_": 0}),
        ],
    )
    def test_invalid_request_does_not_disconnect_client(
        self, connection: Client, command: str, fields: Dict[str, Any]
    ) -> None:
        with pytest.raises(ValueError):
            connection.request(command, **fields)
        assert connection.request("status")["items"] == []

    def test_oversized_state_rolls_back_and_partial_writes_complete(
        self, connection: Client, service: Server
    ) -> None:
        name = "x" * (MAX_FRAME // 4)
        assert (
            connection.request("timer", duration=60, name=name)["items"][0][
                "name"
            ]
            == name
        )
        with pytest.raises(ValueError, match="frame limit"):
            connection.request("timer", duration=60, name=name)
        assert len(connection.request("status")["items"]) == 1
        persisted = UserData.model_validate_json(
            service.state_path.read_text(encoding="utf-8")
        )
        assert len(persisted.alarms) == 1
        assert persisted.next_id == 1

    @pytest.mark.parametrize("command,name", [(None, ""), ("timer", None)])
    def test_invalid_field_types_return_errors(
        self, connection: Client, command: Any, name: Any
    ) -> None:
        connection.sock.sendall(
            encode(
                {
                    "request_id": 100,
                    "command": command,
                    "name": name,
                    "duration": 60,
                }
            )
        )
        assert "string" in connection.receive()["error"]
        assert not connection.request("status")["items"]

    def test_unknown_command_keeps_existing_item(
        self, connection: Client
    ) -> None:
        connection.request("timer", duration=60)
        with pytest.raises(ValueError, match="Unknown command"):
            connection.request("unknown", id_=0)
        assert len(connection.request("status")["items"]) == 1

    def test_bad_request_id_returns_error(self, connection: Client) -> None:
        connection.sock.sendall(
            encode({"request_id": True, "command": "status"})
        )
        assert "integer" in connection.receive()["error"]


class TestNotifications:
    def test_expiry_pushed_and_repeated_until_global_dismissal(
        self, service: Server, connection: Client
    ) -> None:
        with Client(directory=service.directory) as other:
            connection.request("timer", duration=0.1, name="Tea")
            created = next_event(other)
            assert created["notifications"] == []
            expired = next_event(other)
            assert expired["items"][0]["state"] == "triggered"
            assert expired["notifications"][0]["name"] == "Tea"
            first = connection.request("notifications")["notifications"]
            assert connection.request("status")["notifications"] == first
            connection.request("dismiss", id_=0)
            assert next_event(other)["notifications"] == []
            assert other.request("status")["notifications"] == []
            assert (
                connection.request("status")["items"][0]["state"]
                == "triggered"
            )
            with Client(directory=service.directory) as late:
                assert late.snapshot["notifications"] == []

    def test_disconnected_expiry_available_on_reconnect(
        self, service: Server
    ) -> None:
        with Client(directory=service.directory) as creator:
            creator.request("timer", duration=0.05)
        # Readiness wait is tied to the actual deadline, not periodic polling.
        with Client(directory=service.directory) as observer:
            if not observer.snapshot["notifications"]:
                next_event(observer)
        with Client(directory=service.directory) as late:
            assert late.snapshot["notifications"][0]["missed"] is False

    def test_creating_and_rescheduling_past_alarm_keeps_active_status(
        self, connection: Client
    ) -> None:
        past = utc_now() - datetime.timedelta(hours=1)
        snapshot = connection.request(
            "alarm", end_time=Datetime.model_dump(past)
        )
        assert snapshot["items"][0]["state"] == "active"
        assert snapshot["notifications"][0]["missed"]
        connection.request("dismiss", id_=0)
        snapshot = connection.request(
            "reschedule", id_=0, end_time=Datetime.model_dump(past)
        )
        assert snapshot["items"][0]["state"] == "active"
        assert snapshot["notifications"][0]["missed"]

    def test_restart_notifies_after_dismissal(
        self, connection: Client
    ) -> None:
        connection.request("timer", duration=0.05)
        next_event(connection)
        connection.request("dismiss", id_=0)
        connection.request("restart", id_=0)
        assert next_event(connection)["notifications"]


class TestServerRecovery:
    def test_missed_deadline_preserves_status_and_dismissal_survives_restart(
        self, tmp_path: pathlib.Path, now: datetime.datetime
    ) -> None:
        state = UserData()
        state.add_alarm(
            end_time=now - datetime.timedelta(days=1000), name="Missed"
        )
        path = tmp_path / "state.json"
        path.write_text(state.model_dump_json(), encoding="utf-8")
        first = Server(directory=tmp_path)
        try:
            assert first.user_data.get(0).state == State.ACTIVE
            snapshot = first.snapshot()
            assert snapshot["notifications"][0]["missed"]
            first.user_data.get(0).dismiss(utc_now())
            first.save()
        finally:
            first.close()
        second = Server(directory=tmp_path)
        try:
            assert second.snapshot()["notifications"] == []
            assert second.user_data.get(0).state == State.ACTIVE
        finally:
            second.close()

    def test_paused_alarm_resume_notifies_without_status_change(
        self, tmp_path: pathlib.Path
    ) -> None:
        now = utc_now()
        state = UserData()
        alarm = state.add_alarm(end_time=now - datetime.timedelta(hours=1))
        alarm.pause(now - datetime.timedelta(hours=2))
        (tmp_path / "state.json").write_text(
            state.model_dump_json(), encoding="utf-8"
        )
        service = Server(directory=tmp_path)
        worker = threading.Thread(target=service.run)
        worker.start()
        try:
            with Client(directory=tmp_path) as connection:
                assert connection.snapshot["notifications"] == []
                snapshot = connection.request("resume", id_=0)
                assert snapshot["items"][0]["state"] == "active"
                assert snapshot["notifications"][0]["missed"]
        finally:
            service.stop()
            worker.join(timeout=5)
            assert not worker.is_alive()


class TestTransport:
    def test_fragmented_and_coalesced_requests(self, service: Server) -> None:
        with connect_socket(service.directory) as sock:
            first = encode({"request_id": 1, "command": "status"})
            second = encode({"request_id": 2, "command": "notifications"})
            sock.sendall(first[:4])
            sock.sendall(first[4:] + second)
            decoder = Decoder()
            replies = []  # type: List[Dict[str, Any]]
            while len(replies) < 2:
                replies.extend(decoder.feed(sock.recv(65536)))
            assert [reply["request_id"] for reply in replies] == [1, 2]

    @pytest.mark.parametrize("frame", [b"invalid\n", b"[]\n", b"\xff\n"])
    def test_malformed_frame_disconnects_only_sender(
        self, service: Server, connection: Client, frame: bytes
    ) -> None:
        with connect_socket(service.directory) as sock:
            sock.sendall(frame)
            assert sock.recv(1) == b""
        assert connection.request("status")["items"] == []


class TestAutomaticStartup:
    def test_concurrent_clients_start_one_server(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        processes = []  # type: List[subprocess.Popen[bytes]]
        original = subprocess.Popen

        def launch(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
            process = original(  # pylint: disable=consider-using-with
                *args, **kwargs
            )  # type: subprocess.Popen[bytes]
            processes.append(process)
            return process

        monkeypatch.setattr("bonipy35.alarm.client.subprocess.Popen", launch)
        clients = []  # type: List[Client]
        try:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=3
            ) as executor:
                clients = list(
                    executor.map(
                        lambda _: Client(directory=tmp_path), range(3)
                    )
                )
            assert len(processes) == 1
            for connection in clients:
                connection.request("timer", duration=60)
            assert [
                item["id_"] for item in clients[0].request("status")["items"]
            ] == [0, 1, 2]
            clients[0].request("shutdown")
            assert processes[0].wait(timeout=5) == 0
            assert not (tmp_path / "socket").exists()
        finally:
            for connection in clients:
                connection.close()
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)

    def test_startup_failure_reports_corrupt_state(
        self, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "state.json").write_text("broken", encoding="utf-8")
        with pytest.raises(RuntimeError):
            ensure_server(tmp_path)

    def test_cli_module_through_dispatcher(self, service: Server) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "bonipy35.alarm",
                "cli",
                "--directory",
                str(service.directory),
                "timer",
                "1m",
                "--name",
                "Tea",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "Tea" in result.stdout
        failed = subprocess.run(
            [
                sys.executable,
                "-m",
                "bonipy35.alarm",
                "cli",
                "--directory",
                str(service.directory),
                "resume",
                "999",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
            check=False,
        )
        assert failed.returncode == 1


class TestDeadlineClock:
    def test_deadline_readiness_and_disarm(self) -> None:
        timer = DeadlineClock()
        try:
            timer.consume()  # EAGAIN before an expiry is harmless.
            with selectors.DefaultSelector() as selector:
                selector.register(timer.fd, selectors.EVENT_READ)
                timer.arm(utc_now() + datetime.timedelta(milliseconds=10))
                assert selector.select(timeout=2)
                timer.consume()
                timer.arm(None)
                assert not selector.select(timeout=0)
                timer.arm(
                    datetime.datetime(
                        1970, 1, 1, tzinfo=datetime.timezone.utc
                    )
                )
                assert selector.select(timeout=2)
                timer.consume()
        finally:
            timer.close()


class TestPaths:
    def test_directory_created_private(self, tmp_path: pathlib.Path) -> None:
        directory = prepare_directory(tmp_path / "instance")
        assert directory.is_dir()
        assert directory.stat().st_mode & 0o077 == 0
        assert prepare_directory(directory) == directory

    def test_public_directory_rejected(self, tmp_path: pathlib.Path) -> None:
        tmp_path.chmod(0o755)
        with pytest.raises(ValueError, match="0700"):
            prepare_directory(tmp_path)

    def test_default_directory(self) -> None:
        assert default_directory().parts[-2:] == ("bonipy35", "alarm")


class TestShell:
    def test_pasted_commands_and_eof(self, service: Server) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "bonipy35.alarm",
                "cmd",
                "--directory",
                str(service.directory),
            ],
            input="timer 1m --name Tea\nstatus\nquit\n",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.count("Tea") >= 2

    def test_final_line_without_newline(self, service: Server) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "bonipy35.alarm",
                "cmd",
                "--directory",
                str(service.directory),
            ],
            input="timer 1m --name Tea",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "Tea" in result.stdout


class TestTerminalInterface:
    def test_real_terminal_renders_and_quits(self, service: Server) -> None:
        master, slave = pty.openpty()
        try:
            fcntl.ioctl(
                slave, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 100, 0, 0)
            )
            with subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "bonipy35.alarm",
                    "tui",
                    "--directory",
                    str(service.directory),
                ],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                env=dict(os.environ, TERM="xterm"),
            ) as process:
                try:
                    output = b""
                    deadline = time.monotonic() + 5
                    with selectors.DefaultSelector() as selector:
                        selector.register(master, selectors.EVENT_READ)
                        while b"q quit" not in output:
                            assert selector.select(
                                timeout=max(0, deadline - time.monotonic())
                            ), output
                            output += os.read(master, 65536)
                    os.write(master, b"q")
                    assert process.wait(timeout=5) == 0, output
                finally:
                    if process.poll() is None:
                        process.terminate()
        finally:
            os.close(master)
            os.close(slave)
