#!/usr/bin/env python3

# Keep this compatible with Python 3.5.

# Standard libraries.
import argparse
import functools
import http.server
import json
import os
import pathlib
import logging
import socketserver
import sys
import typing
import urllib.parse

# Project modules.
from . import contextlib_ext
from . import logging_ext
from . import inspect_ext

_logger = logging.getLogger(__name__)


class LogRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(
        self,
        *args: typing.Any,
        log_directory: pathlib.Path,
        static_directory: pathlib.Path,
        **kwargs: typing.Any
    ) -> None:
        self.path = ""
        self.log_directory = log_directory
        self.static_directory = static_directory
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        # pylint: disable=too-many-branches
        url = urllib.parse.urlparse(self.path)
        print(url)
        url_path = url.path
        url_query = urllib.parse.parse_qs(url.query)

        if url_path == "/":
            self.path = "log_viewer.html"
            print("static path", self.path)
            super().do_GET()
        elif url_path.startswith("/static/"):
            prefix = "/static/"
            file_path = (
                (self.static_directory / url_path[len(prefix) :])
                .resolve()
                .relative_to(self.static_directory)
            )
            print("path", file_path)
            if file_path.exists() and file_path.is_file():
                self.path = str(file_path)
                super().do_GET()
            else:
                self.send_error(404, "File not found")
        elif url_path == "/file":
            try:
                file_path = (self.log_directory / url_query["path"][0]).resolve()
            except FileNotFoundError:
                self.send_error(404, "File not found")
                return
            if (
                str(file_path).startswith(str(self.log_directory))
                and file_path.exists()
                and file_path.is_file()
            ):
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                with file_path.open("rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        elif url_path == "/suggest":
            suggestions = []

            try:
                query_path = url_query["path"][0]
            except KeyError:
                query_path = ""
            query_path = "./" + query_path
            current_parent, current_name = query_path.rsplit("/", maxsplit=1)

            parent = self.log_directory / current_parent
            if str(parent).startswith(str(self.log_directory)) and parent.exists():
                for entry in parent.iterdir():
                    entry_name = entry.name
                    if entry_name.startswith(current_name):
                        suggestions.append(entry_name + ("/" if entry.is_dir() else ""))

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(suggestions).encode())
        else:
            self.send_error(404, "File not found")


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
