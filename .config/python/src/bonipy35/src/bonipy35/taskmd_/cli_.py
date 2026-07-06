#!/usr/bin/env python3

# Need Python 3.5 support.
# pylint: disable=consider-using-f-string

import argparse
import logging
import sys
import typing
from typing import Generator, List, Union

# Internal modules.
from .. import logging_ext
from .. import xdg
from . import data

_logger = logging.getLogger(__name__)


def read_lines(
    *, buffer_size: Union[None, int] = None, source: typing.TextIO
) -> Generator[str, None, None]:

    default_buffer_size = 4096

    if buffer_size is None:
        buffer_size = default_buffer_size
    if buffer_size <= 0:
        return

    newlines = source.newlines or "\n"
    newlines_len_end = -len(newlines)
    while True:
        line = source.readline(buffer_size)
        # Empty line if at EOF.
        if not line:
            return
        if len(line) >= buffer_size:
            raise BufferError(
                "Line too long to fit in buffer of size {buffer_size}".format(
                    buffer_size=buffer_size
                )
            )
        # Line always has a trailing new line unless ending in EOF.
        # Check line ending of source. Strip line ending before yielding line.
        if line.endswith(newlines):
            line = line[:newlines_len_end]
        yield line


def run_status() -> int:
    app_directories = xdg.AppDirectories(
        app_name=__package__.rsplit(".", maxsplit=1)[-1]
    )

    data_path = app_directories.data_home / "default.md"
    with data_path.open(encoding="utf-8") as data_file:
        parsed_document = data.ParsedDocument.parse(list(read_lines(source=data_file)))
    parsed_document.refresh_durations()
    quicklist_items = data.get_summary_quicklist(parsed_document)
    for quicklist_item in quicklist_items:
        print(quicklist_item.text, file=sys.stdout)
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and run corresponding functions."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(parser)
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status")

    arguments = parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    command = arguments.command
    if command == "status":
        returncode = run_status()
    elif command is None:
        parser.print_help()
        return 1
    else:
        _logger.error("Unknown command: %s", command)
        returncode = 1

    return returncode


if __name__ == "__main__":
    sys.exit(main())
