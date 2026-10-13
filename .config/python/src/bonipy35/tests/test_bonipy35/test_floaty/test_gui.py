#!/usr/bin/env python3

# Widget methods are deliberately exercised without constructing real widgets.
# pylint: disable=protected-access,import-outside-toplevel

import datetime
import sys
import types
import typing
from unittest.mock import Mock, patch

import pytest

from bonipy35.floaty.timer import Timer


@pytest.fixture(name="gui")
def fixture_gui(
    monkeypatch: pytest.MonkeyPatch,
) -> typing.Iterator[types.ModuleType]:
    # Fake only the Tk binding; run the real widget methods without a display.
    tk = types.ModuleType("tkinter")
    for name in ("Label", "Frame", "Event"):
        setattr(tk, name, object)
    font = types.ModuleType("tkinter.font")
    setattr(font, "Font", Mock())
    setattr(tk, "font", font)
    monkeypatch.setitem(sys.modules, "tkinter", tk)
    monkeypatch.setitem(sys.modules, "tkinter.font", font)
    from bonipy35.floaty import gui

    yield gui
    sys.modules.pop("bonipy35.floaty.gui", None)
    import bonipy35.floaty

    delattr(bonipy35.floaty, "gui")


@pytest.fixture(name="frame")
def fixture_frame(gui: types.ModuleType) -> typing.Any:
    frame = object.__new__(gui.TimerFrame)
    frame.timer = Timer(duration=datetime.timedelta(seconds=30))
    frame._after_id = None
    frame.after = Mock(return_value="callback")
    frame.after_cancel = Mock()
    frame.time_label = Mock()
    frame.pause_btn = Mock()
    return frame


class TestStep:
    @pytest.mark.parametrize(
        "remaining, delay", [(30, 1000), (1.5, 500), (0.0001, 1)]
    )
    def test_schedules_next_display_change(
        self, frame: typing.Any, remaining: float, delay: int
    ) -> None:
        frame.timer.remaining = datetime.timedelta(seconds=remaining)
        frame.timer.resume(now=0)
        frame.step(now=0)
        frame.after.assert_called_once_with(delay, frame.step)

    def test_expiry_stops_scheduling(self, frame: typing.Any) -> None:
        frame.timer.resume(now=0)
        frame.step(now=30)
        frame.after.assert_not_called()
        frame.time_label.config.assert_called_once_with(text="00")
        frame.pause_btn.config.assert_called_once_with(text="Resume")

    def test_resume_replaces_old_callback(self, frame: typing.Any) -> None:
        with patch("bonipy35.floaty.gui.time.monotonic", return_value=0):
            frame.resume()
            frame.resume()
        frame.after_cancel.assert_called_once_with("callback")
        assert frame._after_id == "callback"

    def test_pause_cancels_callback(self, frame: typing.Any) -> None:
        with patch("bonipy35.floaty.gui.time.monotonic", return_value=0):
            frame.resume()
            frame.toggle_pause()
        frame.after_cancel.assert_called_once_with("callback")
        assert frame._after_id is None
        assert not frame.timer.is_active()

    def test_reset_reschedules_running_timer(self, frame: typing.Any) -> None:
        with patch("bonipy35.floaty.gui.time.monotonic", return_value=0):
            frame.toggle_pause()
        with patch("bonipy35.floaty.gui.time.monotonic", return_value=10):
            frame.reset()
        frame.after_cancel.assert_called_once_with("callback")
        assert frame.timer.remaining.total_seconds() == 30
        assert frame.after.call_count == 2

    def test_destroy_cancels_only_for_own_widget(
        self, frame: typing.Any
    ) -> None:
        frame._after_id = "callback"
        frame._on_destroy(types.SimpleNamespace(widget=object()))
        frame.after_cancel.assert_not_called()
        frame._on_destroy(types.SimpleNamespace(widget=frame))
        frame.after_cancel.assert_called_once_with("callback")


class TestUpdateClock:
    def test_schedules_exact_minute_boundary(
        self, gui: types.ModuleType
    ) -> None:
        clock = object.__new__(gui.ClockLabel)
        clock.config = Mock()
        clock.after = Mock()
        now = datetime.datetime(2026, 1, 1, 12, 59, 30, 500000)
        with patch("bonipy35.floaty.gui.datetime") as dates:
            dates.datetime.now.return_value = now
            dates.timedelta = datetime.timedelta
            clock.update_clock()
        clock.config.assert_called_once_with(text="12:59")
        clock.after.assert_called_once_with(29500, clock.update_clock)


class TestFontSize:
    def test_finds_largest_fitting_height(
        self, gui: types.ModuleType
    ) -> None:
        font = Mock()
        font.metrics.side_effect = lambda: {
            "linespace": font.config.call_args.kwargs["size"] * 2
        }
        cache: dict[int, int] = {}
        assert (
            gui.get_maximum_font_size(
                15, size_to_height_cache=cache, font=font
            )
            == 7
        )
        assert (
            gui.get_font_height(7, size_to_height_cache=cache, font=font)
            == 14
        )

    def test_default_font_and_exact_height(
        self, gui: types.ModuleType
    ) -> None:
        with patch("bonipy35.floaty.gui.tkinter.font.Font") as factory:
            factory.return_value.metrics.return_value = {"linespace": 4}
            assert gui.get_maximum_font_size(3) == 1

    def test_resize_measures_actual_text(self, gui: types.ModuleType) -> None:
        class Label:
            def __getitem__(self, key: str) -> typing.Any:
                return {
                    "font": "custom",
                    "text": "12:34",
                    "padx": 0,
                    "pady": 0,
                }[key]

            config = Mock()

        label = Label()
        font = Mock()
        font.metrics.side_effect = lambda: {
            "linespace": font.config.call_args.kwargs["size"] * 2
        }
        font.measure.side_effect = (
            lambda text: font.config.call_args.kwargs["size"] * 5
        )
        with patch(
            "bonipy35.floaty.gui.tkinter.font.Font", return_value=font
        ):
            gui.ClockLabel.resize(
                label, font_size_to_height_cache={}, height=22, width=27
            )
        font.config.assert_called_with(size=5)
        assert all(
            call.args == ("12:34",) for call in font.measure.call_args_list
        )


class TestWrappingFrame:
    def test_configure_passes_current_dimensions_to_label(
        self, gui: types.ModuleType
    ) -> None:
        wrapper = object.__new__(gui.WrappingFrame)
        wrapper.clock_label = Mock()
        wrapper.font_size_to_height_cache = {}
        wrapper.winfo_width = Mock(return_value=320)
        wrapper.winfo_height = Mock(return_value=120)
        wrapper.on_configure(None)
        wrapper.clock_label.resize.assert_called_once_with(
            font_size_to_height_cache={}, height=120, width=320
        )
