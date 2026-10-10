#!/usr/bin/env python3
"""Tk interface using Unix socket readiness, without refresh polling."""

# Standard libraries.
import importlib
import pathlib
import sys
import typing

from typing import List, Union

# Internal modules.
from . import cli, client, data


class GUIClient:
    def __init__(self, connection: client.Client, tk: typing.Any) -> None:
        self.connection = connection
        self.tk = tk
        self.root = tk.Tk()
        self.root.title("Alarms and timers")
        self.items = tk.Listbox(
            self.root, width=95, height=15, exportselection=False
        )
        self.items.pack(fill=tk.BOTH, expand=True)
        self.notifications = tk.Label(self.root, justify=tk.LEFT)
        self.notifications.pack(fill=tk.X)
        self.status = tk.Label(self.root, text="")
        self.status.pack(fill=tk.X)
        buttons = tk.Frame(self.root)
        buttons.pack()
        for command in (
            "alarm",
            "timer",
            "reschedule",
            "pause",
            "resume",
            "stop",
            "restart",
            "dismiss",
            "delete",
        ):
            tk.Button(
                buttons,
                text=command,
                command=lambda action=command: self.command(action),
            ).pack(side=tk.LEFT)
        self.root.createfilehandler(
            connection.sock, tk.READABLE, self.on_readable
        )
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.render()

    def render(self) -> None:
        # A response can share a socket read with a later event; those frames
        # need draining even when the OS socket is no longer readable.
        while self.connection.buffered:
            self.connection.receive()
        selection = self.items.curselection()
        self.items.delete(0, self.tk.END)
        snapshot = self.connection.snapshot
        for line in cli.format_snapshot(
            {"items": snapshot["items"], "notifications": []}
        ):
            self.items.insert(self.tk.END, line)
        if selection and selection[0] < len(snapshot["items"]):
            self.items.selection_set(selection[0])
        self.notifications.config(
            text="\n".join(
                cli.format_snapshot(
                    {"items": [], "notifications": snapshot["notifications"]}
                )
            )
        )

    def on_readable(self, _descriptor: typing.Any, _mask: int) -> None:
        try:
            self.connection.receive()
            while self.connection.buffered:
                self.connection.receive()
            self.render()
        except (OSError, ValueError, EOFError) as error:
            self.status.config(text=str(error))
            self.root.deletefilehandler(self.connection.sock)

    def command(self, action: str) -> None:
        # Import here so headless clients do not require Tk dialog support.
        simpledialog = importlib.import_module("tkinter.simpledialog")

        try:
            fields = {}  # type: typing.Dict[str, typing.Any]
            if action in ("alarm", "timer", "reschedule"):
                prompt = (
                    "Duration (e.g. 10m)"
                    if action == "timer"
                    else "HH:MM or YYYY-MM-DD HH:MM"
                )
                value = simpledialog.askstring(
                    action, prompt, parent=self.root
                )
                if value is None:
                    return
                if action == "timer":
                    fields["duration"] = cli.parse_duration(
                        value
                    ).total_seconds()
                else:
                    fields["end_time"] = data.Datetime.model_dump(
                        cli.parse_alarm_time(value, data.utc_now())
                    )
            if action not in ("alarm", "timer"):
                selection = self.items.curselection()
                if not selection:
                    raise ValueError("Select an item first")
                fields["id_"] = self.connection.snapshot["items"][
                    selection[0]
                ]["id_"]
            self.connection.request(action, **fields)
            self.status.config(text="")
            self.render()
        except (OSError, ValueError, EOFError, OverflowError) as error:
            self.status.config(text=str(error))

    def close(self) -> None:
        self.root.deletefilehandler(self.connection.sock)
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run(directory: pathlib.Path) -> int:
    try:
        tk = importlib.import_module("tkinter")
    except ImportError as error:
        raise RuntimeError("Tk is unavailable; install python3-tk") from error
    try:
        with client.Client(directory=directory) as connection:
            GUIClient(connection, tk).run()
    except tk.TclError as error:
        raise RuntimeError(
            "Cannot open Tk display: {}".format(error)
        ) from error
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    return client.interface_main(run, argv, __doc__)


if __name__ == "__main__":
    sys.exit(main())
