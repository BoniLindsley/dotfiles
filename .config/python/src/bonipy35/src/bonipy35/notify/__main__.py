#!/usr/bin/env python3

# Standard libraries.
import argparse
import importlib
import logging
import sys

# Internal modules.
from .. import logging_ext

_logger = logging.getLogger(__name__ if __name__ != "__main__" else __package__)


def run(*, command: str, package: str, remaining_arguments: "list[str]") -> int:
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
            submodule = importlib.import_module(package + "." + command + ".__main__")
        except ImportError:
            _logger.error("Command has no entry point: %s", command)
            return 1

        try:
            submodule_main = submodule.main
        except AttributeError:
            _logger.error("Command not implemented: %s", command)
            return 1

    remaining_arguments.insert(0, command)
    return submodule_main(remaining_arguments)  # type: ignore[no-any-return]


def main(argv: "None | list[str]" = None) -> int:
    """Parse command line arguments and call `run`."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    parser = argparse.ArgumentParser(description="Entry point for subcommands.")
    logging_ext.add_verbose_flag(parser)
    parser.add_argument("command", choices=("cli", "daemon"))
    arguments, remaining_arguments = parser.parse_known_args(argv[1:])

    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run(
        command=arguments.command,
        package=__package__,
        remaining_arguments=remaining_arguments,
    )


if __name__ == "__main__":
    sys.exit(main())
