#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging
import sys

from typing import Union


_logger = logging.getLogger(__name__)
ALL = 1
TRACE = 5
_VERBOSITY_MAP = {
    -2: logging.CRITICAL,
    -1: logging.ERROR,
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
    3: TRACE,
    4: ALL,
}
logging.addLevelName(ALL, "ALL")
logging.addLevelName(TRACE, "TRACE")


def set_logger_verbosity(
    *, logger: logging.Logger, verbosity: int
) -> None:
    minimum_verbosity = min(_VERBOSITY_MAP)
    maximum_verbosity = max(_VERBOSITY_MAP)
    verbosity = int(verbosity)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = _VERBOSITY_MAP.get(verbosity, logging.WARNING)
    logger.debug("Setting logging level to %d", logging_level)
    logger.setLevel(logging_level)


def set_up_logging(
    *, logger: logging.Logger, verbosity: Union[None, int] = None
) -> None:
    formatter = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        fmt="[{asctime}] [python/{name}] [{levelname[0]}] {message}",
        style="{",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if verbosity is not None:
        set_logger_verbosity(logger=logger, verbosity=verbosity)


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )


def parse_arguments(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_verbose_flag(parser)
    parser.add_argument("message")
    return parser.parse_args(args)


def main(argv: None | list[str] = None) -> int:
    if argv is None:
        argv = sys.argv

    arguments = parse_arguments(argv[1:])
    set_up_logging(logger=_logger, verbosity=arguments.verbosity)

    print(f"Command is {arguments.message}")

    _logger.log(ALL, "%s: Everything", ALL)
    _logger.log(TRACE, "%s: Trace", TRACE)
    _logger.debug("%s: Debug", logging.DEBUG)
    _logger.info("%s: Info", logging.INFO)
    _logger.warning("%s: Warning", logging.WARNING)
    _logger.error("%s: Error", logging.ERROR)
    _logger.critical("%s: Critical", logging.CRITICAL)

    return 0


if __name__ == "__main__":
    sys.exit(main())
