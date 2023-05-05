#!/usr/bin/env python3

# External dependencies.
import click
import click_repl


@click.group(invoke_without_command=True)
def main() -> None:
    context = click.get_current_context()
    if context.invoked_subcommand is None:
        click_repl.repl(context)


@main.command()
@click.option("no_new_line", "-n", is_flag=True)
@click.argument("strings", nargs=-1)
def echo(no_new_line: bool, strings: tuple[str]) -> None:
    message = " ".join(strings)
    click.echo(message, nl=not no_new_line)


if __name__ == "__main__":
    main()
