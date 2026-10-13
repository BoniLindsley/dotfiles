#!/usr/bin/env python3

# Standard libraries.
import sys

from typing import List, Union

# Internal modules.
from .. import runpy_ext


def main(argv: Union[None, List[str]] = None) -> int:
    return runpy_ext.subcommand_main(
        argv=argv,
        choices=(
            "clock",
            "counter",
            "editor",
            "tower",
        ),
        description="Asyncio ncurses examples",
        package=__package__,
    )


if __name__ == "__main__":
    sys.exit(main())
