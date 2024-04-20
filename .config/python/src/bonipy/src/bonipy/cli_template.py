#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging
import sys

from typing import List, Union


_logger = logging.getLogger(__name__)


def set_logger_verbosity(
    *, logger: logging.Logger, verbosity: int
) -> None:
    logging_all = 1
    logging_trace = 5
    logging.addLevelName(logging_all, "ALL")
    logging.addLevelName(logging_trace, "TRACE")
    verbosity_map = {
        -2: logging.CRITICAL,
        -1: logging.ERROR,
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
        3: logging_trace,
        4: logging_all,
    }
    minimum_verbosity = min(verbosity_map)
    maximum_verbosity = max(verbosity_map)
    verbosity = int(verbosity)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = verbosity_map.get(verbosity, logging.WARNING)
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


def parse_arguments(args: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )
    return parser.parse_args(args)


def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv

    arguments = parse_arguments(argv[1:])
    set_up_logging(logger=_logger, verbosity=arguments.verbosity)

    _logger.log(1, "%s: Everything", 1)
    _logger.log(5, "%s: Trace", 5)
    _logger.debug("%s: Debug", logging.DEBUG)
    _logger.info("%s: Info", logging.INFO)
    _logger.warning("%s: Warning", logging.WARNING)
    _logger.error("%s: Error", logging.ERROR)
    _logger.critical("%s: Critical", logging.CRITICAL)

    return 0


if __name__ == "__main__":
    sys.exit(main())
