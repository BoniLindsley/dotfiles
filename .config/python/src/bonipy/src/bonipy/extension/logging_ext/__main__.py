#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging
import sys


_logger = logging.getLogger(__name__)
TRACE = 5

_VERBOSITY_MAP: dict[int, int] = {
    -2: logging.CRITICAL,
    -1: logging.ERROR,
    0: logging.WARNING,
    1: logging.INFO,
    2: logging.DEBUG,
    3: TRACE,
    4: 1,
}


def initialise_logging(*, verbosity: int = 0) -> None:
    logging.addLevelName(TRACE, "TRACE")
    logging.basicConfig(level=_VERBOSITY_MAP.get(verbosity))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--verbose", "-v", action="count", help="Incrase verbosity.", default=0
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    initialise_logging(verbosity=arguments.verbose)

    _logger.log(TRACE, "Message level: TRACE")
    _logger.debug("Message level: DEBUG")
    _logger.info("Message level: INFO")
    _logger.warning("Message level: WARNING")
    _logger.error("Message level: ERROR")
    _logger.critical("Message level: CRITICAL")

    return 0


if __name__ == "__main__":
    sys.exit(main())
