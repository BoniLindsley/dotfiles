#!/usr/bin/env python3

# Keep this Python 3.5 compatible for Debian 9 support.
# pylint: disable=consider-using-f-string

# Still being worked on.
# pylint: disable=fixme

# Standard libraries.
import argparse
import enum
import datetime
import logging
import queue
import sys
import threading
import tkinter
import types
import typing

# TODO(Python 3.9): Use builtin.
from typing import Dict, List, Tuple, Type

# TODO(Python 3.10): Use | instead of Union.
from typing import Union

# External dependencies.
import dbus  # type: ignore[import-not-found]  # pylint: disable=import-error
import dbus.service  # type: ignore[import-not-found]  # pylint: disable=import-error
import dbus.mainloop.glib  # type: ignore[import-not-found]  # pylint: disable=import-error
import gi.repository.GLib  # type: ignore[import-not-found]  # pylint: disable=import-error

# Internal modules.
from .. import logging_ext

_logger = logging.getLogger(__name__)

_T = typing.TypeVar("_T")


class TkinterEvent:
    class Pattern:
        BUTTON_1 = "<Button-1>"
        CONTROL_T = "<Control-t>"
        CONTROL_W = "<Control-w>"
        DESTROY = "<Destroy>"
        NOTEBOOK_TAB_CHANGED = "<<NotebookTabChanged>>"
        ON_START = "<<OnStart>>"
        ON_STOP = "<<OnStop>>"

        ON_QUEUE = "<<OnQueue>>"

    class When:
        TAIL: typing.Literal["tail"] = "tail"


class TkQueue(typing.Generic[_T]):
    # Notify Tkinter parent with QUEUE when the queue is no longer empty.
    # Uses `event_generate` for Tkinter communication.
    # Likely sufficiently thread-safe.

    def __init__(
        self,
        parent: tkinter.Misc,
        *args: typing.Any,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._parent = parent
        self._pending = queue.Queue()  # type: queue.Queue[_T]
        # Stop sending events.
        # Sending events would error if parent no longer exists.
        self._is_stopped = False

    def get(self) -> Union[None, _T]:
        _pending = self._pending
        try:
            buffer = _pending.get_nowait()
        except queue.Empty:
            return None
        _pending.task_done()
        return buffer

    def put(self, buffer: _T) -> None:
        if self._is_stopped:
            return

        _pending = self._pending
        _pending.put_nowait(buffer)
        # Notify reader of new items.
        #
        # To reduce the number of notifications sent,
        # only send if the queue likely did not have any beforehand.
        # Since this object is the only writer into the queue,
        # if the count was greater than one,
        # it is safe to assume the queue was not empty,
        # and the queue is still be processed.
        is_generating_event = _pending.qsize() <= 1
        if is_generating_event:
            self._parent.event_generate(
                TkinterEvent.Pattern.ON_QUEUE, when=TkinterEvent.When.TAIL
            )

    def stop(self) -> None:
        self._is_stopped = True


class Reason(enum.Enum):
    OPENED = 0
    EXPIRED = 1
    DISMISSED = 2
    CLOSED = 3
    UNDEFINED = 4


class Notification:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: typing.Any,
        actions: List[typing.Any],
        app_icon: str,
        app_name: str,
        body: str,
        created_at: datetime.datetime,
        expire_timeout: int,
        hints: Dict[str, typing.Any],
        id: int,  # pylint: disable=redefined-builtin
        summary: str,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.actions = actions
        self.app_icon = app_icon
        self.app_name = app_name
        self.body = body
        self.created_at = created_at
        self.expire_timeout = expire_timeout
        self.hints = hints
        self.id = id
        self.summary = summary


class CloseNotificationEvent:
    def __init__(
        self, *args: typing.Any, notification_id: int, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.notification_id = notification_id


class NotificationClosedEvent:
    def __init__(
        self,
        *args: typing.Any,
        id_: int,
        state: Reason,
        **kwargs: typing.Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.id_ = id_
        self.state = state


class OpenNotificationEvent:
    def __init__(
        self, *args: typing.Any, notification: Notification, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.notification = notification


NotificationEvent = Union[
    CloseNotificationEvent, NotificationClosedEvent, OpenNotificationEvent
]


class Dispatcher:
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        super().__init__(*args, **kwargs)
        self._last_id = 0
        self._notifications = {}  # type: dict[int, Notification]

        self.do_close_notification = None  # type: None | typing.Callable[[int], None]
        self.do_notify = None  # type: None | typing.Callable[[Notification], None]
        self.on_notification_closed = (
            None
        )  # type: None | typing.Callable[[int, int], None]

    def close_notification(self, notification_id: int) -> None:
        notification = self._notifications.get(notification_id, None)
        if notification is None:
            return
        do_close_notification = self.do_close_notification
        if do_close_notification is not None:
            do_close_notification(notification_id)

    def notification_closed(self, notification_id: int, reason: int) -> None:
        notification = self._notifications.pop(notification_id, None)
        if notification is None:
            return
        on_notification_closed = self.on_notification_closed
        if on_notification_closed is not None:
            on_notification_closed(notification.id, reason)

    def notify(self, notification: Notification) -> None:
        notification_id = notification.id
        if notification_id == 0:
            self._last_id += 1
            notification_id = self._last_id
            notification.id = notification_id
        _logger.log(logging_ext.TRACE, "Received notification %s", notification.id)
        self._notifications[notification_id] = notification
        do_notify = self.do_notify
        if do_notify is not None:
            do_notify(notification)


class DbusThread(threading.Thread):
    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        self.glib_loop = gi.repository.GLib.MainLoop()
        kwargs.setdefault("daemon", True)
        kwargs.setdefault("target", self.glib_loop.run)
        super().__init__(*args, **kwargs)

    def __enter__(self) -> None:
        _logger.info("Starting notification daemon thread.")
        self.start()

    def __exit__(  # type: ignore[return]
        self,
        type_: Union[None, Type[BaseException]],
        value: Union[None, BaseException],
        traceback: Union[None, types.TracebackType],
    ) -> Union[None, bool]:
        _logger.info("Stopping notification daemon thread.")
        self.glib_loop.quit()


class Service(dbus.service.Object):  # type: ignore[misc]
    IFACE = "org.freedesktop.Notifications"
    PATH = "/org/freedesktop/Notifications"

    def __init__(
        self,
        dispatcher: Dispatcher,
    ) -> None:
        _logger.info("Starting notification service.")
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(self.IFACE, bus)
        super().__init__(bus_name, self.PATH)
        self._dispatcher = dispatcher
        dispatcher.on_notification_closed = self.on_notification_closed

    @dbus.service.method(IFACE, in_signature="u", out_signature="")  # type: ignore[misc]
    def CloseNotification(  # pylint: disable=invalid-name
        self, notification_id: int
    ) -> None:
        self._dispatcher.close_notification(notification_id)
        # self.NotificationClosed(notification_id, 3)  # 3 = closed by CloseNotification

    @dbus.service.method(IFACE, in_signature="", out_signature="as")  # type: ignore[misc]
    def GetCapabilities(self) -> List[str]:  # pylint: disable=invalid-name
        capabilities = {
            "action-icons": False,
            "actions": False,
            "body": True,
            "body-hyperlinks": False,
            "body-images": False,
            "body-markup": False,
            "icon-multi": False,
            "icon-static": False,
            "persistence": True,
            "sound": False,
        }
        return [
            capability
            for capability, is_supported in capabilities.items()
            if is_supported
        ]

    @dbus.service.method(IFACE, in_signature="", out_signature="ssss")  # type: ignore[misc]
    def GetServerInformation(  # pylint: disable=invalid-name
        self,
    ) -> Tuple[str, str, str, str]:
        name = "Python Notification Daemon"
        vendor = "Custom"
        version = "0.0.1"
        spec_version = "1.2"
        return (name, vendor, version, spec_version)

    @dbus.service.signal(IFACE, signature="uu")  # type: ignore[misc]
    def NotificationClosed(  # pylint: disable=invalid-name
        self, id_: int, reason: int
    ) -> None:
        del reason
        _logger.log(logging_ext.TRACE, "Signal closed notification %s", id_)

    @dbus.service.method(IFACE, in_signature="susssasa{sv}i", out_signature="u")  # type: ignore[misc]
    def Notify(  # pylint: disable=invalid-name,too-many-arguments,too-many-positional-arguments
        self,
        app_name: dbus.String,
        replaces_id: dbus.UInt32,
        app_icon: dbus.String,
        summary: dbus.String,
        body: dbus.String,
        actions: typing.Any,
        hints: dbus.Array,
        expire_timeout: dbus.Dictionary,
    ) -> dbus.UInt32:
        notification = Notification(
            id=replaces_id,
            actions=list(actions),
            app_icon=str(app_icon),
            app_name=str(app_name),
            body=str(body),
            created_at=datetime.datetime.now(),
            expire_timeout=int(expire_timeout),
            hints=dict(hints),
            summary=str(summary),
        )
        self._dispatcher.notify(notification)
        return dbus.UInt32(notification.id)

    def on_notification_closed(self, notification_id: int, reason: int) -> None:
        self.NotificationClosed(dbus.UInt32(notification_id), dbus.UInt32(reason))


class Window(tkinter.Toplevel):
    def __init__(  # pylint: disable=too-many-locals
        self,
        parent: tkinter.Misc,
        *args: typing.Any,
        notification: Notification,
        notification_event_queue: TkQueue[NotificationEvent],
        **kwargs: typing.Any
    ) -> None:
        super().__init__(parent, *args, **kwargs)
        _logger.log(logging_ext.TRACE, "Creating window %s", notification.id)
        self._notification = notification
        self._notification_event_queue = notification_event_queue

        font_name = "sans-serif"
        bg = "#222222"
        fg = "#cccccc"
        focused_fg = "#ffffff"
        unfocused_fg = "#888888"

        self.overrideredirect(True)
        self.attributes("-topmost", True)

        main_frame = tkinter.Frame(self, bg=bg)
        main_frame.pack(fill="both", expand=True)

        header = tkinter.Frame(main_frame, bg=bg)
        header.pack(fill="x", padx=10, pady=5)

        app_name = self._notification.app_name or "Notification"
        app_label = tkinter.Label(
            header, text=app_name, fg=unfocused_fg, bg=bg, font=(font_name, 9)
        )
        app_label.pack(side="left")

        close_btn = tkinter.Label(
            header, text="×", fg=unfocused_fg, bg=bg, font=(font_name, 14)
        )
        close_btn.pack(side="right")
        close_btn.bind(TkinterEvent.Pattern.BUTTON_1, self._dismiss)

        summary = self._notification.summary
        if summary:
            sum_label = tkinter.Label(
                main_frame,
                text=summary,
                fg=focused_fg,
                bg=bg,
                font=(font_name, 11, "bold"),
                anchor="w",
                wraplength=280,
            )
            sum_label.pack(fill="x", padx=10)

        body = self._notification.body
        if body:
            body_label = tkinter.Label(
                main_frame,
                text=body,
                fg=fg,
                bg=bg,
                font=(font_name, 10),
                anchor="w",
                wraplength=280,
                justify="left",
            )
            body_label.pack(fill="x", padx=10, pady=(2, 5))

        is_dismiss_on_click = True
        if is_dismiss_on_click:
            self.bind(TkinterEvent.Pattern.BUTTON_1, self._dismiss)

        self.update_idletasks()

        expire_timeout = notification.expire_timeout
        if expire_timeout == -1:
            expire_timeout = 5000
        expire_timeout = max(0, expire_timeout)
        self.after(expire_timeout, self._expire)

    def _expire(self) -> None:
        self._notification_event_queue.put(
            NotificationClosedEvent(id_=self._notification.id, state=Reason.EXPIRED)
        )
        self.destroy()

    def _dismiss(self, event: tkinter.Event) -> None:
        del event
        self._notification_event_queue.put(
            NotificationClosedEvent(id_=self._notification.id, state=Reason.DISMISSED)
        )
        self.destroy()


class Application(tkinter.Tk):
    def __init__(
        self, *args: typing.Any, dispatcher: Dispatcher, **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._dispatcher = dispatcher

        self._notification_event_queue = TkQueue(
            parent=self
        )  # type: TkQueue[NotificationEvent]
        self._windows = {}  # type: dict[int, Window]
        self._last_cleared_window_heights = []  # type: list[int]

        self.withdraw()
        self.title(__package__)
        self.bind(TkinterEvent.Pattern.ON_QUEUE, self._on_queue)
        # self.protocol("WM_DELETE_WINDOW", self.withdraw)

        dispatcher.do_close_notification = self.close_notification_threadsafe
        dispatcher.do_notify = self.open_notification_threadsafe

    def _close_notification(self, notification_id: int) -> None:
        window = self._windows.pop(notification_id, None)
        if window is None:
            return
        self._notification_event_queue.put(
            NotificationClosedEvent(id_=notification_id, state=Reason.CLOSED)
        )
        window.destroy()

    def _notification_closed(self, event: NotificationClosedEvent) -> None:
        windows = self._windows

        id_ = event.id_
        windows.pop(id_, None)
        self._dispatcher.notification_closed(id_, event.state.value)

        if not windows:
            self._last_cleared_window_heights.clear()

    def _on_queue(self, event: tkinter.Event) -> None:
        del event
        get = self._notification_event_queue.get
        while True:
            notification_event = get()
            if notification_event is None:
                break
            if isinstance(notification_event, OpenNotificationEvent):
                self._open_notification(notification_event.notification)
            elif isinstance(notification_event, NotificationClosedEvent):
                self._notification_closed(notification_event)
            else:
                self._close_notification(notification_event.notification_id)
        _logger.log(logging_ext.TRACE, "No more events.")

    def _open_notification(self, notification: Notification) -> None:
        notification_id = notification.id
        # TODO: If the ID is known, content should be changed
        # instead of reopening, as required by the specification.
        self._close_notification(notification_id)

        window = Window(
            self,
            notification=notification,
            notification_event_queue=self._notification_event_queue,
        )

        height = window.winfo_reqheight()
        screen_h = window.winfo_screenheight()
        padding = 32
        last_cleared_window_heights = self._last_cleared_window_heights
        y = (
            screen_h
            - (padding * 2 + height)
            - (
                sum(last_cleared_window_heights)
                + (len(last_cleared_window_heights) + 1) * padding
            )
        )

        width = 300
        x = padding

        geometry = "{width}x{height}+{x}+{y}".format(
            width=width, height=height, x=x, y=y
        )
        window.geometry(geometry)

        self._windows[notification_id] = window
        last_cleared_window_heights.append(height)

    def close_notification_threadsafe(self, notification_id: int) -> None:
        self._notification_event_queue.put(
            CloseNotificationEvent(notification_id=notification_id)
        )

    def open_notification_threadsafe(self, notification: Notification) -> None:
        self._notification_event_queue.put(
            OpenNotificationEvent(notification=notification)
        )


def run() -> int:
    with DbusThread():
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        dispatcher = Dispatcher()
        application = Application(dispatcher=dispatcher)
        service = Service(dispatcher=dispatcher)
        # TODO: This blocks until event handling is needed,
        # even when SIGINT is received.
        application.mainloop()
        del service
    return 0


def main(argv: Union[None, List[str]] = None) -> int:
    """Parse command line arguments and run corresponding functions."""

    if argv is None:
        argv = sys.argv

    logging_ext.set_up_logging(logger=_logger)

    argument_parser = argparse.ArgumentParser()
    logging_ext.add_verbose_flag(argument_parser)

    arguments = argument_parser.parse_args(argv[1:])
    logging_ext.set_logger_verbosity(logger=_logger, verbosity=arguments.verbosity)

    try:
        return run()
    except KeyboardInterrupt:
        return 2


if __name__ == "__main__":
    sys.exit(main())
