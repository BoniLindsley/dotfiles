#!/usr/bin/env python3

# Standard libraries.
import argparse
import importlib
import logging
import sys

from typing import List, Sequence, Union

# Internal modules.
from . import logging_ext

_logger = logging.getLogger(__name__)


def run_subcommand(
    *, command: str, package: str, remaining_arguments: List[str]
) -> int:
    """Forward request to argument parser in submodules."""

    try:
        submodule = importlib.import_module(package + "." + command)
    except ImportError:
        _logger.error("Command is not known: %s", command)
        return 1

    try:
        submodule_main = submodule.main
    except AttributeError:
        try:
            submodule = importlib.import_module(
                package + "." + command + ".__main__"
            )
        except ImportError:
            _logger.error("Command has no entry point: %s", command)
            return 1

        try:
            submodule_main = submodule.main
        except AttributeError:
            _logger.error("Command not implemented: %s", command)
            return 1

    argv = [command] + remaining_arguments
    return submodule_main(argv)  # type: ignore[no-any-return]


def subcommand_main(
    argv: Union[None, List[str]] = None,
    *,
    package: str,
    choices: Sequence[str],
    description: str = "Entry point for subcommands."
) -> int:
    """Parse arguments and dispatch a command from ``choices`` in ``package``.

    ``argv`` includes the program name and defaults to ``sys.argv``.
    ``description`` supplies the introductory text in command-line help.
    """
    if argv is None:
        argv = sys.argv

    logger = logging.getLogger(package)
    logging_ext.set_up_logging(logger=logger)

    parser = argparse.ArgumentParser(description=description)
    logging_ext.add_verbose_flag(parser)
    parser.add_argument("command", choices=choices)
    # Once a command is selected, its parser owns all remaining options,
    # including help and verbosity flags shared with this dispatcher.
    parser.add_argument("remaining_arguments", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(
        logger=logger, verbosity=arguments.verbosity
    )

    return run_subcommand(
        command=arguments.command,
        package=package,
        remaining_arguments=arguments.remaining_arguments,
    )
