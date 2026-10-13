#!/usr/bin/env python3

# Standard libraries.
import pathlib

from typing import Any, Dict, List
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.client import Client
from bonipy35.alarm.protocol import encode


@pytest.fixture(name="sockets")
def fixture_sockets() -> List[Mock]:
    return [Mock(), Mock()]


class TestClientHandshake:
    @pytest.mark.parametrize("reset", [False, True])
    def test_lost_handshake_reconnects_before_commands(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        sockets: List[Mock],
        reset: bool,
    ) -> None:
        connector = Mock(side_effect=sockets)
        monkeypatch.setattr("bonipy35.alarm.client.ensure_server", connector)
        sockets[0].recv.return_value = b""
        if reset:
            sockets[0].recv.side_effect = ConnectionResetError()
        snapshot = {"items": [], "notifications": []}  # type: Dict[str, Any]
        sockets[1].recv.return_value = encode(
            {"request_id": 2, "snapshot": snapshot}
        )
        with Client(directory=tmp_path) as connection:
            assert connection.snapshot == snapshot
            sockets[0].close.assert_called_once_with()
            assert connector.call_count == 2
            # A mutation whose response is lost must never be replayed.
            sockets[1].recv.side_effect = ConnectionResetError()
            with pytest.raises(ConnectionResetError):
                connection.request("timer", duration=60)
            assert connector.call_count == 2
            assert sockets[1].sendall.call_count == 2
        sockets[1].close.assert_called_once_with()

    def test_repeated_handshake_failure_closes_both_sockets(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        sockets: List[Mock],
    ) -> None:
        connector = Mock(side_effect=sockets)
        monkeypatch.setattr("bonipy35.alarm.client.ensure_server", connector)
        for sock in sockets:
            sock.recv.return_value = b""
        with pytest.raises(EOFError):
            Client(directory=tmp_path)
        assert connector.call_count == 2
        for sock in sockets:
            sock.close.assert_called_once_with()

    def test_server_error_does_not_retry(
        self,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
        sockets: List[Mock],
    ) -> None:
        connector = Mock(side_effect=sockets)
        monkeypatch.setattr("bonipy35.alarm.client.ensure_server", connector)
        sockets[0].recv.return_value = encode(
            {"request_id": 1, "error": "Cannot read status"}
        )
        with pytest.raises(ValueError, match="Cannot read status"):
            Client(directory=tmp_path)
        connector.assert_called_once_with(tmp_path)
        sockets[0].close.assert_called_once_with()
