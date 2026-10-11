#!/usr/bin/env python3
"""Interactive commands with immediate server events while waiting for input."""

# Standard libraries.
import codecs
import os
import pathlib
import selectors
import shlex
import sys

from typing import List, Union

# Internal modules.
from . import cli, client


def execute_line(connection: client.Client, line: str) -> bool:
    if line.strip() in ("quit", "exit"):
        return False
    try:
        arguments = cli.make_parser().parse_args(shlex.split(line))
        if arguments.command is None:
            return True
        if arguments.command == "watch":
            cli.display(connection.snapshot)
        else:
            cli.display(
                connection.request(
                    arguments.command, **cli.request_fields(arguments)
                )
            )
        return bool(arguments.command != "shutdown")
    except (ValueError, OverflowError) as error:
        print(str(error), file=sys.stderr)
    except SystemExit:
        # argparse errors should leave the interactive session usable.
        pass
    return True


def run(directory: pathlib.Path) -> int:
    with client.Client(directory=directory) as connection:
        cli.display(connection.snapshot)
        decoder = codecs.getincrementaldecoder(
            sys.stdin.encoding or "utf-8"
        )()
        pending_input = ""
        with connection.events(), selectors.DefaultSelector() as selector:
            selector.register(connection.sock, selectors.EVENT_READ, "event")
            selector.register(sys.stdin, selectors.EVENT_READ, "input")
            print("(alarm) ", end="", flush=True)
            while True:
                if connection.buffered:
                    connection.receive()
                    cli.display(connection.snapshot)
                    continue
                for key, _mask in selector.select():
                    if key.data == "event":
                        connection.receive()
                        print()
                        cli.display(connection.snapshot)
                    else:
                        chunk = os.read(sys.stdin.fileno(), 65536)
                        pending_input += decoder.decode(
                            chunk, final=not chunk
                        )
                        while "\n" in pending_input:
                            line, pending_input = pending_input.split("\n", 1)
                            if not execute_line(connection, line):
                                return 0
                        if not chunk:
                            if pending_input:
                                execute_line(connection, pending_input)
                            return 0
                    print("(alarm) ", end="", flush=True)


def main(argv: Union[None, List[str]] = None) -> int:
    return client.interface_main(run, argv, __doc__)


if __name__ == "__main__":
    sys.exit(main())
