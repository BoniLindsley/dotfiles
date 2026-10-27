#!/usr/bin/env python3

# Standard libraries.
import curses
import datetime

from pathlib import Path
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.selector_loop import EventLoop
from bonipy35.curses_ext.counter import Data, async_run


class TestData:
    @pytest.mark.parametrize(
        "timestamp", ["2023-12-28T01:11:59", "2023-12-28T01:11:59.289951"]
    )
    def test_load_old_save(self, tmp_path: Path, timestamp: str) -> None:
        path = tmp_path / "data.json"
        path.write_text(
            '{"zenny": 10, "updated_at": "' + timestamp + '"}',
            encoding="utf-8",
        )
        data = Data.load(path)
        assert data.zenny == 10
        assert data.updated_at.year == 2023

    def test_save_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "data.json"
        data = Data.load(path)
        data.zenny = 12
        timestamp = data.updated_at
        data.save(path)
        data.save(path)
        assert data.updated_at == timestamp
        assert isinstance(data.updated_at, datetime.datetime)
        loaded = Data.load(path)
        assert loaded.zenny == 12
        assert loaded.updated_at == timestamp


class TestAsyncRun:
    def test_counter(
        self,
        loop: EventLoop,
        window: Mock,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.chdir(tmp_path)
        window.getch.side_effect = [
            curses.KEY_RESIZE,
            ord("+"),
            ord("s"),
            ord("q"),
        ] + [-1] * 20
        assert loop.run_until_complete(async_run()) == 0
        assert Data.load(tmp_path / "data.json").zenny == 1
