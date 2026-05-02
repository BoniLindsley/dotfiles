#!/usr/bin/env python3

# Standard libraries.
import logging
import pathlib
import subprocess
import typing

from typing import List, Union

# Internal modules.
from . import packaging

_logger = logging.getLogger(__name__)


def run_subprocess(cmd: List[str], *, cwd: Union[None, pathlib.Path] = None) -> None:
    _logger.info("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=str(cwd) if cwd is not None else None)


class LlvmProject(packaging.Package):
    default_version = "21.1.8"
    name = "llvm-project"

    def __init__(
        self, *args: typing.Any, version: Union[None, str] = None, **kwargs: typing.Any
    ) -> None:
        if version is None:
            version = self.default_version
        super().__init__(*args, package=self.name, tag=version, **kwargs)

    def build(self) -> None:
        run_subprocess(
            [
                "cmake",
                "-S",
                "llvm",
                "-B",
                "build",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DLLVM_ENABLE_PROJECTS=clang;clang-tools-extra",
                "-DLLVM_ENABLE_RUNTIMES=compiler-rt;libc;libcxx;libcxxabi;libunwind;openmp",
            ],
            cwd=self.build_directory,
        )
        run_subprocess(["cmake", "--build", "build"], cwd=self.build_directory)

    @property
    def orig_url(self) -> str:
        control = self.control
        git_tag = "llvmorg-" + control.tag
        orig_url = (
            "https://github.com/llvm/llvm-project/archive/refs/tags/"
            + git_tag
            + self.orig_suffix
        )
        return orig_url


class Neovim(packaging.Package):
    default_version = "0.12.2"
    name = "neovim"

    def __init__(
        self, *args: typing.Any, version: Union[None, str] = None, **kwargs: typing.Any
    ) -> None:
        if version is None:
            version = self.default_version
        super().__init__(*args, package=self.name, tag=version, **kwargs)

    def build(self) -> None:
        destdir = self.destdir
        run_subprocess(
            [
                "make",
                "CMAKE_BUILD_TYPE=RelWithDebInfo",
                "CMAKE_EXTRA_FLAGS=-DCMAKE_INSTALL_PREFIX=" + str(destdir),
            ],
            cwd=self.build_directory,
        )
        run_subprocess(
            ["make", "CMAKE_INSTALL_PREFIX=" + str(destdir), "install"],
            cwd=self.build_directory,
        )

    @property
    def orig_url(self) -> str:
        git_tag = "v" + self.control.tag
        orig_url = (
            "https://github.com/neovim/neovim/archive/refs/tags/"
            + git_tag
            + self.orig_suffix
        )
        return orig_url


PACKAGES = {package.name: package for package in (LlvmProject, Neovim)}


def run() -> int:
    neovim = Neovim()
    neovim.download_orig()
    neovim.push_orig()
    neovim.pull_orig()
    neovim.extract()
    neovim.build()
    neovim.package()
    neovim.push()
    neovim.pull()
    neovim.install()
    return 0
