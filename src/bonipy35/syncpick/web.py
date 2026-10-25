#!/usr/bin/env python3
"""Serve the syncpick page and its API on localhost."""

# Standard libraries.
import binascii
import hmac
import http.server
import json
import logging
import os
import pathlib
import socketserver
import typing
import urllib.parse

from typing import Callable, Dict

_logger = logging.getLogger(__name__)

STATIC_DIRECTORY = pathlib.Path(__file__).resolve().parent / "static"

TOKEN_HEADER = "X-Syncpick-Token"

Route = Callable[["Handler", object], None]
"""Answers a POST request, given its handler and its parsed JSON body."""


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """An HTTP server on ``127.0.0.1`` requiring a per-run token.

    The page is requested with the token as the ``token`` query parameter,
    and API requests with the token in the ``X-Syncpick-Token`` header.
    Requests are handled in threads, so a long copy does not block others.
    """

    daemon_threads = True

    def __init__(
        self,
        *,
        port: int = 0,
        token: str = "",
        static_directory: pathlib.Path = STATIC_DIRECTORY
    ) -> None:
        super().__init__(("127.0.0.1", port), Handler)
        self.token = token or binascii.hexlify(os.urandom(16)).decode("ascii")
        self.static_directory = static_directory
        self.routes = {}  # type: Dict[str, Route]

    @property
    def url(self) -> str:
        """The address of the page, including the token."""
        return "http://127.0.0.1:{}/?{}".format(
            self.server_address[1],
            urllib.parse.urlencode({"token": self.token}),
        )


class Handler(http.server.BaseHTTPRequestHandler):
    @property
    def app(self) -> Server:
        """The server handling this request."""
        return typing.cast(Server, self.server)

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        url = urllib.parse.urlsplit(self.path)
        tokens = urllib.parse.parse_qs(url.query).get("token", [])
        if not self.is_authorized(tokens[0] if tokens else ""):
            self.send_json_error(403, "Missing or wrong token")
            return
        if url.path != "/":
            self.send_json_error(404, "Not found")
            return
        try:
            content = (self.app.static_directory / "index.html").read_bytes()
        except OSError:
            self.send_json_error(404, "Not found")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        if not self.is_authorized(self.headers.get(TOKEN_HEADER, "")):
            self.send_json_error(403, "Missing or wrong token")
            return
        route = self.app.routes.get(urllib.parse.urlsplit(self.path).path)
        if route is None:
            self.send_json_error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
            if length < 0:
                raise ValueError(length)
        except ValueError:
            self.send_json_error(400, "Invalid Content-Length")
            return
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeError):
            self.send_json_error(400, "Invalid JSON")
            return
        route(self, body)

    def is_authorized(self, token: str) -> bool:
        return hmac.compare_digest(
            token.encode("utf-8"), self.app.token.encode("utf-8")
        )

    def send_json(self, code: int, data: object) -> None:
        content = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def send_json_error(self, code: int, message: str) -> None:
        self.send_json(code, {"error": message})

    def log_message(self, format: str, *args: typing.Any) -> None:
        # Request lines include the page URL, so hide the token.
        message = format % args
        _logger.debug(
            "%s %s",
            self.address_string(),
            message.replace(self.app.token, "<token>"),
        )
