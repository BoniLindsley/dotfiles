#!/usr/bin/env python3

# Standard libraries.
import datetime
import http.client
import json
import logging
import pathlib
import shutil
import sys
import threading
import typing
import urllib.parse

from typing import Dict, Iterator, List, Tuple, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.compare import Entry, Side, State
from bonipy35.syncpick.rc import Daemon, RcError
from bonipy35.syncpick.runner import Runner
from bonipy35.syncpick.web import (
    STATIC_DIRECTORY,
    TOKEN_HEADER,
    Handler,
    Server,
    add_routes,
    entry_json,
    locations,
    side_json,
)

RCLONE = shutil.which("rclone")


@pytest.fixture(name="server")
def fixture_server(tmp_path: pathlib.Path) -> Iterator[Server]:
    (tmp_path / "index.html").write_text("<p>page</p>")
    server = Server(token="secret", static_directory=tmp_path)
    # Polls only to notice shutdown() quickly; see T-017 for serving.
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.01}
    )
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def request(
    server: Server,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    headers: Union[None, Dict[str, str]] = None
) -> Tuple[int, Dict[str, str], bytes]:
    connection = http.client.HTTPConnection(
        "127.0.0.1", server.server_address[1]
    )
    try:
        connection.request(
            method, path, body=body or None, headers=headers or {}
        )
        response = connection.getresponse()
        return (
            response.status,
            {name.lower(): value for name, value in response.getheaders()},
            response.read(),
        )
    finally:
        connection.close()


def post(
    server: Server, path: str, body: bytes, *, token: str = "secret"
) -> Tuple[int, object]:
    status, _, content = request(
        server, "POST", path, body=body, headers={TOKEN_HEADER: token}
    )
    return status, json.loads(content.decode("utf-8"))


class TestServer:
    def test_binds_localhost(self, server: Server) -> None:
        assert server.server_address[0] == "127.0.0.1"
        assert server.server_address[1] != 0

    def test_url(self, server: Server) -> None:
        assert server.url == "http://127.0.0.1:{}/?token=secret".format(
            server.server_address[1]
        )

    def test_generates_token(self) -> None:
        with Server() as first, Server() as second:
            assert len(first.token) == 32
            assert first.token != second.token
            assert urllib.parse.parse_qs(
                urllib.parse.urlsplit(first.url).query
            ) == {"token": [first.token]}

    def test_default_static_directory(self) -> None:
        assert (STATIC_DIRECTORY / "index.html").is_file()


class TestDoGet:
    def test_page(self, server: Server) -> None:
        status, headers, content = request(server, "GET", "/?token=secret")
        assert status == 200
        assert content == b"<p>page</p>"
        assert headers["content-type"] == "text/html; charset=utf-8"
        assert headers["referrer-policy"] == "no-referrer"
        assert headers["cache-control"] == "no-store"

    @pytest.mark.parametrize(
        "path", ["/", "/?token=", "/?token=wrong", "/?token=secretx"]
    )
    def test_rejects_token(self, server: Server, path: str) -> None:
        status, _, content = request(server, "GET", path)
        assert status == 403
        assert b"secret" not in content

    def test_rejects_header_token(self, server: Server) -> None:
        # Only the page URL carries the token for GET.
        status, _, _ = request(
            server, "GET", "/", headers={TOKEN_HEADER: "secret"}
        )
        assert status == 403

    def test_unknown_path(self, server: Server) -> None:
        status, _, _ = request(server, "GET", "/other?token=secret")
        assert status == 404

    def test_missing_page(
        self, server: Server, tmp_path: pathlib.Path
    ) -> None:
        (tmp_path / "index.html").unlink()
        status, _, _ = request(server, "GET", "/?token=secret")
        assert status == 404


class TestDoPost:
    @pytest.fixture(name="received")
    def fixture_received(self, server: Server) -> List[object]:
        received = []  # type: List[object]

        def echo(handler: Handler, body: object) -> None:
            received.append(body)
            handler.send_json(200, {"echo": body})

        server.routes["/api/echo"] = echo
        return received

    def test_dispatches_route(
        self, server: Server, received: List[object]
    ) -> None:
        assert post(server, "/api/echo", b'{"a": [1, "\\u00fc"]}') == (
            200,
            {"echo": {"a": [1, "ü"]}},
        )
        assert received == [{"a": [1, "ü"]}]

    @pytest.mark.parametrize("token", ["", "wrong"])
    def test_rejects_token(
        self, server: Server, received: List[object], token: str
    ) -> None:
        assert post(server, "/api/echo", b"{}", token=token) == (
            403,
            {"error": "Missing or wrong token"},
        )
        assert not received

    def test_rejects_query_token(
        self, server: Server, received: List[object]
    ) -> None:
        status, _, _ = request(server, "POST", "/api/echo?token=secret")
        assert status == 403
        assert not received

    def test_unknown_route(self, server: Server) -> None:
        assert post(server, "/api/missing", b"{}") == (
            404,
            {"error": "Not found"},
        )

    @pytest.mark.parametrize(
        ("body", "message"),
        [(b"{", "Invalid JSON"), (b"\xff", "Invalid JSON")],
    )
    def test_invalid_body(
        self,
        server: Server,
        received: List[object],
        body: bytes,
        message: str,
    ) -> None:
        assert post(server, "/api/echo", body) == (400, {"error": message})
        assert not received

    @pytest.mark.parametrize("length", ["", "x", "-1"])
    def test_invalid_length(
        self, server: Server, received: List[object], length: str
    ) -> None:
        headers = {TOKEN_HEADER: "secret"}
        if length:
            headers["Content-Length"] = length
        connection = http.client.HTTPConnection(
            "127.0.0.1", server.server_address[1]
        )
        try:
            connection.putrequest("POST", "/api/echo")
            for name, value in headers.items():
                connection.putheader(name, value)
            connection.endheaders()
            response = connection.getresponse()
            assert response.status == 400
            assert json.loads(response.read().decode("utf-8")) == {
                "error": "Invalid Content-Length"
            }
        finally:
            connection.close()
        assert not received


class TestLogMessage:
    def test_hides_token(
        self, server: Server, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.DEBUG, logger="bonipy35.syncpick.web"):
            request(server, "GET", "/?token=secret")
        assert "GET /?token=<token>" in caplog.text
        assert "secret" not in caplog.text


class FakeDaemon(Daemon):
    """Lists ``left`` with one file and checks it as left only."""

    def __init__(self) -> None:
        super().__init__(Runner(executable=sys.executable))
        self.error = None  # type: Union[None, RcError]

    def call(
        self, path: str, parameters: Union[None, Dict[str, object]] = None
    ) -> Dict[str, object]:
        if self.error is not None:
            raise self.error
        parameters = parameters or {}
        if path == "operations/check":
            return {"combined": ["+ a"]}
        if parameters["fs"] == "left":
            return {
                "list": [
                    {
                        "Path": "a",
                        "Size": 1,
                        "ModTime": "2026-10-25T01:02:03Z",
                    }
                ]
            }
        return {"list": []}


@pytest.fixture(name="daemon")
def fixture_daemon(server: Server) -> FakeDaemon:
    daemon = FakeDaemon()
    add_routes(server, daemon)
    return daemon


class TestSideJson:
    def test_utc_with_microseconds(self) -> None:
        offset = datetime.timezone(datetime.timedelta(hours=-1))
        side = Side(
            size=3,
            modified=datetime.datetime(
                2026, 10, 25, 1, 2, 3, 45, tzinfo=offset
            ),
        )
        assert side_json(side) == {
            "size": 3,
            "modified": "2026-10-25T02:02:03.000045Z",
        }

    def test_missing(self) -> None:
        assert side_json(None) is None


class TestEntryJson:
    def test_state_name(self) -> None:
        assert entry_json(
            Entry(path="p", state=State.RIGHT_ONLY, left=None, right=None)
        ) == {"path": "p", "state": "right_only", "left": None, "right": None}


class TestLocations:
    def test_valid(self) -> None:
        assert locations({"left": "a", "right": "b:", "other": 1}) == {
            "left": "a",
            "right": "b:",
        }

    @pytest.mark.parametrize(
        "body", [[], {"left": "a"}, {"left": "a", "right": 1}, {"right": "b"}]
    )
    def test_invalid(self, body: object) -> None:
        assert locations(body) is None


class TestCompareRoute:
    @pytest.mark.usefixtures("daemon")
    def test_entries(self, server: Server) -> None:
        assert post(
            server, "/api/compare", b'{"left": "left", "right": "right"}'
        ) == (
            200,
            {
                "entries": [
                    {
                        "path": "a",
                        "state": "left_only",
                        "left": {
                            "size": 1,
                            "modified": "2026-10-25T01:02:03.000000Z",
                        },
                        "right": None,
                    }
                ]
            },
        )

    @pytest.mark.usefixtures("daemon")
    def test_invalid_body(self, server: Server) -> None:
        assert post(server, "/api/compare", b'{"left": "left"}') == (
            400,
            {"error": "Expected left and right as strings"},
        )

    def test_rclone_error(self, server: Server, daemon: FakeDaemon) -> None:
        daemon.error = RcError(
            "no remote", path="operations/list", status=500
        )
        assert post(
            server, "/api/compare", b'{"left": "x:", "right": "y"}'
        ) == (502, {"error": "no remote"})


@pytest.mark.integration
@pytest.mark.skipif(RCLONE is None, reason="Executable not found: rclone")
class TestRealCompareRoute:
    def test_entries(self, server: Server, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "rclone.conf"
        config.write_text("")
        left = tmp_path / "left"
        right = tmp_path / "right"
        (left / "d").mkdir(parents=True)
        right.mkdir()
        (left / "d" / "a file").write_text("a")
        (right / "b").write_text("bb")
        with Daemon(Runner(config=config)) as daemon:
            add_routes(server, daemon)
            status, body = post(
                server,
                "/api/compare",
                json.dumps({"left": str(left), "right": str(right)}).encode(
                    "utf-8"
                ),
            )
        assert status == 200
        entries = typing.cast(
            List[Dict[str, typing.Any]],
            typing.cast(Dict[str, object], body)["entries"],
        )
        assert [(entry["path"], entry["state"]) for entry in entries] == [
            ("b", "right_only"),
            ("d/a file", "left_only"),
        ]
        assert entries[0]["left"] is None
        assert entries[1]["left"]["size"] == 1
        assert entries[1]["left"]["modified"].endswith("Z")
