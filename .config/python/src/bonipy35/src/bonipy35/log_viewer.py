#!/usr/bin/env python3

# Keep this compatible with Python 3.5.

# Standard libraries.
import argparse
import bz2
import functools
import gzip
import http.server
import json
import logging
import lzma
import os
import pathlib
import re
import socketserver
import sys
import tarfile
import typing
import urllib.parse

# Project modules.
from . import contextlib_ext
from . import logging_ext
from . import inspect_ext

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
        rb"\d{4}-\d{2}-\d{2}[\s\T]\d{2}:\d{2}:\d{2}",  # ISO format
        rb"\d{2}/\d{2}/\d{4}\s\d{2}:\d{2}:\d{2}",  # US format
        rb"\d{2}-\d{2}-\d{4}\s\d{2}:\d{2}:\d{2}",  # EU format
        rb"\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}",  # Syslog format
    ]

    word_patterns = {
        "error": rb"\b(?i)(error|err)\b",
        "warning": rb"\b(?i)(warning|warn)\b",
        "info": rb"\b(?i)(info|information)\b",
        "debug": rb"\b(?i)(debug|dbg)\b",
        "stderr": rb"\b(?i)(stderr)\b",
        "fatal": rb"\b(?i)(fatal|critical|crit)\b",
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
        with tarfile.open(file_path, "r:gz") as tar:
            members = tar.getmembers()
            if len(members) != 1:
                raise ValueError("Tar archive must contain exactly one file")
            file_obj = tar.extractfile(members[0])
            if not file_obj:
                raise ValueError("Could not extract file from tar archive")
            return file_obj.read()
    if file_path.suffix == ".gz":
        with gzip.open(file_path, "rb") as f:
            return f.read()
    if file_path.suffix == ".bz2":
        with bz2.open(file_path, "rb") as f:
            return f.read()
    if file_path.suffix == ".xz":
        with lzma.open(file_path, "rb") as f:
            return f.read()
    # Read plain text as binary and let browser handle decoding
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

    def check_request_path(self, file_path: pathlib.Path) -> "None | pathlib.Path":
        if file_path is None:
            return None
        if ".." in file_path.parts:
            return None
        if not file_path.exists():
            return None
        if not file_path.is_file():
            return None
        return file_path

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        url = urllib.parse.urlparse(self.path)
        url_path = url.path

        file_path = None  # type: None | pathlib.Path
        if url_path.startswith("/api/log"):
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            try:
                file_path = pathlib.Path(params["path"][0])
            except (IndexError, KeyError):
                pass
            if file_path is not None:
                file_path = self.check_request_path(file_path)
            if file_path is not None:
                self.send_log_response(file_path)
                return

        url_path = url_path.lstrip("/")
        if url_path == "":
            url_path = "index.html"
        if url_path == "index.html":
            url_path = "log_viewer.html"

        if url_path in {"log_viewer.html", "log_viewer.js", "log_viewer.css"}:
            file_path = pathlib.Path(url_path)

        if file_path is not None:
            file_path = self.check_request_path(file_path)

        content = b""
        if file_path is not None:
            try:
                content = file_path.read_bytes()
            except FileNotFoundError:
                file_path = None

        if file_path is None:
            self.send_error(404, "File not found")
            return

        content_type = self.extension_map.get(file_path.suffix, "text/plain")

        self.send_response(200)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        if self.path != "/api/log":
            self.send_error(404, "File not found")

        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        try:
            data = json.loads(post_data.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json_error(400, "Invalid JSON")
            return

        file_path = None
        url_path = data.get("path")
        if url_path is not None:
            file_path = pathlib.Path(url_path)
        if file_path is not None:
            file_path = self.check_request_path(file_path)
        if file_path is None:
            self.send_error(404, "File not found")
            return

        self.send_log_response(file_path)

    def send_log_response(self, file_path: pathlib.Path) -> None:
        # Read the log file
        try:
            content = read_file_contents(file_path)
        except ValueError:
            self.send_json_error(500, "Error reading file")
            return

        # Generate highlighting data
        highlights = generate_highlights(content)

        response = {
            "content": content.decode("utf-8"),
            "highlights": highlights,
            "file_path": str(file_path),
        }

        self.send_json_response(200, response)

    def send_json_error(self, code: int, message: str) -> None:
        self.send_json_response(code, {"error": message})

    def send_json_response(self, code: int, data: "dict[str, typing.Any]") -> None:
        self.send_response(code)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        response = json.dumps(data)
        self.wfile.write(response.encode("utf-8"))


def run(*, log_directory: pathlib.Path, port: int) -> int:
    log_directory = log_directory.resolve()
    _logger.info("Serving log viewer for logs at %s", log_directory)

    # Python 3.5 only serves from current directory.
    last_cwd = os.getcwd()
    static_directory = inspect_ext.get_module_directory(lambda: None) / "static"
    os.chdir(str(static_directory))
    _logger.info("Setting current directory to: %s", static_directory)
    try:
        server_address = ("", port)
        handler = functools.partial(
            LogRequestHandler,
            log_directory=log_directory,
            static_directory=static_directory,
        )

        _logger.info("Serving log viewer at http://localhost:%s", port)
        httpd = socketserver.TCPServer(server_address, handler)
        try:
            with contextlib_ext.suppress_keyboard_interrupt():
                httpd.serve_forever()
        finally:
            httpd.server_close()
    finally:
        os.chdir(str(last_cwd))
    return 0


def main(argv: "None | list[str]" = None) -> int:
    """Parse command line arguments and call `run`."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(parser)
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--directory", default=pathlib.Path(), type=pathlib.Path)
    arguments = parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run(log_directory=arguments.directory, port=arguments.port)


if __name__ == "__main__":
    sys.exit(main())
