#!/usr/bin/env python3

# Standard libraries.
import curses
import datetime
import pathlib
import typing

from unittest.mock import Mock

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm import cli
from bonipy35.alarm.client import Client, interface_main
from bonipy35.alarm.gui import GUIClient, run as run_gui
from bonipy35.alarm.tui import TUIClient


@pytest.fixture(name="ui_connection")
def fixture_ui_connection() -> Mock:
    connection = Mock(spec=Client)
    connection.sock = Mock()
    connection.snapshot = {
        "items": [
            {
                "id_": 0,
                "name": "Tea",
                "state": "active",
                "end_time": "deadline",
                "remaining": 60,
            }
        ],
        "notifications": [{"id_": 0, "name": "Tea", "missed": True}],
    }
    connection.buffered = False
    return connection


@pytest.fixture(name="gui")
def fixture_gui(ui_connection: Mock) -> GUIClient:
    tk = Mock()
    tk.Listbox.return_value.curselection.return_value = (0,)
    tk.Label.side_effect = [Mock(), Mock()]
    return GUIClient(ui_connection, tk)


@pytest.fixture(name="tui")
def fixture_tui(ui_connection: Mock) -> TUIClient:
    window = Mock()
    window.getmaxyx.return_value = (24, 80)
    return TUIClient(ui_connection, window)


class TestGUIRender:
    def test_uses_socket_readiness_and_persistent_notification_list(
        self, gui: GUIClient, ui_connection: Mock
    ) -> None:
        gui.root.createfilehandler.assert_called_once_with(
            ui_connection.sock, gui.tk.READABLE, gui.on_readable
        )
        gui.notifications.config.assert_called_with(
            text="Notification 0: Tea (missed)"
        )
        ui_connection.snapshot["notifications"] = []
        gui.on_readable(None, 0)
        ui_connection.receive.assert_called_once()
        gui.notifications.config.assert_called_with(text="")
        gui.items.selection_set.assert_called_with(0)

    def test_buffered_event_after_response_is_rendered_without_new_socket_readiness(
        self, gui: GUIClient, ui_connection: Mock
    ) -> None:
        ui_connection.buffered = True

        def receive() -> None:
            ui_connection.snapshot["notifications"] = []
            ui_connection.buffered = False

        ui_connection.receive.side_effect = receive
        gui.render()
        gui.notifications.config.assert_called_with(text="")

    def test_disconnect_removes_readiness_handler(
        self, gui: GUIClient, ui_connection: Mock
    ) -> None:
        ui_connection.receive.side_effect = EOFError("Disconnected")
        gui.on_readable(None, 0)
        gui.status.config.assert_called_with(text="Disconnected")
        gui.root.deletefilehandler.assert_called_once_with(ui_connection.sock)

    def test_close_cleans_up_handler(
        self, gui: GUIClient, ui_connection: Mock
    ) -> None:
        gui.close()
        gui.root.deletefilehandler.assert_called_once_with(ui_connection.sock)
        gui.root.destroy.assert_called_once()


class TestGUICommand:
    @pytest.mark.parametrize(
        "action", ["pause", "resume", "stop", "restart", "dismiss", "delete"]
    )
    def test_selected_item_command(
        self,
        gui: GUIClient,
        ui_connection: Mock,
        action: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module", Mock()
        )
        gui.command(action)
        ui_connection.request.assert_called_once_with(action, id_=0)

    def test_timer_creation(
        self,
        gui: GUIClient,
        ui_connection: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        dialog = Mock()
        dialog.askstring.return_value = "10m"
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module",
            Mock(return_value=dialog),
        )
        gui.command("timer")
        ui_connection.request.assert_called_once_with("timer", duration=600)

    @pytest.mark.parametrize("action", ["alarm", "reschedule"])
    def test_alarm_creation_and_reschedule(
        self,
        gui: GUIClient,
        ui_connection: Mock,
        action: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        dialog = Mock()
        dialog.askstring.return_value = "2026-10-12 12:00"
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module",
            Mock(return_value=dialog),
        )
        resolver = Mock(
            return_value=datetime.datetime(
                2026, 10, 12, 12, tzinfo=datetime.timezone.utc
            )
        )
        # Dotted targets use importlib.import_module, already mocked above.
        monkeypatch.setattr(cli, "parse_alarm_time", resolver)
        gui.command(action)
        if action == "alarm":
            ui_connection.request.assert_called_once_with(
                "alarm", end_time="20261012T120000.000000Z"
            )
        else:
            ui_connection.request.assert_called_once_with(
                "reschedule", end_time="20261012T120000.000000Z", id_=0
            )

    def test_cancelled_dialog_does_not_create(
        self,
        gui: GUIClient,
        ui_connection: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        dialog = Mock()
        dialog.askstring.return_value = None
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module",
            Mock(return_value=dialog),
        )
        gui.command("alarm")
        ui_connection.request.assert_not_called()

    def test_invalid_duration_shows_error(
        self,
        gui: GUIClient,
        ui_connection: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        dialog = Mock()
        dialog.askstring.return_value = "invalid"
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module",
            Mock(return_value=dialog),
        )
        gui.command("timer")
        ui_connection.request.assert_not_called()
        assert "duration" in gui.status.config.call_args.kwargs["text"]

    def test_no_selection_shows_error(
        self,
        gui: GUIClient,
        ui_connection: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module", Mock()
        )
        gui.items.curselection.return_value = ()
        gui.command("dismiss")
        ui_connection.request.assert_not_called()
        gui.status.config.assert_called_with(text="Select an item first")


class TestGUIRun:
    def test_missing_tk_is_reported(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "bonipy35.alarm.gui.importlib.import_module",
            Mock(side_effect=ImportError),
        )
        with pytest.raises(RuntimeError, match="Tk is unavailable"):
            run_gui(tmp_path)


class TestTUIHandle:
    @pytest.mark.parametrize(
        "key,action",
        [
            ("p", "pause"),
            ("s", "stop"),
            ("r", "restart"),
            ("d", "delete"),
            ("x", "dismiss"),
        ],
    )
    def test_selected_item_commands(
        self, tui: TUIClient, ui_connection: Mock, key: str, action: str
    ) -> None:
        assert tui.handle(ord(key))
        ui_connection.request.assert_called_once_with(action, id_=0)

    def test_paused_item_resumes(
        self, tui: TUIClient, ui_connection: Mock
    ) -> None:
        ui_connection.snapshot["items"][0]["state"] = "paused"
        tui.handle(ord("p"))
        ui_connection.request.assert_called_once_with("resume", id_=0)

    def test_empty_list_and_unknown_key_do_not_issue_commands(
        self, tui: TUIClient, ui_connection: Mock
    ) -> None:
        ui_connection.snapshot["items"] = []
        assert tui.handle(ord("x"))
        assert tui.handle(curses.KEY_RESIZE)
        ui_connection.request.assert_not_called()

    def test_navigation_and_quit(self, tui: TUIClient) -> None:
        assert tui.handle(ord("j")) and tui.selected == 0
        assert tui.handle(ord("k")) and tui.selected == 0
        assert not tui.handle(ord("q"))

    def test_operation_error_remains_visible(
        self, tui: TUIClient, ui_connection: Mock
    ) -> None:
        ui_connection.request.side_effect = ValueError("Not active")
        assert tui.handle(ord("p"))
        assert tui.message == "Not active"

    def test_timer_creation_and_prompt_cleanup(
        self,
        tui: TUIClient,
        ui_connection: Mock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("bonipy35.alarm.tui.curses.echo", Mock())
        noecho = Mock()
        monkeypatch.setattr("bonipy35.alarm.tui.curses.noecho", noecho)
        typing.cast(Mock, tui.window).getstr.return_value = b"10m"
        assert tui.handle(ord("t"))
        ui_connection.request.assert_called_once_with("timer", duration=600)
        noecho.assert_called_once()
        typing.cast(Mock, tui.window).nodelay.assert_called_with(True)


class TestTUIDraw:
    def test_small_terminal_keeps_draw_within_bounds(
        self, tui: TUIClient
    ) -> None:
        window = typing.cast(Mock, tui.window)
        window.getmaxyx.return_value = (3, 10)
        tui.draw()
        assert window.addnstr.call_count == 2
        for call in window.addnstr.call_args_list:
            assert call.args[0] < 2
            assert call.args[3] == 9

    def test_notification_is_displayed(self, tui: TUIClient) -> None:
        window = typing.cast(Mock, tui.window)
        tui.draw()
        assert any(
            "Notification 0" in call.args[2]
            for call in window.addnstr.call_args_list
        )


class TestInterfaceMain:
    def test_directory_argument(self, tmp_path: pathlib.Path) -> None:
        run = Mock(return_value=0)
        assert (
            interface_main(
                run, ["gui", "--directory", str(tmp_path)], "description"
            )
            == 0
        )
        run.assert_called_once_with(tmp_path)

    @pytest.mark.parametrize(
        "error,code", [(ValueError("bad"), 1), (KeyboardInterrupt(), 0)]
    )
    def test_errors_and_interrupt(
        self, error: BaseException, code: int
    ) -> None:
        assert (
            interface_main(Mock(side_effect=error), ["gui"], "description")
            == code
        )
