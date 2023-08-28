#!/usr/bin/env python3

# Standard libraries.
import shlex


# Parameters correspond to TMUX command parameters.
def set_option(  # pylint: disable=too-many-locals
    option: str,
    value: str,
    *,
    append: bool = False,
    default: bool = False,
    format_: bool = False,
    global_: bool = False,
    pane: bool = False,
    quiet: bool = False,
    session: bool = False,
    target_pane: None | str = None,
    unset: bool = False,
    unset_panes: bool = False,
    window: bool = False
) -> str:
    arguments = ["set-option"]
    flags = ""
    flags += "a" if append else ""
    flags += "F" if format_ else ""
    flags += "g" if global_ else ""
    flags += "o" if default else ""
    flags += "p" if pane else ""
    flags += "q" if quiet else ""
    flags += "s" if session else ""
    flags += "u" if unset else ""
    flags += "U" if unset_panes else ""
    flags += "w" if window else ""
    if flags:
        arguments.append("-" + flags)
    if target_pane is not None:
        arguments.append("-t")
        arguments.append(shlex.quote(target_pane))
    arguments.append(shlex.quote(option))
    arguments.append(shlex.quote(value))
    command = " ".join(arguments)
    return command
