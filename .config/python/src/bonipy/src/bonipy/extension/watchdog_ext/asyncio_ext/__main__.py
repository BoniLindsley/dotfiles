#!/usr/bin/env python3

# Standard libraries.
import argparse
import asyncio
import pathlib
import sys

# Internal modules.
from .__init__ import schedule


def parse_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("path", type=pathlib.Path)
    arguments = argument_parser.parse_args()
    return arguments


async def amain() -> int:
    arguments = parse_arguments()

    async with schedule(path=arguments.path) as event_queue:
        async for event in event_queue.subscribe():
            print(event)
    return 0


def main() -> int:
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        return 2  # SIGINT = 2


if __name__ == "__main__":
    sys.exit(main())
