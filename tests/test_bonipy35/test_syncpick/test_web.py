#!/usr/bin/env python3

# Standard libraries.
import http.client
import json
import logging
import pathlib
import threading
import urllib.parse

from typing import Dict, Iterator, List, Tuple, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.web import (
    STATIC_DIRECTORY,
    TOKEN_HEADER,
    Handler,
    Server,
)


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
