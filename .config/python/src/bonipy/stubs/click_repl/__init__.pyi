#!/usr/bin/env python3

# Standard libraries.
import collections.abc

# External dependencies.
import click
import prompt_toolkit.completion

from prompt_toolkit.completion import Completer

# Internal modules.
from .exceptions import InternalCommandException as InternalCommandException

HAS_C8: bool

class ClickExit(RuntimeError): ...

class ClickCompleter(Completer):
    cli: click.Command

    def __init__(self, cli: click.Command) -> None: ...
    def get_completions(
        self,
        document: prompt_toolkit.document.Document,
        complete_event: prompt_toolkit.completion.base.CompleteEvent = ...,
    ) -> collections.abc.Generator[
        prompt_toolkit.completion.base.Completion, None, None
    ]: ...

def bootstrap_prompt(
    prompt_kwargs: dict[str, object], group: click.Command
) -> dict[str, object]: ...
def repl(
    old_ctx: click.Context,
    prompt_kwargs: dict[str, object] = ...,
    allow_system_commands: bool = ...,
    allow_internal_commands: bool = ...,
) -> str | None: ...
def register_repl(group: click.Group, name: str = ...) -> None: ...
def exit() -> None: ...  # pylint: disable=redefined-builtin
def dispatch_repl_commands(command: str) -> bool: ...
def handle_internal_commands(
    command: str,
) -> None | collections.abc.Callable[..., object]: ...
