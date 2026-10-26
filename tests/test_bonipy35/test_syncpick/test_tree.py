#!/usr/bin/env python3

# Standard libraries.
import datetime

from typing import List

# External dependencies.
import pytest

# Internal modules.
from bonipy35.syncpick.compare import Entry, Side, State
from bonipy35.syncpick.transfer import Direction
from bonipy35.syncpick.tree import Directory, File, Model, Pick, Row, build

SIDE = Side(size=1, modified=datetime.datetime(2026, 1, 1))


def entry(path: str, state: State) -> Entry:
    return Entry(
        path=path,
        state=state,
        left=None if state is State.RIGHT_ONLY else SIDE,
        right=None if state is State.LEFT_ONLY else SIDE,
    )


ENTRIES = [
    entry("same/a", State.SAME),
    entry("same/b", State.SAME),
    entry("sub/deep/changed", State.DIFFERENT),
    entry("sub/deep/new", State.LEFT_ONLY),
    entry("sub/theirs", State.RIGHT_ONLY),
    entry("top", State.SAME),
]


@pytest.fixture(name="model")
def fixture_model() -> Model:
    return Model(ENTRIES)


def describe(rows: List[Row]) -> List[str]:
    """Rows as indented names, directories ending with ``/``."""
    return [
        "  " * row.depth
        + (row.name + "/" if isinstance(row, Directory) else row.name)
        for row in rows
    ]


def directory(model: Model, path: str) -> Directory:
    for row in model.rows():
        if isinstance(row, Directory) and row.path == path:
            return row
    raise KeyError(path)


def file(model: Model, path: str) -> File:
    for row in model.rows():
        if isinstance(row, File) and row.entry.path == path:
            return row
    raise KeyError(path)


class TestBuild:
    def test_empty(self) -> None:
        root = build([])
        assert (root.path, root.depth) == ("", -1)
        assert not root.directories and not root.files and not root.entries

    def test_nesting(self) -> None:
        root = build(ENTRIES)
        assert sorted(root.directories) == ["same", "sub"]
        assert [file.name for file in root.files] == ["top"]
        assert root.entries == ENTRIES
        deep = root.directories["sub"].directories["deep"]
        assert (deep.name, deep.path, deep.depth) == ("deep", "sub/deep/", 1)
        assert [(file.name, file.depth) for file in deep.files] == [
            ("changed", 2),
            ("new", 2),
        ]
        assert deep.entries == ENTRIES[2:4]

    def test_counts(self) -> None:
        root = build(ENTRIES)
        assert root.directories["sub"].counts() == {
            State.DIFFERENT: 1,
            State.LEFT_ONLY: 1,
            State.RIGHT_ONLY: 1,
        }
        assert root.directories["same"].counts() == {State.SAME: 2}


class TestModel:
    class TestRows:
        def test_default_expansion(self, model: Model) -> None:
            # Directories with only identical files start collapsed.
            assert describe(model.rows()) == [
                "same/",
                "sub/",
                "  deep/",
                "    changed",
                "    new",
                "  theirs",
                "top",
            ]

        def test_toggle(self, model: Model) -> None:
            model.toggle(directory(model, "same/"))
            model.toggle(directory(model, "sub/"))
            assert describe(model.rows()) == [
                "same/",
                "  a",
                "  b",
                "sub/",
                "top",
            ]
            assert model.expanded == {"same/": True, "sub/": False}

        def test_hidden_state(self, model: Model) -> None:
            model.toggle_state(State.SAME)
            model.toggle_state(State.RIGHT_ONLY)
            assert State.SAME not in model.shown
            # Directories with nothing shown below them disappear.
            assert describe(model.rows()) == [
                "sub/",
                "  deep/",
                "    changed",
                "    new",
            ]
            model.toggle_state(State.SAME)
            assert describe(model.rows())[0] == "same/"

    class TestPick:
        def test_file(self, model: Model) -> None:
            row = file(model, "sub/theirs")
            model.pick(row, True)
            assert model.picked == {"sub/theirs"}
            assert model.pick_state(row) is Pick.ALL
            assert model.pick_state(directory(model, "sub/")) is Pick.SOME
            model.pick(row, False)
            assert model.pick_state(row) is Pick.NONE

        def test_directory(self, model: Model) -> None:
            model.pick(directory(model, "sub/"), True)
            assert model.picked == {
                "sub/deep/changed",
                "sub/deep/new",
                "sub/theirs",
            }
            assert model.pick_state(directory(model, "sub/deep/")) is Pick.ALL

        def test_directory_picks_only_shown(self, model: Model) -> None:
            model.toggle_state(State.RIGHT_ONLY)
            model.pick(directory(model, "sub/"), True)
            assert model.picked == {"sub/deep/changed", "sub/deep/new"}
            # A file shown again is not picked, so the directory is partly.
            model.toggle_state(State.RIGHT_ONLY)
            assert model.pick_state(directory(model, "sub/")) is Pick.SOME

        def test_toggle_pick(self, model: Model) -> None:
            sub = directory(model, "sub/")
            model.pick(file(model, "sub/theirs"), True)
            model.toggle_pick(sub)
            assert model.pick_state(sub) is Pick.ALL
            model.toggle_pick(sub)
            assert model.picked == set()

    class TestPickedPaths:
        def test_by_direction(self, model: Model) -> None:
            model.pick(directory(model, "sub/"), True)
            assert model.picked_paths() == [
                "sub/deep/changed",
                "sub/deep/new",
                "sub/theirs",
            ]
            assert model.picked_paths(Direction.LEFT_TO_RIGHT) == [
                "sub/deep/changed",
                "sub/deep/new",
            ]
            assert model.picked_paths(Direction.RIGHT_TO_LEFT) == [
                "sub/deep/changed",
                "sub/theirs",
            ]

        def test_only_shown(self, model: Model) -> None:
            model.pick(directory(model, "sub/"), True)
            model.toggle_state(State.LEFT_ONLY)
            assert model.picked_paths() == ["sub/deep/changed", "sub/theirs"]

    class TestRefresh:
        def test_keeps_present_picks(self, model: Model) -> None:
            model.pick(directory(model, "sub/"), True)
            model.toggle(directory(model, "same/"))
            model.refresh([entry("sub/theirs", State.SAME)])
            assert model.picked == {"sub/theirs"}
            assert model.expanded == {"same/": True}
            assert describe(model.rows()) == ["sub/"]
