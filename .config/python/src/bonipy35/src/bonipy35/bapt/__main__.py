#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging
import pathlib
import sys

from typing import List, Union

# Internal libraries.
from .. import logging_ext

from . import manifests
from . import packaging

_logger = logging.getLogger(
    __name__ if __name__ != "__main__" else __package__
)


def list_pool(configuration: packaging.Configuration) -> None:
    component = "main"
    packages = set()  # type: set[str]
    for package_directory in (
        configuration.repository / "pool" / component
    ).glob("*/*"):
        if not package_directory.is_dir():
            continue
        packages.add(package_directory.name)
    for create_package in manifests.PACKAGES.values():
        package = create_package()
        packages.add(package.control.package)
    for package_name in sorted(packages):
        print(package_name)


def main(  # pylint: disable=too-many-locals
    argv: Union[None, List[str]] = None,
) -> int:
    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser(prog="bapt")
    logging_ext.add_verbose_flag(argument_parser)
    argument_parser.add_argument(
        "--prefix",
        help="Installation prefix (default: "
        + str(packaging.Configuration.get_default_prefix())
        + ")",
        type=pathlib.Path,
    )

    argument_subparsers = argument_parser.add_subparsers(dest="command")

    argument_subparsers.add_parser("list")
    status_parser = argument_subparsers.add_parser("status")
    status_parser.add_argument("name")
    status_parser.add_argument("version", nargs="?")
    download_orig_parser = argument_subparsers.add_parser("download_orig")
    download_orig_parser.add_argument("name")
    download_orig_parser.add_argument("version", nargs="?")
    push_orig_parser = argument_subparsers.add_parser("push_orig")
    push_orig_parser.add_argument("name")
    push_orig_parser.add_argument("version", nargs="?")
    pull_orig_parser = argument_subparsers.add_parser("pull_orig")
    pull_orig_parser.add_argument("name")
    pull_orig_parser.add_argument("version", nargs="?")
    extract_parser = argument_subparsers.add_parser("extract")
    extract_parser.add_argument("name")
    extract_parser.add_argument("version", nargs="?")
    build_parser = argument_subparsers.add_parser("build")
    build_parser.add_argument("name")
    build_parser.add_argument("version", nargs="?")
    package_parser = argument_subparsers.add_parser("package")
    package_parser.add_argument("name")
    package_parser.add_argument("version", nargs="?")
    push_parser = argument_subparsers.add_parser("push")
    push_parser.add_argument("name")
    push_parser.add_argument("version", nargs="?")
    pull_parser = argument_subparsers.add_parser("pull")
    pull_parser.add_argument("name")
    pull_parser.add_argument("version", nargs="?")
    install_parser = argument_subparsers.add_parser("install")
    install_parser.add_argument("name")
    install_parser.add_argument("version", nargs="?")

    arguments = argument_parser.parse_args(argv[1:])
    if arguments.command is None:
        argument_parser.error("a subcommand is required")
    if (
        arguments.command != "list"
        and arguments.name not in manifests.PACKAGES
    ):
        argument_parser.error("unknown package: " + arguments.name)

    logging_ext.set_logger_verbosity(
        logger=_logger, verbosity=arguments.verbosity
    )

    configuration = packaging.Configuration(prefix=arguments.prefix)

    if arguments.command == "list":
        list_pool(configuration)
        return 0

    package = manifests.PACKAGES[arguments.name](
        configuration=configuration, version=arguments.version
    )
    getattr(package, arguments.command)()
    return 0


if __name__ == "__main__":
    sys.exit(main())
