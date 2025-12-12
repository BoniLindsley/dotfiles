#!/usr/bin/env python3

# pylint: disable=fixme

# Standard libraries.
import argparse
import collections
import logging
import pathlib
import subprocess
import sys
import tarfile
import typing

from typing import List, Union

# Internal modules.
from . import logging_ext
from . import xdg

_logger = logging.getLogger(__name__)


# TODO: Follow build instructions for apt:
# - <https://wiki.debian.org/PackagingWithGit>
# - <https://www.debian.org/doc/devel-manuals#debmake-doc>


class Control:
    def __init__(
        self,
        *args: typing.Any,
        architecture: Union[None, str] = None,
        package: str,
        revision: Union[None, int, str] = None,  # 1
        version: str,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        # TODO: Determine local architecture automatically if `None`
        if architecture is None:
            architecture = "all"
        if not architecture:
            raise ValueError("Package architecture cannot be empty.")
        if not package:
            raise ValueError("Package name cannot be empty.")
        if not version:
            raise ValueError("Package version must be provided.")

        if isinstance(revision, int):
            revision = str(revision)
        if revision:
            version = version + "-" + revision

        self.architecture = architecture
        self.package = package
        self.version = version

    def to_dict(self) -> "collections.OrderedDict[str, str]":
        as_dict = collections.OrderedDict()  # type: collections.OrderedDict[str, str]
        as_dict["Package"] = self.package
        as_dict["Version"] = self.version
        as_dict["Architecture"] = self.architecture
        return as_dict

    @classmethod
    def parse(cls, stem: str) -> "typing.Self":
        package = stem
        package_version = package.split("_", maxsplit=1)
        if len(package_version) == 1:
            version = ""
        else:
            package, version = package_version

        version_architecture = version.rsplit("_", maxsplit=1)
        if len(version_architecture) == 1:
            architecture = None  # type: None | str
        else:
            version, architecture = version_architecture

        if not version:
            version = "0.0.1"

        return cls(architecture=architecture, package=package, version=version)

    @property
    def revision(self) -> Union[None, str]:
        version = self.version
        i = version.rfind("-")
        if i < 0:
            return None
        revision = version[i + 1 :]
        if not revision:
            return None
        return revision

    @property
    def stem(self) -> str:
        stem = "_".join((self.package, self.version, self.architecture))
        return stem


class Repository:
    def __init__(
        self, *args: typing.Any, path: pathlib.Path, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.path = path

    def create_binary_package(
        self,
        directory: pathlib.Path,
        *,
        component: Union[None, str] = None,
        control: Control,
        destdir: pathlib.Path
    ) -> None:
        if component is None:
            component = "main"

        destdir.mkdir(mode=0o755, parents=True, exist_ok=True)
        data_path = destdir / "data.tar.gz"
        name = "_".join((control.package, control.version, control.architecture))
        with tarfile.open(str(data_path), "w:gz") as tar:
            tar.add(str(directory), arcname=name)

        package = control.package
        path = (
            self.path / "pool" / component / package[0] / package / name / "data.tar.gz"
        )
        path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        data_path.rename(path)

    def get_listing_path(
        self, *, architecture: str, component: str, distribution: str
    ) -> pathlib.Path:
        # Mimic this structure:
        # <https://ftp.debian.org/debian/dists/stable/main/binary-amd64/>
        path = (
            self.path
            / "dists"
            / distribution
            / component
            / ("binary-" + architecture)
            / "Packages"
        )
        return path

    def get_package_paths(
        self, package: str, *, component: Union[None, str] = None
    ) -> List[pathlib.Path]:
        if component is None:
            component = "main"

        package_paths = list(
            (self.path / "pool" / component / package[0] / package).iterdir()
        )
        return package_paths

    def install_binary_package(self, path: pathlib.Path, prefix: pathlib.Path) -> None:
        data_path = path / "data.tar.gz"
        destdir = prefix / "opt"
        destdir.mkdir(mode=0o755, parents=True, exist_ok=True)
        with tarfile.open(str(data_path), "r:gz") as tar:
            tar.extractall(str(destdir))


def get_neovim_source(src_path: pathlib.Path) -> None:
    get_source(
        repository="https://github.com/neovim/neovim.git",
        src_path=src_path,
        version="v0.11.1",
    )


def get_source(*, repository: str, src_path: pathlib.Path, version: str) -> None:
    repository_path = pathlib.Path(repository)
    name = repository_path.name
    suffix = ".git"
    if name.endswith(suffix):
        name = name[: -len(suffix)]
    if not name:
        name = repository_path.parent.name
    subprocess.run(
        [
            "git",
            "clone",
            "--branch",
            version,
            "--depth",
            "1",
            "--",
            repository,
            str(src_path / name),
        ],
        check=True,
    )


def run(*, arguments: argparse.Namespace) -> int:
    prefix = arguments.prefix  # type:pathlib.Path

    if arguments.destdir is None:
        destdir = prefix / "scratch"
    else:
        destdir = arguments.destdir

    repository_path = arguments.repository_path  # type: pathlib.Path
    if repository_path is None:
        repository_path = prefix / "srv" / "bapt"

    repository = Repository(path=repository_path)

    command = arguments.command  # type: typing.Literal["install", "package", "search"]
    if command == "install":
        path = arguments.path  # type: pathlib.Path
        repository.install_binary_package(path=path, prefix=prefix)
        return 0

    if command == "package":
        directory = arguments.directory  # type: pathlib.Path
        control = Control.parse(directory.name)
        repository.create_binary_package(directory, control=control, destdir=destdir)
        return 0

    if command == "search":
        package = arguments.package  # type: str
        for package_path in repository.get_package_paths(package):
            print(package_path)
        return 0

    return ValueError("Unknown command: " + command)


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and call `run`."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(argument_parser)
    argument_parser.add_argument("--destdir", type=pathlib.Path)
    argument_parser.add_argument("--prefix", default=xdg.home(), type=pathlib.Path)
    argument_parser.add_argument("--repository-path", type=pathlib.Path)
    subparsers = argument_parser.add_subparsers(dest="command")
    install_subparser = subparsers.add_parser("install")
    install_subparser.add_argument("path", type=pathlib.Path)
    package_subparser = subparsers.add_parser("package")
    package_subparser.add_argument(
        "directory", default=pathlib.Path(), type=pathlib.Path
    )
    install_subparser = subparsers.add_parser("search")
    install_subparser.add_argument("package")
    arguments = argument_parser.parse_args(argv[1:])

    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    if not arguments.command:
        argument_parser.print_help()
        return 1
    return run(arguments=arguments)


if __name__ == "__main__":
    sys.exit(main())
