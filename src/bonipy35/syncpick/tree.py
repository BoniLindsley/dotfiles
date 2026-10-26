#!/usr/bin/env python3
"""Show a comparison as a tree of directories, for any frontend.

The rules match the web page: identical files are shown,
directories start expanded only if something below them differs,
and picking a directory picks every shown file below it.
"""

# Standard libraries.
import enum
import typing

from typing import Dict, Iterable, List, Set, Union

# Internal modules.
from . import compare
from . import transfer


class Directory:
    """A directory of a comparison, with every shown entry below it.

    ``path`` ends with ``/``, except for the root, whose path is empty
    and whose depth is -1.
    """

    def __init__(self, name: str, path: str, depth: int) -> None:
        self.name = name
        self.path = path
        self.depth = depth
        self.directories = {}  # type: Dict[str, Directory]
        self.files = []  # type: List[File]
        self.entries = []  # type: List[compare.Entry]

    def counts(self) -> Dict[compare.State, int]:
        """Count the entries below by state, leaving out absent states."""
        counts = {}  # type: Dict[compare.State, int]
        for entry in self.entries:
            counts[entry.state] = counts.get(entry.state, 0) + 1
        return counts


File = typing.NamedTuple(
    "File", [("name", str), ("entry", compare.Entry), ("depth", int)]
)
"""A file of a comparison, named within its directory."""

Row = Union[Directory, File]


class Pick(enum.Enum):
    """Whether a row is picked; a directory may be partly picked."""

    NONE = "none"
    SOME = "some"
    ALL = "all"


def build(entries: Iterable[compare.Entry]) -> Directory:
    """Group entries by their ``/``-separated paths into a tree."""
    root = Directory("", "", -1)
    for entry in entries:
        names = entry.path.split("/")
        directory = root
        directory.entries.append(entry)
        for name in names[:-1]:
            child = directory.directories.get(name)
            if child is None:
                child = Directory(
                    name, directory.path + name + "/", directory.depth + 1
                )
                directory.directories[name] = child
            directory = child
            directory.entries.append(entry)
        directory.files.append(
            File(name=names[-1], entry=entry, depth=directory.depth + 1)
        )
    return root


class Model:
    """Which entries are shown, expanded and picked.

    Starts with every state shown and nothing picked.
    Directories the user has not toggled are expanded
    only if an entry below them is not the same on both sides.
    """

    def __init__(self, entries: Iterable[compare.Entry] = ()) -> None:
        self.entries = list(entries)
        self.shown = set(compare.State)  # type: Set[compare.State]
        self.expanded = {}  # type: Dict[str, bool]
        self.picked = set()  # type: Set[str]

    def refresh(self, entries: Iterable[compare.Entry]) -> None:
        """Replace the entries, keeping picks of paths still present."""
        self.entries = list(entries)
        self.picked &= {entry.path for entry in self.entries}

    def shown_entries(self) -> List[compare.Entry]:
        return [entry for entry in self.entries if entry.state in self.shown]

    def tree(self) -> Directory:
        return build(self.shown_entries())

    def is_expanded(self, directory: Directory) -> bool:
        expanded = self.expanded.get(directory.path)
        if expanded is not None:
            return expanded
        return any(
            entry.state is not compare.State.SAME
            for entry in directory.entries
        )

    def toggle(self, directory: Directory) -> None:
        self.expanded[directory.path] = not self.is_expanded(directory)

    def toggle_state(self, state: compare.State) -> None:
        """Show or hide entries of a state."""
        if state in self.shown:
            self.shown.remove(state)
        else:
            self.shown.add(state)

    def rows(self) -> List[Row]:
        """Rows to show: directories first, sorted, then files in order."""
        rows = []  # type: List[Row]
        self._add_rows(self.tree(), rows)
        return rows

    def _add_rows(self, directory: Directory, rows: List[Row]) -> None:
        for name in sorted(directory.directories):
            child = directory.directories[name]
            rows.append(child)
            if self.is_expanded(child):
                self._add_rows(child, rows)
        rows.extend(directory.files)

    def pick_state(self, row: Row) -> Pick:
        paths = _paths(row)
        count = sum(1 for path in paths if path in self.picked)
        if paths and count == len(paths):
            return Pick.ALL
        return Pick.SOME if count else Pick.NONE

    def pick(self, row: Row, picked: bool) -> None:
        """Pick or unpick a file, or every file below a directory."""
        if picked:
            self.picked.update(_paths(row))
        else:
            self.picked.difference_update(_paths(row))

    def toggle_pick(self, row: Row) -> None:
        """Pick a row unless it is fully picked, then unpick it."""
        self.pick(row, self.pick_state(row) is not Pick.ALL)

    def picked_paths(
        self, direction: Union[None, transfer.Direction] = None
    ) -> List[str]:
        """Shown, picked paths; with a direction, only those on its source."""
        return [
            entry.path
            for entry in self.shown_entries()
            if entry.path in self.picked and _has_source(entry, direction)
        ]


def _paths(row: Row) -> List[str]:
    if isinstance(row, Directory):
        return [entry.path for entry in row.entries]
    return [row.entry.path]


def _has_source(
    entry: compare.Entry, direction: Union[None, transfer.Direction]
) -> bool:
    if direction is None:
        return True
    if direction is transfer.Direction.LEFT_TO_RIGHT:
        return entry.left is not None
    return entry.right is not None
