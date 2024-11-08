#!/usr/bin/env python3

# Standard libraries.
import io
import os
import pathlib
import struct
import sys
import typing

# External dependencies.
import textual.app
import textual.binding
import textual.widgets
import textual.widgets.data_table

from rich.text import Text
from textual.widgets import RadioButton


class PidInputScreen(textual.screen.Screen[int]):
    def __init__(self, *args: typing.Any, pid: int, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._pid = pid

    def compose(self) -> textual.app.ComposeResult:
        yield textual.widgets.Input(value=str(self._pid), type="integer")

    def on_input_submitted(self, event: textual.widgets.Input.Submitted) -> None:
        self.dismiss(int(event.value))


class MemoryMapTable(textual.widgets.DataTable["Text | str"]):
    buffer = textual.reactive.reactive(b"")

    def on_mount(self) -> None:
        self.add_columns(
            "Start", "End", "Length", "Perms", "Offset", "dev", "inode", "pathname"
        )
        self.cursor_type = "row"

    def update_all_cells(self) -> None:
        self.clear()

        data_stream = io.BytesIO(self.buffer)
        for row_data in data_stream:
            # Remove trailing new line.
            row_data = row_data.strip()
            # Likely reached end of file.
            if not row_data:
                break
            # There are five mandatory fields.
            try:
                address, perms, offset, dev, remaining = row_data.split(maxsplit=4)
            except ValueError:
                continue
            try:
                address_start, address_end = address.split(b"-", maxsplit=1)
            except ValueError:
                continue

            # Pathname is optional.
            try:
                inode, pathname = remaining.split(maxsplit=1)
            except ValueError:
                inode = remaining
                pathname = b""

            start = int(address_start, 16)
            end = int(address_end, 16)
            length = end - start

            # Show the parsed data.
            self.add_row(
                f"{start:#014x}",
                f"{end:#018x}",
                Text(str(length), justify="right"),
                perms.decode(),
                offset.decode(),
                dev.decode(),
                Text(inode.decode(), justify="right"),
                # Using `pathname.decode()` directly seems to make `[heap]` disappear.
                Text(pathname.decode(), justify="left"),
            )

    def watch_buffer(self, old_buffer: bytes, new_buffer: bytes) -> None:
        del old_buffer
        del new_buffer
        cursor_coordinate = self.cursor_coordinate
        self.update_all_cells()
        self.cursor_coordinate = cursor_coordinate


class MemorySelectionScreen(textual.screen.Screen[bytes]):
    BINDINGS = [
        ("P", "select_pid", "Select PID"),
    ]

    pid = textual.reactive.reactive(os.getpid())

    def action_select_pid(self) -> None:
        def callback(pid: int) -> None:
            self.pid = pid

        new_screen = PidInputScreen(pid=self.pid)
        self.app.push_screen(new_screen, callback=callback)

    def compose(self) -> textual.app.ComposeResult:
        yield textual.widgets.Header()
        yield MemoryMapTable()
        yield textual.widgets.Footer()

    def on_data_table_row_selected(
        self, event: textual.widgets.DataTable.RowSelected
    ) -> None:
        memory_map_table = event.control
        row = memory_map_table.get_row(event.row_key)
        start = int(row[0], 16)

        mem_path = pathlib.Path("/proc") / str(self.pid) / "mem"
        with mem_path.open("br") as mem_file:
            mem_file.seek(start)
            buffer_size = 1024
            buffer = mem_file.read(buffer_size)
        self.dismiss(buffer)

    def on_mount(self) -> None:
        # Focus the table instead of the first widget.
        memory_map_table = self.get_child_by_type(MemoryMapTable)
        memory_map_table.focus()

    def watch_pid(self, old_pid: int, new_pid: int) -> None:
        del old_pid
        maps_path = pathlib.Path("/proc") / str(new_pid) / "maps"
        memory_map_table = self.get_child_by_type(MemoryMapTable)
        memory_map_table.buffer = maps_path.read_bytes()
        self.sub_title = f"PID: {new_pid}"


STRUCT_FORMAT_CHAR = {
    "char": "c",
    "signed char": "b",
    "unsigned char": "B",
    "bool": "?",
    "short": "h",
    "unsigned short": "H",
    "int ": "i",
    "unsigned int ": "I",
    "long": "l",
    "unsigned long": "L",
    "long long": "q",
    "unsigned long long": "Q",
    "ssize_t": "n",
    "size_t": "N",
    "float": "f",
    "double": "d",
}


class StructFormatScreen(textual.screen.Screen[str]):
    def __init__(
        self, *args: typing.Any, struct_format: str, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._struct_format = struct_format

    def compose(self) -> textual.app.ComposeResult:
        with textual.widgets.RadioSet():
            for label in STRUCT_FORMAT_CHAR:
                yield RadioButton(label, value=label == self._struct_format)

    def on_radio_set_changed(self, event: textual.widgets.RadioSet.Changed) -> None:
        self.dismiss(STRUCT_FORMAT_CHAR[str(event.pressed.label)])


def data_to_cell(data: "bytes | int | str") -> "int | str":
    if isinstance(data, bytes):
        return data.decode()

    return data


class MemoryTable(textual.widgets.DataTable["int | str"]):
    BINDINGS = [
        ("A", "add_new_column", "New Column"),
        ("D", "delete_column", "Delete Column"),
        ("ctrl+v", "toggle_cursor_type('column')", "Column"),
    ]

    buffer = textual.reactive.reactive(b"")

    def action_add_new_column(self) -> None:
        # Keep track of cursor coordinate to restore later.
        cursor_coordinate = self.cursor_coordinate
        # Textual cannot insert columns in the middle.
        # So fetch existing columns and add everything again.
        new_label = "B"
        column_labels = [column.label for column in self.ordered_columns]
        column_labels.insert(cursor_coordinate.column, Text(new_label))
        self.clear(columns=True)
        self.add_columns(*column_labels)
        # Shift buffer content.
        self.update_all_cells()
        # Restore coordinate for the user.
        self.cursor_coordinate = cursor_coordinate

    def action_delete_column(self) -> None:
        # Keep track of cursor coordinate to restore later.
        cursor_coordinate = self.cursor_coordinate
        # Figure out which column to remove.
        cursor_column_key = self.ordered_columns[cursor_coordinate.column].key
        self.remove_column(cursor_column_key)
        # Shift buffer content.
        self.update_all_cells()
        # Restore coordinate for the user.
        # Okay to go past the end. Textual seems to round as appropriate.
        self.cursor_coordinate = cursor_coordinate

    def action_toggle_cursor_type(
        self, cursor_type: textual.widgets.data_table.CursorType
    ) -> None:
        if self.cursor_type != cursor_type:
            self.cursor_type = cursor_type
        else:
            self.cursor_type = "cell"

    def on_data_table_column_selected(
        self, event: textual.widgets.DataTable.ColumnSelected
    ) -> None:
        def callback(struct_format_char: str) -> None:
            self.columns[event.column_key].label = Text(struct_format_char)
            self.update_all_cells()

        struct_format_screen = StructFormatScreen(
            struct_format=str(self.columns[event.column_key].label)
        )
        self.app.push_screen(struct_format_screen, callback=callback)

    def on_mount(self) -> None:
        self.add_columns("B", "B", "B", "B")

    def update_all_cells(self) -> None:
        self.clear()

        ordered_columns = self.ordered_columns
        if not ordered_columns:
            return

        struct_format = "@" + "".join(str(column.label) for column in ordered_columns)
        table_struct = struct.Struct(struct_format)
        struct_size = table_struct.size

        data_stream = io.BytesIO(self.buffer)
        while True:
            row_data = data_stream.read(struct_size)
            if len(row_data) < struct_size:
                break

            row = table_struct.unpack(row_data)
            self.add_row(*(data_to_cell(data) for data in row))

    def watch_buffer(self, old_buffer: bytes, new_buffer: bytes) -> None:
        del old_buffer
        del new_buffer
        self.update_all_cells()


class MemoryScreen(textual.screen.Screen[None]):
    BINDINGS = [
        ("P", "read_process", "Read Process"),
    ]

    def action_read_process(self) -> None:
        def callback(buffer: bytes) -> None:
            memory_table = self.get_child_by_type(MemoryTable)
            memory_table.buffer = buffer

        new_screen = MemorySelectionScreen()
        self.app.push_screen(new_screen, callback=callback)

    def compose(self) -> textual.app.ComposeResult:
        yield textual.widgets.Header()
        yield MemoryTable()
        yield textual.widgets.Footer()

    def on_mount(self) -> None:
        # Focus the table instead of the first widget.
        memory_table = self.get_child_by_type(MemoryTable)
        memory_table.buffer = b"abcd123499082284"
        memory_table.focus()
        self.action_read_process()


class HowApp(textual.app.App):  # type: ignore[type-arg]
    BINDINGS = [
        textual.binding.Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
    ]
    ENABLE_COMMAND_PALETTE = True

    def on_mount(self) -> None:
        memory_screen = MemoryScreen()
        self.push_screen(memory_screen)


def main() -> int:
    HowApp().run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
