#!/usr/bin/env python3
"""Serve the syncpick page and its API on localhost."""

# Standard libraries.
import binascii
import datetime
import hmac
import http.server
import json
import logging
import os
import pathlib
import selectors
import signal
import socket
import socketserver
import sys
import typing
import urllib.parse

from typing import Callable, Dict, List, Union

# Internal modules.
from .compare import Entry, Side, compare
from .rc import Daemon, RcError
from .runner import RcloneError, argument_parser, runner_from_arguments
from .transfer import Direction, copy_files

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


def side_json(side: Union[None, Side]) -> Union[None, Dict[str, object]]:
    """Describe a side for JSON, with its time in UTC to microseconds."""
    if side is None:
        return None
    modified = side.modified.astimezone(datetime.timezone.utc)
    return {
        "size": side.size,
        "modified": modified.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    }


def entry_json(entry: Entry) -> Dict[str, object]:
    """Describe an entry for JSON; ``state`` is a name such as ``left_only``."""
    return {
        "path": entry.path,
        "state": entry.state.name.lower(),
        "left": side_json(entry.left),
        "right": side_json(entry.right),
    }


def locations(body: object) -> Union[None, Dict[str, str]]:
    """Return ``left`` and ``right`` of a request body if both are strings."""
    if not isinstance(body, dict):
        return None
    left = body.get("left")
    right = body.get("right")
    if not isinstance(left, str) or not isinstance(right, str):
        return None
    return {"left": left, "right": right}


def copy_request(
    body: object,
) -> Union[None, typing.Tuple[str, str, List[str], Direction]]:
    """Return locations, paths and direction of a copy request if valid."""
    paths = locations(body)
    if paths is None:
        return None
    body = typing.cast(Dict[str, object], body)
    picked = body.get("paths")
    if not isinstance(picked, list) or not all(
        isinstance(path, str) for path in picked
    ):
        return None
    try:
        direction = Direction(body.get("direction"))
    except ValueError:
        return None
    return (
        paths["left"],
        paths["right"],
        typing.cast(List[str], picked),
        direction,
    )


def add_routes(server: Server, daemon: Daemon) -> None:
    """Serve the API on ``server``, sending rclone requests to ``daemon``."""

    def compare_route(handler: Handler, body: object) -> None:
        paths = locations(body)
        if paths is None:
            handler.send_json_error(400, "Expected left and right as strings")
            return
        try:
            entries = compare(daemon, paths["left"], paths["right"])
        except RcError as error:
            handler.send_json_error(502, str(error))
            return
        handler.send_json(
            200, {"entries": [entry_json(entry) for entry in entries]}
        )

    def copy_route(handler: Handler, body: object) -> None:
        request = copy_request(body)
        if request is None:
            handler.send_json_error(
                400,
                "Expected left and right as strings, paths as a list of"
                " strings, and direction as left-to-right or right-to-left",
            )
            return
        left, right, paths, direction = request
        # One line per file as it finishes; the connection ends the stream.
        handler.send_response(200)
        handler.send_header("Content-Type", "application/x-ndjson")
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        results = copy_files(daemon, left, right, paths, direction=direction)
        try:
            for result in results:
                line = json.dumps(
                    {"path": result.path, "error": result.error}
                )
                handler.wfile.write(line.encode("utf-8") + b"\n")
        except ConnectionError:
            # The page went away, so copy nothing more.
            _logger.debug("Copy stopped: client disconnected.")
        finally:
            results.close()

    server.routes["/api/compare"] = compare_route
    server.routes["/api/copy"] = copy_route


def page_url(server: Server, *, left: str = "", right: str = "") -> str:
    """The page address, with ``left`` and ``right`` to fill in if given."""
    query = [("left", left), ("right", right)]
    extra = urllib.parse.urlencode([item for item in query if item[1]])
    return server.url + ("&" + extra if extra else "")


class Waker:
    """A socket pair: writing to one end wakes a selector on the other.

    ``signal.set_wakeup_fd(waker.writer_fileno)`` makes signals write to it
    as they arrive, so Ctrl+C wakes a waiting selector on Windows too.
    """

    def __init__(self) -> None:
        self._reader, self._writer = socket.socketpair()
        self._reader.setblocking(False)
        self._writer.setblocking(False)
        self.stopped = False

    def __enter__(self) -> "Waker":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def writer_fileno(self) -> int:
        return self._writer.fileno()

    def fileno(self) -> int:
        return self._reader.fileno()

    def stop(self) -> None:
        """Make ``serve`` return, from any thread."""
        self.stopped = True
        try:
            self._writer.send(b"\0")
        except BlockingIOError:
            pass  # Already full, so a wakeup is pending.

    def drain(self) -> None:
        # Any bytes left wake the selector again and are drained then.
        try:
            self._reader.recv(4096)
        except BlockingIOError:
            pass

    def close(self) -> None:
        self._reader.close()
        self._writer.close()


def serve(server: Server, waker: Waker) -> None:
    """Handle requests until ``waker`` is stopped, waiting without timeouts."""
    with selectors.DefaultSelector() as selector:
        selector.register(server, selectors.EVENT_READ)
        selector.register(waker, selectors.EVENT_READ)
        while True:
            for key, _ in selector.select():
                if key.fileobj is waker:
                    # A signal's handler, if any, runs after this returns.
                    waker.drain()
                    if waker.stopped:
                        return
                else:
                    server.handle_request()


def main(argv: Union[None, List[str]] = None) -> int:
    """Serve the syncpick page on localhost until Ctrl+C.

    Prints the page address, which includes this run's token.
    """
    parser = argument_parser(description=typing.cast(str, main.__doc__))
    parser.add_argument(
        "left", nargs="?", default="", help="rclone path to fill in"
    )
    parser.add_argument(
        "right", nargs="?", default="", help="rclone path to fill in"
    )
    parser.add_argument(
        "--port", type=int, default=0, help="port (default: any free one)"
    )
    arguments = parser.parse_args((sys.argv if argv is None else argv)[1:])
    try:
        with Daemon(
            runner_from_arguments(arguments)
        ) as daemon, Waker() as waker:
            # Servers are context managers only from Python 3.6.
            server = Server(port=arguments.port)
            try:
                add_routes(server, daemon)
                print(
                    "Open:",
                    page_url(
                        server, left=arguments.left, right=arguments.right
                    ),
                )
                print("Press Ctrl+C to stop.", flush=True)
                previous = signal.set_wakeup_fd(waker.writer_fileno)
                try:
                    serve(server, waker)
                except KeyboardInterrupt:
                    pass
                finally:
                    signal.set_wakeup_fd(previous)
            finally:
                server.server_close()
    except (OSError, RcError, RcloneError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
