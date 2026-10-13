#!/usr/bin/env python3

# Standard libraries.
import argparse
import datetime

# Internal modules.
from .. import datetime_ext

from . import model


def add_mode_flags(subparser: argparse.ArgumentParser) -> None:
    mode_group = subparser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--strict", action="store_true", help="strict parsing (default)"
    )
    mode_group.add_argument(
        "--lenient", action="store_true", help="lenient parsing"
    )


def add_input_flags(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "paths",
        nargs="*",
        help="taskmd file(s) to read, in addition to any --file/--dir",
    )
    subparser.add_argument(
        "--file",
        action="append",
        dest="file",
        metavar="FILE",
        help="an explicit file to read (repeatable)",
    )
    subparser.add_argument(
        "--dir",
        dest="dir",
        metavar="DIR",
        help=(
            "recursively scan DIR (with no input, scan "
            "$XDG_DATA_HOME/bonipy35/taskmd; "
            "XDG_DATA_HOME defaults to ~/.local/share)"
        ),
    )
    subparser.add_argument(
        "--depth",
        type=int,
        default=None,
        metavar="N",
        help="limit recursive directory depth (only with --dir)",
    )


def parse_iso_date(value: str) -> datetime.date:
    try:
        return datetime_ext.parse_date(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            "{0!r} is not a valid ISO-8601 date (expected YYYY-MM-DD)".format(
                value,
            ),
        ) from error


def add_status_flag(
    subparser: argparse.ArgumentParser, *, help_text: str
) -> None:
    subparser.add_argument(
        "--status",
        action="append",
        dest="status",
        choices=list(status.name for status in model.Status),
        metavar="STATUS",
        help=help_text,
    )
