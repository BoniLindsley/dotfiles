#!/usr/bin/env python3

# Standard libraries.
import curses

from pathlib import Path
from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.curses_ext.asyncio_loop import EventLoop
from bonipy35.curses_ext.editor import Editor, async_run


@pytest.fixture(name="pad")
def fixture_pad(monkeypatch: pytest.MonkeyPatch) -> Mock:
    pad = Mock()
    pad.lines = [""] * 5
    pad.getmaxyx.return_value = (5, 20)
    pad.getyx.return_value = (2, 3)
    pad.instr.side_effect = (
        lambda row, _column, width: pad.lines[row]
        .ljust(width)
        .encode("ascii")
    )
    pad.erase.side_effect = lambda: pad.lines.__setitem__(
        slice(None), [""] * 5
    )
    pad.addstr.side_effect = lambda row, _column, line: pad.lines.__setitem__(
        row, line
    )
    monkeypatch.setattr(curses, "newpad", Mock(return_value=pad))
    monkeypatch.setattr("curses.textpad.Textbox", Mock())
    return pad


@pytest.fixture(name="editor")
def fixture_editor(window: Mock, pad: Mock) -> Editor:
    del pad
    return Editor(window)


class TestEditor:
    class TestInit:
        @pytest.mark.parametrize("dimensions", [(2, 80), (24, 3)])
        def test_small_terminal(
            self, window: Mock, dimensions: tuple[int, int]
        ) -> None:
            window.getmaxyx.return_value = dimensions
            with pytest.raises(ValueError, match="at least"):
                Editor(window)

    class TestText:
        def test_blank_lines_and_cursor(
            self, editor: Editor, pad: Mock
        ) -> None:
            pad.lines = ["", "a  ", "", "b", ""]
            assert editor.text() == "\na\n\nb\n"
            pad.move.assert_called_with(2, 3)

        def test_empty(self, editor: Editor) -> None:
            assert editor.text() == ""

    class TestLoad:
        @pytest.mark.parametrize(
            "raw, expected",
            [
                (b"a\n\nb\n", "a\n\nb\n"),
                (b"", ""),
                (b"a\r\nb", "a\nb\n"),
                (b"\tX\n", "    X\n"),
            ],
        )
        def test_normalization(
            self, editor: Editor, tmp_path: Path, raw: bytes, expected: str
        ) -> None:
            path = tmp_path / "input.txt"
            path.write_bytes(raw)
            editor.load(path)
            assert editor.path == path
            assert editor.text() == expected
            assert editor.saved_text == expected

        @pytest.mark.parametrize(
            "raw",
            [
                b"x" * 4097,
                b"\x80",
                b"\x07",
                b"x" * 20,
                b"x\n" * 6,
                b"\t" * 4096,
            ],
        )
        def test_invalid_preserves_buffer(
            self, editor: Editor, pad: Mock, tmp_path: Path, raw: bytes
        ) -> None:
            pad.lines[0] = "original"
            path = tmp_path / "input.txt"
            path.write_bytes(raw)
            with pytest.raises(ValueError):
                editor.load(path)
            assert editor.text() == "original\n"
            assert editor.path is None

    class TestExecute:
        @pytest.mark.parametrize("command", ["quit", "new", "edit other.txt"])
        def test_dirty_protection(
            self, editor: Editor, pad: Mock, command: str
        ) -> None:
            pad.lines[0] = "unsaved"
            with pytest.raises(ValueError, match="Unsaved"):
                editor.execute(command)
            assert editor.execute("q!")
            assert not editor.execute("n!")
            assert editor.text() == ""
            assert editor.path is None

        def test_edit_and_write(
            self, editor: Editor, pad: Mock, tmp_path: Path
        ) -> None:
            source = tmp_path / "source.txt"
            source.write_text("original\n", encoding="ascii")
            assert not editor.execute("e " + str(source))
            pad.lines[0] = "changed"
            assert not editor.execute("w")
            assert source.read_text(encoding="ascii") == "changed\n"
            destination = tmp_path / "space name.txt"
            assert not editor.execute('write "' + str(destination) + '"')
            assert destination.read_text(encoding="ascii") == "changed\n"
            assert editor.path == destination
            assert editor.saved_text == "changed\n"
            assert editor.execute("quit")

        def test_force_edit(
            self, editor: Editor, pad: Mock, tmp_path: Path
        ) -> None:
            pad.lines[0] = "unsaved"
            path = tmp_path / "other.txt"
            path.write_bytes(b"loaded")
            editor.execute("edit! " + str(path))
            assert editor.text() == "loaded\n"

        @pytest.mark.parametrize(
            "command",
            ["unknown", "edit", "quit extra", "write a b", 'edit "'],
        )
        def test_bad_command(self, editor: Editor, command: str) -> None:
            with pytest.raises(ValueError):
                editor.execute(command)

        def test_empty_and_redraw(
            self, editor: Editor, pad: Mock, window: Mock
        ) -> None:
            assert not editor.execute("")
            assert not editor.execute("redraw")
            window.clearok.assert_called_with(True)
            pad.touchwin.assert_called_once()

        def test_write_without_name(self, editor: Editor) -> None:
            with pytest.raises(ValueError, match="filename"):
                editor.execute("write")

        def test_write_size_limit(
            self,
            editor: Editor,
            pad: Mock,
            tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch,
        ) -> None:
            monkeypatch.setattr("bonipy35.curses_ext.editor.MAX_FILE_SIZE", 2)
            pad.lines[0] = "long"
            path = tmp_path / "out.txt"
            with pytest.raises(ValueError, match="exceeds"):
                editor.execute("write " + str(path))
            assert not path.exists()

    class TestHandleKey:
        def test_modes_and_editing(self, editor: Editor) -> None:
            assert not editor.handle_key(ord("x"))
            assert not editor.handle_key(ord("i"))
            assert editor.mode == "insert"
            editor.handle_key(ord("a"))
            editor.textbox.do_command.assert_called_with(ord("a"))  # type: ignore[attr-defined]
            editor.handle_key(curses.KEY_DC)
            editor.textbox.do_command.assert_called_with(4)  # type: ignore[attr-defined]
            editor.handle_key(
                7
            )  # Textbox's usual terminator does not change modes.
            assert editor.mode == "insert"
            editor.handle_key(12)
            editor.handle_key(27)
            assert editor.mode == "normal"
            editor.handle_key(12)
            editor.handle_key(ord(":"))
            assert editor.mode == "command"
            for key in map(ord, "quitx"):
                editor.handle_key(key)
            editor.handle_key(curses.KEY_BACKSPACE)
            assert editor.command == "quit"
            assert editor.handle_key(10)
            assert editor.mode == "normal"

        def test_cancel_and_command_errors(self, editor: Editor) -> None:
            editor.handle_key(ord(":"))
            editor.handle_key(27)
            assert editor.command == ""
            editor.handle_key(ord(":"))
            editor.handle_key(0)
            editor.command = "x" * 1024
            editor.handle_key(ord("x"))
            assert len(editor.command) == 1024
            editor.command = "unknown"
            assert not editor.handle_key(13)
            assert "Use quit" in editor.message
            editor.handle_key(ord(":"))
            editor.command = "edit /nonexistent/bonipy35-file.txt"
            assert not editor.handle_key(curses.KEY_ENTER)
            assert "No such file" in editor.message

        def test_resize(self, editor: Editor, window: Mock) -> None:
            editor.handle_key(curses.KEY_RESIZE)
            window.clearok.assert_called_with(True)

    class TestRender:
        def test_modes_and_resize(
            self, editor: Editor, pad: Mock, window: Mock
        ) -> None:
            editor.render()
            pad.noutrefresh.assert_called()
            editor.mode = "command"
            editor.command = "write"
            pad.lines[0] = "dirty"
            editor.render()
            assert any(
                ":write" in call.args
                for call in window.addnstr.call_args_list
            )
            assert any(
                "COMMAND [No name] *" in call.args
                for call in window.addnstr.call_args_list
            )
            window.getmaxyx.return_value = (1, 1)
            pad.noutrefresh.reset_mock()
            editor.render()
            pad.noutrefresh.assert_not_called()


class TestAsyncRun:
    def test_quit(self, loop: EventLoop, window: Mock, pad: Mock) -> None:
        del pad
        window.getch.side_effect = list(map(ord, ":quit\n")) + [-1] * 20
        assert loop.run_until_complete(async_run()) == 0
