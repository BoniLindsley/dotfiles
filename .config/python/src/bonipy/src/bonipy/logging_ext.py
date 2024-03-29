#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging
import sys


_logger = logging.getLogger(__name__)
ALL = 1
TRACE = 5

_VERBOSITY_MAP: dict[int, int] = {
    -2: logging.CRITICAL,
    -1: logging.ERROR,
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
    3: TRACE,
    4: ALL,
}


def set_up_logging(*, verbosity: int = 0) -> None:
    logging.addLevelName(TRACE, "TRACE")
    logging_level = _VERBOSITY_MAP.get(min(4, verbosity))
    logging.basicConfig(level=logging_level)
    _logger.debug("Logging level is set to %d", logging_level)


def add_verbose_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        dest="verbosity",
        help="Incrase verbosity.",
        default=0,
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
    set_up_logging(verbosity=arguments.verbosity)

    print(f"Command is {arguments.message}")

    _logger.log(1, "%s: Everything", 1)
    _logger.log(TRACE, "%s: Trace", TRACE)
    _logger.debug("%s: Debug", logging.DEBUG)
    _logger.info("%s: Info", logging.INFO)
    _logger.warning("%s: Warning", logging.WARNING)
    _logger.error("%s: Error", logging.ERROR)
    _logger.critical("%s: Critical", logging.CRITICAL)

    return 0


if __name__ == "__main__":
    sys.exit(main())
