#!/usr/bin/env python3

# Standard libraries.
import argparse
import functools
import http.server
import inspect
import pathlib
import socketserver
import sys


module_path = pathlib.Path(inspect.getsourcefile(lambda: None) or ".")


def parse_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser()
    command_parsers = argument_parser.add_subparsers(dest="command", required=True)

    command_parsers.add_parser("run")

    serve_parser = command_parsers.add_parser("serve")
    serve_parser.add_argument("--port", default=8000, type=int)
    arguments = argument_parser.parse_args()
    return arguments


def serve(arguments: argparse.Namespace) -> int:
    server_address = ("", arguments.port)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=module_path.parent
    )
    with socketserver.TCPServer(server_address, handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass  # Graceful exit to not block port.
    return 0


def run() -> int:
    from . import hello  # pylint: disable=import-outside-toplevel

    return hello.main()


def main() -> int:
    arguments = parse_arguments()
    command = arguments.command
    if command == "serve":
        return serve(arguments)
    if command == "run":
        return run()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
