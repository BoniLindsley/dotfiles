#!/usr/bin/env python3

# pylint: disable=fixme

# Standard libraries.
import collections
import logging
import pathlib
import shutil
import typing
import urllib.request

from typing import Union

# Internal modules.
from .. import pathlib_ext
from .. import tarfile_ext

_logger = logging.getLogger(__name__)


# TODO: Follow build instructions for apt:
# - <https://wiki.debian.org/PackagingWithGit>
# - <https://www.debian.org/doc/devel-manuals#debmake-doc>
# Use Makefile convention as necessary.
# - <https://www.gnu.org/software/make/manual/html_node/Directory-Variables.html>
# Example pool directory:
# - <https://deb.debian.org/debian/pool/main/g/git/>


def download(url: str, dest: pathlib.Path) -> None:
    _logger.info("Downloading URL: %s", url)
    _logger.info("Downloading to : %s", dest)
    pathlib_ext.ensure_is_dir(dest.parent)
    with urllib.request.urlopen(url) as response:
        with open(str(dest), "wb") as output_file:
            shutil.copyfileobj(response, output_file)
    _logger.info("Finished downloading %s", url)


class Control:
    def __init__(
        self,
        *args: typing.Any,
        architecture: Union[None, str] = None,
        package: str,
        revision: Union[None, int, str] = None,  # 1
        tag: str,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        # TODO: Determine local architecture automatically if `None`
        if architecture is None:
            architecture = "all"
        if not architecture:
            raise ValueError("Package architecture cannot be empty.")
        if not package:
            raise ValueError("Package name cannot be empty.")
        if not tag:
            raise ValueError("Package tag must be provided.")

        if isinstance(revision, int):
            revision = str(revision)

        self.architecture = architecture
        self.package = package
        self.tag = tag
        self.revision = revision

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Control):
            return (
                self.architecture == other.architecture
                and self.package == other.package
                and self.tag == other.tag
                and self.revision == other.revision
            )
        return NotImplemented

    def get_package_directory(
        self, *, component: Union[None, str] = None
    ) -> pathlib.Path:
        if component is None:
            component = "main"

        package = self.package
        package_directory = pathlib.Path("pool") / component / package[0] / package
        return package_directory

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

        tag_revision = version.rsplit("-", maxsplit=1)
        if len(tag_revision) == 1:
            tag = version
            revision = None  # type: None | str
        else:
            tag, revision = tag_revision

        return cls(
            architecture=architecture, package=package, revision=revision, tag=tag
        )

    @property
    def stem(self) -> str:
        stem = "_".join((self.package, self.version, self.architecture))
        return stem

    def to_dict(self) -> "collections.OrderedDict[str, str]":
        as_dict = collections.OrderedDict()  # type: collections.OrderedDict[str, str]
        as_dict["Package"] = self.package
        as_dict["Version"] = self.version
        as_dict["Architecture"] = self.architecture
        return as_dict

    @property
    def version(self) -> str:
        revision = self.revision
        tag = self.tag
        if revision:
            version = tag + "-" + revision
        else:
            version = tag
        return version


class Configuration:

    def __init__(
        self,
        *args: typing.Any,
        build_directory: Union[None, pathlib.Path] = None,
        prefix: Union[None, pathlib.Path] = None,
        repository: Union[None, pathlib.Path] = None,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._build_directory = build_directory
        self._prefix = prefix
        self._repository = repository

    @property
    def build_directory(self) -> pathlib.Path:
        return self._build_directory or self.prefix / "build"

    @classmethod
    def get_default_prefix(cls) -> pathlib.Path:
        del cls
        return pathlib.Path.home()

    def get_install_directory(
        self,
        control: Control,
    ) -> pathlib.Path:
        install_directory = self.prefix / "opt" / control.stem
        return install_directory

    def get_package_directory(
        self,
        control: Control,
        *,
        component: Union[None, str] = None,
    ) -> pathlib.Path:
        if component is None:
            component = "main"

        package = control.package
        package_directory = self.repository / "pool" / component / package[0] / package
        return package_directory

    @property
    def prefix(self) -> pathlib.Path:
        return self._prefix or self.get_default_prefix()

    @prefix.setter
    def prefix(self, new_prefix: Union[None, pathlib.Path]) -> None:
        self._prefix = new_prefix

    @property
    def repository(self) -> pathlib.Path:
        return self._repository or self.prefix / "srv" / "bapt"

    @repository.setter
    def repository(self, new_repository: Union[None, pathlib.Path]) -> None:
        self._repository = new_repository


class Package:
    def __init__(
        self,
        *args: typing.Any,
        configuration: Union[None, Configuration] = None,
        orig_suffix: Union[None, str] = None,
        package: str,
        tag: str,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if configuration is None:
            configuration = Configuration()
        if orig_suffix is None:
            orig_suffix = ".tar.gz"
        self.orig_suffix = orig_suffix
        self.configuration = configuration
        self.control = Control(package=package, tag=tag)

    def build(self) -> None:
        raise NotImplementedError()

    @property
    def build_directory(self) -> pathlib.Path:
        return self.configuration.build_directory / self.orig_stem

    @property
    def destdir(self) -> pathlib.Path:
        return self.build_directory / "bapt" / self.orig_stem

    def download_orig(self) -> None:
        download(self.orig_url, self.orig_local_path)

    def extract(self) -> None:
        tarfile_ext.extract(
            self.orig_local_path, self.build_directory, strip_components=1
        )

    def install(self) -> None:
        tarfile_ext.extract(
            self.local_path,
            self.configuration.get_install_directory(self.control),
            strip_components=1,
        )

    @property
    def local_path(self) -> pathlib.Path:
        local_path = (
            self.configuration.build_directory / self.control.stem / "data.tar.gz"
        )
        return local_path

    @property
    def orig_filename(self) -> str:
        orig_filename = self.orig_stem + ".orig" + self.orig_suffix
        return orig_filename

    @property
    def orig_local_path(self) -> pathlib.Path:
        orig_local_path = self.configuration.build_directory / self.orig_filename
        return orig_local_path

    @property
    def orig_package_path(self) -> pathlib.Path:
        package_directory = self.configuration.get_package_directory(self.control)
        orig_package_path = package_directory / self.orig_filename
        return orig_package_path

    @property
    def orig_stem(self) -> str:
        control = self.control
        orig_stem = control.package + "_" + control.tag
        return orig_stem

    @property
    def orig_url(self) -> str:
        raise NotImplementedError()

    def package(self) -> None:
        local_path = self.local_path
        pathlib_ext.ensure_is_dir(local_path.parent)
        tarfile_ext.create(self.destdir, local_path)

    @property
    def package_path(self) -> pathlib.Path:
        package_directory = self.configuration.get_package_directory(self.control)
        package_path = package_directory / self.control.stem / "data.tar.gz"
        return package_path

    def pull(self) -> None:
        local_path = self.local_path
        pathlib_ext.ensure_is_dir(local_path.parent)
        shutil.copyfile(self.package_path, local_path)

    def pull_orig(self) -> None:
        orig_local_path = self.orig_local_path
        pathlib_ext.ensure_is_dir(orig_local_path.parent)
        shutil.copyfile(self.orig_package_path, orig_local_path)

    def push(self) -> None:
        package_path = self.package_path
        pathlib_ext.ensure_is_dir(package_path.parent)
        shutil.copyfile(self.local_path, package_path)

    def push_orig(self) -> None:
        orig_package_path = self.orig_package_path
        pathlib_ext.ensure_is_dir(orig_package_path.parent)
        shutil.copyfile(self.orig_local_path, orig_package_path)

    def status(self) -> None:
        print("Package", self.control.package)
        print("Version", self.control.version)
        s = {
            "downloaded": self.orig_local_path.exists(),
            "archived": self.orig_package_path.exists(),
            "built": self.local_path.exists(),
            "packaged": self.package_path.exists(),
            "installed": self.configuration.get_install_directory(
                self.control
            ).exists(),
        }
        for k, v in s.items():
            mark = "   " if v else "Not"
            print(mark, k)
