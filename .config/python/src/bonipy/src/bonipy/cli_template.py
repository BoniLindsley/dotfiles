#!/usr/bin/env python3

# Keep this Python 3.5 compatible for Debian 9 support.

# Standard libraries.
import argparse
import contextlib
import logging
import sys

# TODO(Python 3.9): Use collections.abc version.
from typing import Generator

# TODO(Python 3.9): Use builtin.
from typing import List

# TODO(Python 3.10): Use | instead of Union.
from typing import Union

# ========
# Common code
# ========


_logger = logging.getLogger(__name__)
LOGGING_ALL = 1
LOGGING_TRACE = 5


def set_up_logging(*, logger: logging.Logger) -> None:
    logging.addLevelName(LOGGING_ALL, "ALL")
    logging.addLevelName(LOGGING_TRACE, "TRACE")

    formatter = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        fmt="[{asctime}] [python/{name}] [{levelname[0]}] {message}",
        style="{",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def set_logger_verbosity(
    *, logger: logging.Logger, verbosity: Union[None, int] = None
) -> None:
    if verbosity is None:
        verbosity = 0

    verbosity_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: LOGGING_TRACE,
        4: LOGGING_ALL,
    }
    minimum_verbosity = min(verbosity_map)
    maximum_verbosity = max(verbosity_map)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = verbosity_map.get(verbosity, logging.WARNING)
    logger.setLevel(logging_level)


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )


@contextlib.contextmanager
def suppress_keyboard_interrupt() -> Generator[None, None, None]:
    try:
        yield
    except KeyboardInterrupt:
        # Clear line echo-ing "^C".
        print()


# ========
# Actual implementation
# ========


def run() -> int:
    _logger.log(1, "%s: Everything", 1)
    _logger.log(5, "%s: Trace", 5)
    _logger.debug("%s: Debug", logging.DEBUG)
    _logger.info("%s: Info", logging.INFO)
    _logger.warning("%s: Warning", logging.WARNING)
    _logger.error("%s: Error", logging.ERROR)
    _logger.critical("%s: Critical", logging.CRITICAL)
    return 0


def parse_arguments(args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_verbose_flag(parser)
    return parser.parse_args(args)


@suppress_keyboard_interrupt()
def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    set_up_logging(logger=_logger)

    arguments = parse_arguments(argv[1:])
    set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run()


if __name__ == "__main__":
    sys.exit(main())
