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
projects_directory = module_path.parent / "projects"


def parse_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser()
    command_parsers = argument_parser.add_subparsers(dest="command", required=True)

    command_parsers.add_parser("list")

    run_parser = command_parsers.add_parser("run")
    run_parser.add_argument("--port", default=8000, type=int)
    run_parser.add_argument("project")

    arguments = argument_parser.parse_args()
    return arguments


def list_projects() -> None:
    for project_path in projects_directory.iterdir():
        print(project_path.name)


def run(arguments: argparse.Namespace) -> None:
    server_address = ("", arguments.port)
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=projects_directory / arguments.project,
    )
    with socketserver.TCPServer(server_address, handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass  # Graceful exit to not block port.


def main() -> int:
    arguments = parse_arguments()
    command = arguments.command
    if command == "list":
        list_projects()
    elif command == "run":
        run(arguments)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
