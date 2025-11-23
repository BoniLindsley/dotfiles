#!/usr/bin/env python3

# Keep this Python 3.5 compatible for Debian 9 support.

# Standard libraries.
import argparse
import logging
import subprocess
import sys

# TODO(Python 3.9): Use builtin.
from typing import List

# TODO(Python 3.10): Use | instead of Union.
from typing import Union

# Internal modules.
from .. import inspect_ext
from .. import logging_ext

_logger = logging.getLogger(__name__)


def gdbus_notify(  # pylint: disable=too-many-arguments
    *,
    app_name: str,
    replaces_id: Union[None, int] = None,
    app_icon: Union[None, str] = None,
    summary: str,
    body: Union[None, str] = None,
    actions: Union[None, str] = None,
    hints: Union[None, str] = None,
    expire_timeout: Union[None, int] = None
) -> int:
    if replaces_id is None:
        replaces_id = 0  # New notification.
    if app_icon is None:
        app_icon = ""  # No icon
    if body is None:
        body = ""  # Empty body
    if actions is None:
        actions = "[]"
    if hints is None:
        hints = "{}"
    if expire_timeout is None:
        expire_timeout = -1  # Use server settings.

    # Requires Debian package `libglib2.0-bin`.
    # Writes `(type, id}` to stdout. For example, `(uint32,6)`.
    subprocess.run(
        [
            "gdbus",
            "call",
            "--session",
            "--dest",
            "org.freedesktop.Notifications",
            "--object-path",
            "/org/freedesktop/Notifications",
            "--method",
            "org.freedesktop.Notifications.Notify",
            app_name,
            str(replaces_id),
            app_icon,
            summary,
            body,
            actions,
            hints,
            str(expire_timeout),
        ],
        check=True,
    )
    return True


def send_freedesktop_notification(title: str, message: str) -> bool:
    _logger.log(5, "Using gdbus.")
    try:
        gdbus_notify(
            app_name="python",
            summary=title,
            body=message,
            expire_timeout=5000,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    else:
        return True
    return False


def send_toast_notification(title: str, message: str) -> bool:
    _logger.log(5, "Using toast.")
    # Use PowerShell to create a Windows toast notification
    module_directory = inspect_ext.get_module_directory(lambda: None)
    ps_script = (module_directory / "toast.ps.fstring").read_text()
    ps_script = ps_script.format(message=message, title=title)
    try:
        subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", ps_script],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    else:
        return True
    return False


def run(*, title: str, message: str) -> int:
    result = False
    if sys.platform == "linux":
        if not result:
            result = send_freedesktop_notification(title, message)
    elif sys.platform == "win32":
        result = False
        if not result:
            result = send_toast_notification(title, message)
    else:
        _logger.error("Unsupported platform: %s", sys.platform)
    if not result:
        _logger.error("Unable to send notifications.")
        return 1
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and run corresponding functions."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(argument_parser)
    argument_parser.add_argument("title")
    argument_parser.add_argument("message")

    arguments = argument_parser.parse_args(argv[1:])
    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    return run(title=arguments.title, message=arguments.message)


if __name__ == "__main__":
    sys.exit(main())
