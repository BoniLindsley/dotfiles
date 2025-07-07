#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging
import sys


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
    *,
    logger: logging.Logger,
    verbosity: int,
    verbosity_map: "None | dict[int, int]" = None
) -> None:
    if not verbosity_map:
        verbosity_map = _VERBOSITY_MAP

    minimum_verbosity = min(verbosity_map)
    maximum_verbosity = max(verbosity_map)
    verbosity = int(verbosity)
    verbosity = min(maximum_verbosity, verbosity)
    verbosity = max(minimum_verbosity, verbosity)
    logging_level = verbosity_map.get(verbosity, logging.WARNING)
    logger.debug("Setting logging level to %d", logging_level)
    logger.setLevel(logging_level)


def set_up_logging(*, logger: logging.Logger) -> None:
    formatter = logging.Formatter(
        datefmt="%Y-%m-%d %H:%M:%S",
        fmt="[{asctime}] [python/{name}] [{levelname[0]}] {message}",
        style="{",
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        dest="verbosity",
        help="Incrase verbosity.",
    )


def parse_arguments(args: "list[str]") -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    add_verbose_flag(parser)
    parser.add_argument("message")
    return parser.parse_args(args)


def main(argv: "None | list[str]" = None) -> int:
    if argv is None:
        argv = sys.argv

    set_up_logging(logger=_logger)

    arguments = parse_arguments(argv[1:])
    set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    print("Command is", arguments.message)

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
