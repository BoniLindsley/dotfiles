#!/usr/bin/env python3

# Standard libraries.
import argparse
import bz2
import functools
import gzip
import http.server
import json
import logging
import lzma
import pathlib
import re
import socketserver
import sys
import tarfile
import typing
import urllib.parse

# Project modules.
from .. import contextlib_ext
from .. import logging_ext

_logger = logging.getLogger(__name__)

if typing.TYPE_CHECKING:
    Highlight = typing.TypedDict(
        "Highlight",
        {
            "end": int,
            "start": int,
        },
    )
else:
    Highlight = dict


def generate_highlights(content: bytes) -> "dict[str, list[Highlight]]":
    """Generate highlight patterns for the log content"""
    lines = content.split(b"\n")
    highlights = {
        "all": [],
        "datetime": [],
        "error": [],
        "warning": [],
        "info": [],
        "debug": [],
        "stderr": [],
        "fatal": [],
    }  # type: dict[str, list[Highlight]]

    # Regex patterns
    datetime_patterns = [
        rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",  # ISO format
        rb"\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2}",  # US format
        rb"\d{2}-\d{2}-\d{4}\s\d{2}:\d{2}:\d{2}",  # EU format
        rb"\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",  # Syslog format
    ]

    word_patterns = {
        "error": rb"(?i)\b(error|err)\b",
        "warning": rb"(?i)\b(warning|warn)\b",
        "info": rb"(?i)\b(info|information)\b",
        "debug": rb"(?i)\b(debug|dbg)\b",
        "stderr": rb"(?i)\b(stderr)\b",
        "fatal": rb"(?i)\b(fatal|critical|crit)\b",
    }

    char_offset = 0
    for line in lines:
        line_start = char_offset

        # Find datetime patterns
        for pattern in datetime_patterns:
            for match in re.finditer(pattern, line):
                highlights["datetime"].append(
                    {
                        "start": line_start + match.start(),
                        "end": line_start + match.end(),
                    }
                )

        # Find word patterns
        for category, pattern in word_patterns.items():
            for match in re.finditer(pattern, line):
                highlights[category].append(
                    {
                        "start": line_start + match.start(),
                        "end": line_start + match.end(),
                    }
                )

        char_offset += len(line) + 1  # +1 for newline character

    return highlights


def read_file_contents(file_path: pathlib.Path) -> bytes:
    """Read file contents with appropriate decompression based on extension."""
    if file_path.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(str(file_path), "r:gz") as tar:
            members = tar.getmembers()
            if len(members) != 1:
                raise ValueError("Tar archive must contain exactly one file")
            file_obj = tar.extractfile(members[0])
            if not file_obj:
                raise ValueError("Could not extract file from tar archive")
            with file_obj:
                return file_obj.read()
    if file_path.suffix == ".gz":
        with gzip.open(str(file_path), "rb") as f:
            return f.read()
    if file_path.suffix == ".bz2":
        with bz2.open(str(file_path), "rb") as f:
            return f.read()
    if file_path.suffix == ".xz":
        with lzma.open(str(file_path), "rb") as f:
            return f.read()
    # Decode all formats consistently when constructing the response.
    with file_path.open("rb") as f:
        return f.read()


class LogRequestHandler(http.server.BaseHTTPRequestHandler):
    default_extension_map = {
        ".css": "text/css",
        ".html": "text/html",
        ".js": "application/javascript",
    }

    def __init__(
        self,
        *args: typing.Any,
        log_directory: pathlib.Path,
        static_directory: pathlib.Path,
        **kwargs: typing.Any
    ) -> None:
        self.path = ""
        self.extension_map = self.default_extension_map.copy()
        self.log_directory = log_directory
        self.static_directory = static_directory
        super().__init__(*args, **kwargs)

    def check_request_path(
        self, file_path: pathlib.Path
    ) -> "None | pathlib.Path":
        # Resolve symlinks before checking containment in the configured root.
        try:
            root = self.log_directory.resolve()
            file_path = (root / file_path).resolve()
            file_path.relative_to(root)
            if not file_path.is_file():
                return None
        except (OSError, RuntimeError, ValueError):
            return None
        return file_path

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        url = urllib.parse.urlparse(self.path)
        url_path = url.path

        if url_path == "/api/log":
            params = urllib.parse.parse_qs(url.query)
            paths = params.get("path", [])
            if not paths:
                self.send_json_error(400, "Expected a non-empty path")
                return
            self.send_requested_log(paths[0])
            return

        if url_path in {"/", "/index.html"}:
            url_path = "/log_viewer.html"
        if url_path not in {
            "/log_viewer.html",
            "/log_viewer.js",
            "/log_viewer.css",
        }:
            self.send_error(404, "File not found")
            return

        file_path = self.static_directory / url_path[1:]
        try:
            content = file_path.read_bytes()
        except OSError:
            self.send_error(404, "File not found")
            return

        content_type = self.extension_map.get(file_path.suffix, "text/plain")

        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        if urllib.parse.urlparse(self.path).path != "/api/log":
            self.send_json_error(404, "File not found")
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.send_json_error(400, "Invalid Content-Length")
            return
        if content_length < 0:
            self.send_json_error(400, "Invalid Content-Length")
            return
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except (ValueError, UnicodeError):
            self.send_json_error(400, "Invalid JSON")
            return
        if not isinstance(data, dict):
            self.send_json_error(400, "Expected a JSON object")
            return
        self.send_requested_log(data.get("path"))

    def send_requested_log(self, path: typing.Any) -> None:
        if not isinstance(path, str) or not path or "\0" in path:
            self.send_json_error(400, "Expected a non-empty path")
            return
        file_path = self.check_request_path(pathlib.Path(path))
        if file_path is None:
            self.send_json_error(404, "File not found")
            return
        self.send_log_response(file_path)

    def send_log_response(self, file_path: pathlib.Path) -> None:
        # Read the log file
        try:
            content = read_file_contents(file_path)
            text = content.decode("utf-8")
        except (
            OSError,
            EOFError,
            ValueError,
            lzma.LZMAError,
            tarfile.TarError,
        ):
            self.send_json_error(500, "Error reading file")
            return

        # Generate highlighting data
        highlights = generate_highlights(content)

        response = {
            "content": text,
            "highlights": highlights,
            "file_path": str(file_path),
        }

        self.send_json_response(200, response)

    def send_json_error(self, code: int, message: str) -> None:
        self.send_json_response(code, {"error": message})

    def send_json_response(
        self, code: int, data: "dict[str, typing.Any]"
    ) -> None:
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = json.dumps(data)
        self.wfile.write(response.encode("utf-8"))


def run(*, log_directory: pathlib.Path, port: int) -> int:
    log_directory = log_directory.resolve()
    _logger.info("Serving log viewer for logs at %s", log_directory)

    static_directory = pathlib.Path(__file__).resolve().parent / "static"
    handler = functools.partial(
        LogRequestHandler,
        log_directory=log_directory,
        static_directory=static_directory,
    )

    _logger.info("Serving log viewer at http://localhost:%s", port)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    try:
        with contextlib_ext.suppress_keyboard_interrupt():
            httpd.serve_forever()
    finally:
        httpd.server_close()
    return 0


def main(argv: "None | list[str]" = None) -> int:
    """Parse command line arguments and call `run`."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(parser)
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument(
        "--directory", default=pathlib.Path(), type=pathlib.Path
    )
    arguments = parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(
        logger=_logger, verbosity=arguments.verbosity
    )

    return run(log_directory=arguments.directory, port=arguments.port)
