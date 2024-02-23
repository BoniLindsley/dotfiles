#!/usr/bin/env python3

# External dependencies.
import click.testing

# Internal modules.
from bonipy.click_how import cli


class TestEcho:
    def test_fails_if_uknown_command_given(self) -> None:
        result = click.testing.CliRunner().invoke(cli, ["bad_command"])
        assert result.exit_code == 2
        assert result.output == "\n".join(
            (
                "Usage: cli [OPTIONS] COMMAND [ARGS]...",
                "Try 'cli --help' for help.",
                "",
                "Error: No such command 'bad_command'.",
                "",
            )
        )
