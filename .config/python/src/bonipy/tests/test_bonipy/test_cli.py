#!/usr/bin/env python3


# External dependencies.
import click.testing

# Internal modules.
import bonipy.cli


class TestEcho:
    def test_okay_with_no_arguments(self) -> None:
        result = click.testing.CliRunner().invoke(bonipy.cli.main, ["echo"])
        assert result.exit_code == 0
        assert result.output == "\n"

    def test_prints_argument_containing_spaces(self) -> None:
        result = click.testing.CliRunner().invoke(bonipy.cli.main, ["echo", "a  b  c"])
        assert result.exit_code == 0
        assert result.output == "a  b  c\n"

    def test_splits_arguments_with_single_spaces(self) -> None:
        result = click.testing.CliRunner().invoke(bonipy.cli.main, ["echo", "a", "b"])
        assert result.exit_code == 0
        assert result.output == "a b\n"

    def test_flag_n_to_disable_new_line(self) -> None:
        result = click.testing.CliRunner().invoke(bonipy.cli.main, ["echo", "-n", "a"])
        assert result.exit_code == 0
        assert result.output == "a"
