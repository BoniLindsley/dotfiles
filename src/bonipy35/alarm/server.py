#!/usr/bin/env python3
"""Single-owner, readiness-driven local service."""

# Standard libraries.
import argparse
import contextlib
import datetime
import errno
import fcntl
import logging
import os
import pathlib
import selectors
import signal
import socket
import sys
import tempfile
import typing

from typing import Dict, List, Union

# Internal modules.
from . import clock, data, paths, protocol

_logger = logging.getLogger(__name__)


class Connection:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.decoder = protocol.Decoder()
        self.output = b""


class Server:
    def __init__(self, *, directory: pathlib.Path) -> None:
        self.directory = paths.prepare_directory(directory)
        self._resources = contextlib.ExitStack()
        self.connections = []  # type: List[Connection]
        self.stopping = False
        self._shutdown_requested = False
        try:
            lock = self._resources.enter_context(
                (self.directory / "server.lock").open("a+")
            )
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.state_path = self.directory / "state.json"
            try:
                self.user_data = data.UserData.model_validate_json(
                    self.state_path.read_text(encoding="utf-8")
                )
            except FileNotFoundError:
                self.user_data = data.UserData()
            self.check_capacity()
            # Missed deadlines retain their persisted lifecycle status.
            if self.user_data.update(data.utc_now(), missed=True):
                self.save()
            self.selector = self._resources.enter_context(
                selectors.DefaultSelector()
            )
            self.deadline_clock = clock.DeadlineClock()
            self._resources.callback(self.deadline_clock.close)
            self.selector.register(
                self.deadline_clock.fd, selectors.EVENT_READ, "deadline"
            )
            self.listener = self._resources.enter_context(
                socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            )
            endpoint = self.directory / "socket"
            if endpoint.exists():
                endpoint.unlink()
            self.listener.bind(str(endpoint))
            self._resources.callback(endpoint.unlink)
            self.listener.listen()
            self.listener.setblocking(False)
            self.selector.register(
                self.listener, selectors.EVENT_READ, "accept"
            )
            self._wakeup_read, self._wakeup_write = socket.socketpair()
            self._resources.enter_context(self._wakeup_read)
            self._resources.enter_context(self._wakeup_write)
            self._wakeup_read.setblocking(False)
            self._wakeup_write.setblocking(False)
            self.selector.register(
                self._wakeup_read, selectors.EVENT_READ, "stop"
            )
            self.rearm()
        except BaseException:
            self._resources.close()
            raise

    def save(self) -> None:
        descriptor, filename = tempfile.mkstemp(
            prefix="state-", suffix=".tmp", dir=str(self.directory)
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                output.write(self.user_data.model_dump_json())
                output.flush()
                os.fsync(output.fileno())
            os.replace(filename, str(self.state_path))
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

    def rearm(self) -> None:
        self.deadline_clock.arm(self.user_data.next_deadline())

    def snapshot(self) -> Dict[str, typing.Any]:
        return self.user_data.snapshot(data.utc_now())

    def check_capacity(self) -> None:
        snapshot = self.snapshot()
        # Reserve every item's eventual notification and timestamp expansion,
        # so expiry cannot turn a previously accepted state into an oversized frame.
        snapshot["notifications"] = [
            {
                "id_": item.id_,
                "name": item.name,
                "occurred_at": data.Datetime.model_dump(item.end_time),
                "missed": True,
            }
            for item in self.user_data.alarms
        ]
        budget = protocol.MAX_FRAME - 128 * (len(self.user_data.alarms) + 1)
        if len(protocol.encode({"snapshot": snapshot})) > budget:
            raise ValueError("State exceeds frame limit")

    def queue(
        self, connection: Connection, message: Dict[str, typing.Any]
    ) -> None:
        connection.output += protocol.encode(message)
        # Disconnect slow readers rather than growing an unbounded event queue.
        if len(connection.output) > protocol.MAX_FRAME * 4:
            self.drop(connection)
            return
        self.selector.modify(
            connection.sock,
            selectors.EVENT_READ | selectors.EVENT_WRITE,
            connection,
        )

    def broadcast(self) -> None:
        event = {"event": "snapshot", "snapshot": self.snapshot()}
        for connection in list(self.connections):
            self.queue(connection, event)

    def expire(self) -> None:
        if self.user_data.update(data.utc_now()):
            try:
                self.save()
            except OSError as error:
                raise RuntimeError("Cannot persist expiry") from error
            self.broadcast()
        self.rearm()

    def operate(
        self,
        command: str,
        request: Dict[str, typing.Any],
        now: datetime.datetime,
    ) -> None:
        item = self.user_data.get(int(request["id_"]))
        if command == "delete":
            self.user_data.delete(item.id_)
        elif command == "pause":
            item.pause(now)
        elif command == "resume":
            item.resume(now)
        elif command == "stop":
            item.stop()
        elif command == "dismiss":
            item.dismiss(now)
        elif command == "restart":
            if not isinstance(item, data.Timer):
                raise ValueError("Only timers can be restarted")
            item.start(now)
        elif command == "reschedule":
            item.reschedule(
                data.Datetime.model_validate_datetime(request["end_time"])
            )
            item.update(now, missed=True)
        else:
            raise ValueError("Unknown command: {}".format(command))

    def execute(self, request: Dict[str, typing.Any]) -> None:
        command = request["command"]
        if not isinstance(command, str):
            raise ValueError("command must be a string")
        name = request.get("name", "")
        if not isinstance(name, str):
            raise ValueError("name must be a string")
        now = data.utc_now()
        if command in ("status", "notifications"):
            return
        if command == "alarm":
            item = self.user_data.add_alarm(
                end_time=data.Datetime.model_validate_datetime(
                    request["end_time"]
                ),
                name=name,
            )
            item.update(now, missed=True)
        elif command == "timer":
            self.user_data.add_timer(
                duration=datetime.timedelta(
                    seconds=float(request["duration"])
                ),
                now=now,
                name=request.get("name", ""),
            )
        elif command == "shutdown":
            self._shutdown_requested = True
            return
        else:
            self.operate(command, request, now)
        self.check_capacity()
        try:
            self.save()
        except OSError as error:
            # Persistence failures are service failures, not client disconnects.
            raise RuntimeError("Cannot persist alarm state") from error
        self.rearm()
        self.broadcast()

    def process(
        self, connection: Connection, request: Dict[str, typing.Any]
    ) -> None:
        request_id = request.get("request_id")
        self.expire()
        original = self.user_data
        self.user_data = data.UserData.model_validate(original.model_dump())
        try:
            if not isinstance(request_id, int) or isinstance(
                request_id, bool
            ):  # bool is not a request ID.
                raise ValueError("request_id must be an integer")
            self.execute(request)
        except (ValueError, KeyError, TypeError, OverflowError) as error:
            self.user_data = original
            self.queue(
                connection, {"request_id": request_id, "error": str(error)}
            )
        else:
            self.queue(
                connection,
                {"request_id": request_id, "snapshot": self.snapshot()},
            )

    def drop(self, connection: Connection) -> None:
        if connection in self.connections:
            self.connections.remove(connection)
            self.selector.unregister(connection.sock)
            connection.sock.close()

    def service(self, connection: Connection, mask: int) -> None:
        try:
            if mask & selectors.EVENT_READ:
                chunk = connection.sock.recv(65536)
                if not chunk:
                    self.drop(connection)
                    return
                for message in connection.decoder.feed(chunk):
                    self.process(connection, message)
                    if connection not in self.connections:
                        return
            if mask & selectors.EVENT_WRITE and connection.output:
                sent = connection.sock.send(connection.output)
                connection.output = connection.output[sent:]
                if not connection.output:
                    self.selector.modify(
                        connection.sock, selectors.EVENT_READ, connection
                    )
        except BlockingIOError:
            return
        except (OSError, ValueError):
            self.drop(connection)

    def run(self) -> None:
        try:
            while not self.stopping:
                for key, mask in self.selector.select():
                    if key.data == "accept":
                        sock, _address = self.listener.accept()
                        sock.setblocking(False)
                        connection = Connection(sock)
                        self.connections.append(connection)
                        self.selector.register(
                            sock, selectors.EVENT_READ, connection
                        )
                    elif key.data == "deadline":
                        self.deadline_clock.consume()
                        self.expire()
                    elif key.data == "stop":
                        self._wakeup_read.recv(1024)
                    else:
                        self.service(key.data, mask)
                if self._shutdown_requested and not any(
                    connection.output for connection in self.connections
                ):
                    self.stopping = True
        finally:
            self.close()

    def stop(self) -> None:
        self.stopping = True
        try:
            self._wakeup_write.send(b"s")
        except OSError as error:
            if error.errno not in (errno.EAGAIN, errno.EBADF):
                raise

    def close(self) -> None:
        for connection in list(self.connections):
            self.drop(connection)
        self._resources.close()


def main(argv: Union[None, List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv
    parser = argparse.ArgumentParser(description=__doc__)
    paths.add_directory_argument(parser)
    parser.add_argument("--ready-fd", type=int)
    arguments = parser.parse_args(argv[1:])
    ready = (
        socket.socket(fileno=arguments.ready_fd)
        if arguments.ready_fd is not None
        else None
    )
    try:
        server = Server(directory=arguments.directory)
    except (OSError, ValueError, KeyError, TypeError) as error:
        if ready is not None:
            ready.sendall(protocol.encode({"error": str(error)}))
            ready.close()
        _logger.error("Cannot start alarm server: %s", error)
        return 1
    if ready is not None:
        ready.sendall(protocol.encode({"ready": True}))
        ready.close()
    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, lambda _signum, _frame: server.stop())
    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
