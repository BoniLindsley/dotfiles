#!/usr/bin/env python3

# Standard libraries.
import pathlib

# External dependencies.
import pytest

# Internal modules.
from bonipy35.bapt.__main__ import list_pool, main
from bonipy35.bapt.manifests import Neovim
from bonipy35.bapt.packaging import Configuration


class TestListPool:
    def test_empty_repository(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        list_pool(Configuration(prefix=tmp_path))
        assert capsys.readouterr().out.splitlines() == [
            "llvm-project",
            "neovim",
            "neovim-qt",
        ]

    def test_repository_names(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        configuration = Configuration(prefix=tmp_path)
        pool = configuration.repository / "pool" / "main"
        (pool / "n" / "neovim" / "neovim_1.0_all").mkdir(parents=True)
        (pool / "n" / "neovim" / "neovim_2.0_all").mkdir()
        (pool / "e" / "example" / "example_1.0_all").mkdir(parents=True)
        (pool / "e" / "file").touch()
        list_pool(configuration)
        assert capsys.readouterr().out.splitlines() == [
            "example",
            "llvm-project",
            "neovim",
            "neovim-qt",
        ]


class TestMain:
    @pytest.mark.parametrize(
        "command",
        [
            "status",
            "download_orig",
            "push_orig",
            "pull_orig",
            "extract",
            "build",
            "package",
            "push",
            "pull",
            "install",
        ],
    )
    def test_dispatch(
        self,
        command: str,
        tmp_path: pathlib.Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        called = []  # type: list[str]

        def action(package: Neovim) -> None:
            assert package.configuration.prefix == tmp_path
            assert package.control.tag == "1.2.3"
            called.append(command)

        monkeypatch.setattr(Neovim, command, action)
        assert (
            main(
                [
                    "bapt",
                    "--prefix",
                    str(tmp_path),
                    command,
                    "neovim",
                    "1.2.3",
                ]
            )
            == 0
        )
        assert called == [command]

    def test_missing_command(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as error:
            main(["bapt"])
        assert error.value.code == 2
        assert "a subcommand is required" in capsys.readouterr().err

    def test_unknown_package(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as error:
            main(["bapt", "status", "unknown"])
        assert error.value.code == 2
        assert "unknown package: unknown" in capsys.readouterr().err

    def test_list_names_are_accepted(
        self, tmp_path: pathlib.Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main(["bapt", "--prefix", str(tmp_path), "list"]) == 0
        names = capsys.readouterr().out.splitlines()
        for name in names:
            assert (
                main(["bapt", "--prefix", str(tmp_path), "status", name]) == 0
            )
            assert "Package " + name in capsys.readouterr().out
