#!/usr/bin/env python3

# Standard libraries.
import logging
import types
import typing

from typing import List
from unittest import mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.runpy_ext import run_subcommand, subcommand_main


class TestSubcommandMain:
    def test_configures_package_logging(self) -> None:
        with mock.patch(
            "bonipy35.runpy_ext.logging_ext.set_up_logging"
        ) as set_up, mock.patch(
            "bonipy35.runpy_ext.logging_ext.set_logger_verbosity"
        ) as set_verbosity, mock.patch(
            "bonipy35.runpy_ext.run_subcommand", return_value=0
        ):
            assert (
                subcommand_main(
                    ["program", "-vv", "example"],
                    package="package",
                    choices=["example"],
                )
                == 0
            )
        logger = logging.getLogger("package")
        set_up.assert_called_once_with(logger=logger)
        set_verbosity.assert_called_once_with(logger=logger, verbosity=2)

    def test_defaults_to_sys_argv(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("sys.argv", ["program", "other"])
        with mock.patch(
            "bonipy35.runpy_ext.run_subcommand", return_value=3
        ) as dispatch:
            assert (
                subcommand_main(package="other_package", choices=["other"])
                == 3
            )
        dispatch.assert_called_once_with(
            command="other", package="other_package", remaining_arguments=[]
        )

    def test_forwards_arguments_and_status(self) -> None:
        argv = ["program", "example", "--option", "value"]
        with mock.patch(
            "bonipy35.runpy_ext.run_subcommand", return_value=7
        ) as dispatch:
            assert (
                subcommand_main(argv, package="package", choices=("example",))
                == 7
            )
        dispatch.assert_called_once_with(
            command="example",
            package="package",
            remaining_arguments=["--option", "value"],
        )
        assert argv == ["program", "example", "--option", "value"]

    @pytest.mark.parametrize(
        "remaining", [["--help"], ["-vv"], ["--verbose", "--option", "value"]]
    )
    def test_subcommand_owns_help_and_verbosity(
        self, remaining: List[str]
    ) -> None:
        with mock.patch(
            "bonipy35.runpy_ext.run_subcommand", return_value=0
        ) as dispatch:
            assert (
                subcommand_main(
                    ["program", "example"] + remaining,
                    package="package",
                    choices=["example"],
                )
                == 0
            )
        dispatch.assert_called_once_with(
            command="example",
            package="package",
            remaining_arguments=remaining,
        )

    @pytest.mark.parametrize(
        "description", ["Entry point for subcommands.", "Custom commands"]
    )
    def test_help_description(
        self, description: str, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as error:
            if description == "Entry point for subcommands.":
                subcommand_main(
                    ["program", "--help"],
                    package="package",
                    choices=["example"],
                )
            else:
                subcommand_main(
                    ["program", "--help"],
                    package="package",
                    choices=["example"],
                    description=description,
                )
        assert error.value.code == 0
        assert description in capsys.readouterr().out

    @pytest.mark.parametrize("arguments", [[], ["unknown"]])
    def test_rejects_invalid_commands(self, arguments: List[str]) -> None:
        with mock.patch("bonipy35.runpy_ext.run_subcommand") as dispatch:
            with pytest.raises(SystemExit) as error:
                subcommand_main(
                    ["program"] + arguments,
                    package="package",
                    choices=["example"],
                )
        assert error.value.code == 2
        dispatch.assert_not_called()


class TestRunSubcommand:
    def test_forwards_arguments_and_status(self) -> None:
        remaining_arguments = ["argument"]
        main = mock.Mock(return_value=7)
        module = types.SimpleNamespace(main=main)
        with mock.patch(
            "bonipy35.runpy_ext.importlib.import_module", return_value=module
        ) as import_module:
            assert (
                run_subcommand(
                    command="example",
                    package="package",
                    remaining_arguments=remaining_arguments,
                )
                == 7
            )
        import_module.assert_called_once_with("package.example")
        main.assert_called_once_with(["example", "argument"])
        assert remaining_arguments == ["argument"]

    def test_propagates_command_errors(self) -> None:
        module = types.SimpleNamespace(
            main=mock.Mock(side_effect=ValueError("failure"))
        )
        with mock.patch(
            "bonipy35.runpy_ext.importlib.import_module", return_value=module
        ):
            with pytest.raises(ValueError, match="failure"):
                run_subcommand(
                    command="example",
                    package="package",
                    remaining_arguments=[],
                )

    @pytest.mark.parametrize(
        "modules, message",
        [
            ([ImportError("missing")], "Command is not known"),
            (
                [types.SimpleNamespace(), ImportError("missing")],
                "Command has no entry point",
            ),
            (
                [types.SimpleNamespace(), types.SimpleNamespace()],
                "Command not implemented",
            ),
        ],
    )
    def test_reports_missing_command(
        self,
        modules: List[typing.Any],
        message: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        with mock.patch(
            "bonipy35.runpy_ext.importlib.import_module", side_effect=modules
        ):
            assert (
                run_subcommand(
                    command="missing",
                    package="package",
                    remaining_arguments=[],
                )
                == 1
            )
        assert message + ": missing" in caplog.text

    def test_uses_package_main_fallback(self) -> None:
        main = mock.Mock(return_value=3)
        modules = [types.SimpleNamespace(), types.SimpleNamespace(main=main)]
        with mock.patch(
            "bonipy35.runpy_ext.importlib.import_module", side_effect=modules
        ) as import_module:
            assert (
                run_subcommand(
                    command="example",
                    package="package",
                    remaining_arguments=[],
                )
                == 3
            )
        assert import_module.call_args_list == [
            mock.call("package.example"),
            mock.call("package.example.__main__"),
        ]
        main.assert_called_once_with(["example"])
