#!/usr/bin/env python3

# Standard libraries.
import pathlib

from typing import List, Type, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.bapt import manifests
from bonipy35.bapt.manifests import LlvmProject, NeovimQt
from bonipy35.bapt.packaging import Configuration


class TestBuild:
    @pytest.mark.parametrize("package_type", [LlvmProject, NeovimQt])
    def test_install_into_package_directory(
        self,
        package_type: Union[Type[LlvmProject], Type[NeovimQt]],
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        package = package_type(configuration=Configuration(prefix=tmp_path))
        commands = []  # type: List[List[str]]

        def run_subprocess(
            cmd: List[str], *, cwd: Union[None, pathlib.Path] = None
        ) -> None:
            assert cwd == package.build_directory
            commands.append(cmd)

        monkeypatch.setattr(manifests, "run_subprocess", run_subprocess)
        package.build()
        assert "-DCMAKE_INSTALL_PREFIX=" + str(package.destdir) in commands[0]
        assert commands[1] == ["cmake", "--build", "build"]
        assert commands[2] == ["cmake", "--install", "build"]
