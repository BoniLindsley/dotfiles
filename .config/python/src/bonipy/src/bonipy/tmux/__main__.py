#!/usr/bin/env python3

# Standard libraries.
import asyncio
# TODO[pylint/1469]: Lint fails when using `asyncio.subprocess.Process` directly.
# Reference: https://github.com/pylint-dev/pylint/issues/1469
from asyncio.subprocess import Process
from collections import abc
import contextlib
import datetime
import logging
import os
import sys
import typing as t

# External dependencies.
import watchdog

# Internal modules.
from . import commands as c


_P = t.ParamSpec("_P")
_T = t.TypeVar("_T")
_logger = logging.getLogger(__name__)


class Block(t.TypedDict):
    time: datetime.datetime
    command: int
    flags: str
    output: list[str]


class MessageParseError(RuntimeError):
    pass


def parse_block_begin_line(line: str) -> Block | MessageParseError:
    if not line.startswith("%begin "):
        return MessageParseError(f"Block not starting with prefix: {line}")
    line_split = line.split(" ", maxsplit=3)
    if len(line_split) < 4:
        return MessageParseError(f"Not enough arguments in block: {line}")
    return {
        "time": datetime.datetime.fromtimestamp(int(line_split[1])),
        "command": int(line_split[2]),
        "flags": line_split[3],
        "output": [],
    }


def get_block_end_line(block: Block) -> str:
    return " ".join(
        ("%end", str(block["time"].timestamp), str(block["command"]), block["flags"])
    )


async def parse_block_output(
    lines: abc.AsyncIterator[str], end_line: str
) -> list[str] | MessageParseError:
    output: list[str] = []
    async for line in lines:
        if line != end_line:
            return output
        output.append(line)
    return MessageParseError("Unterminated output block from tmux.")


async def read_block(
    first_line: str, lines: abc.AsyncIterator[str]
) -> Block | MessageParseError:
    block = parse_block_begin_line(first_line)
    if isinstance(block, MessageParseError):
        return block
    output = await parse_block_output(lines, get_block_end_line(block))
    if isinstance(output, MessageParseError):
        return output
    block["output"] = output
    return block


Notification = str
Message = Block | Notification


async def read_message(lines: abc.AsyncIterator[str]) -> Message | MessageParseError:
    try:
        first_line = await anext(lines)
    except StopAsyncIteration:
        return MessageParseError("No messages available from tmux.")
    if first_line.startswith("%begin "):
        return await read_block(first_line, lines)
    # Unsupported or unknown output format.
    return first_line


class UnexpectedNestedSession(RuntimeError):
    pass


async def read_lines(process: Process) -> abc.AsyncIterator[str]:
    # Must be able to read from the process.
    stdout = process.stdout
    assert stdout is not None

    while True:
        next_line = await stdout.readline()
        if not next_line.endswith(b"\n"):
            break
        line = next_line[:-1].decode()
        del next_line
        _logger.debug("tmux > %s", line)
        yield line


async def parse_first_block(lines: abc.AsyncIterator[str]) -> Block | MessageParseError:
    # First message should be an empty block.
    block = await read_message(lines)
    if isinstance(block, MessageParseError):
        return block
    if not isinstance(block, dict):
        return MessageParseError("First message is not a block.")
    if block["output"]:
        return MessageParseError("First message block is not empty.")
    return block


@contextlib.asynccontextmanager
async def create_control_mode_process(
    *, ignore_environ_tmux: bool = False
) -> abc.AsyncIterator[Process | MessageParseError | UnexpectedNestedSession]:
    if not ignore_environ_tmux and "TMUX" in os.environ:
        yield UnexpectedNestedSession(
            "Aborting. Detected Nested tmux session."
            " It can trigger infinite event handling loops."
        )
        return

    process = await asyncio.create_subprocess_exec(
        # Double "-CC" flag causes TTY stdout to be disabled, not just command echo.
        "tmux",
        "-C",
        "new-session",
        "-A",
        "-s",
        "ctrl",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
    )
    try:
        block = await read_message(read_lines(process))
        if isinstance(block, MessageParseError):
            yield block
            return
        yield process
    finally:
        try:
            # Request a clean exit from tmux. Not strictly necessary.
            # An empty line is treated by tmux as request for a clean exit.
            # End the previous line even if incomplete.
            # Followed by another line that is definitely empty.
            # It is okay for either newline character to be treated as an exit request.
            stdin = process.stdin
            if stdin is not None:
                stdin.write(b"\n\n")
            process.kill()
        except ProcessLookupError:
            # Process may have ended already.
            pass
        await process.wait()


class Request:
    def __init__(self, command: str, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.command = command
        self.reply: asyncio.Future[Block] = asyncio.get_running_loop().create_future()


class Service:
    def __init__(self, process: Process, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Communication channel with tmux .
        self.process = process
        # Requests must be serialised and syncrhonised with replies.
        self.request_queue: asyncio.Queue[Request] = asyncio.Queue()

    async def send_command(self, command: str) -> Block:
        request = Request(command=command)
        self.request_queue.put_nowait(request)
        return await request.reply

    async def run(self) -> None:
        # Must be able to send to the process.
        stdin = self.process.stdin
        assert stdin is not None

        current_request: None | Request = None
        line_reader = read_lines(self.process)

        message_reader: None | asyncio.Task[Message | MessageParseError] = None
        queue_checker: None | asyncio.Task[Request] = None
        try:
            done: set[asyncio.Task[Message | MessageParseError | Request]] = set()
            pending: set[asyncio.Task[Message | MessageParseError | Request]] = set()
            while True:
                # Read the next message from tmux if any. Reset the reader afterwards.
                if message_reader in done:
                    message = await message_reader
                    message_reader = None
                    # If there was a request,
                    # check whether the message is a response to the request.
                    if current_request and isinstance(message, dict):
                        current_request.reply.set_result(message)
                        current_request = None
                # Falls through if message reader was done.
                # Also enters in first loop.
                if not message_reader:
                    message_reader = asyncio.create_task(read_message(line_reader))
                # Always try to read the next message.
                pending.add(message_reader)
                # Check for another request
                # only if no existing request is waiting for a response.
                if not current_request:
                    if queue_checker in done:
                        current_request = await queue_checker
                        queue_checker = None
                        command = current_request.command
                        _logger.debug("tmux < %s", command)
                        stdin.write(command.encode("utf-8"))
                        stdin.write(b"\n")
                    # Falls through if there was a request.
                    # Also enters in first loop.
                    if not queue_checker:
                        queue_checker = asyncio.create_task(self.request_queue.get())
                        pending.add(queue_checker)

                # Nothing to wait for, somehow.
                if not pending:
                    _logger.error("No tmux message tasks to wait for.")
                    break

                done, pending = await asyncio.wait(
                    pending, return_when=asyncio.FIRST_COMPLETED
                )

                # Not sure what is going on if `asyncio.wait` returns without any `done`.
                if not done:
                    _logger.error("No tmux message tasks found.")
                    break

        finally:
            _logger.debug("Stopping tmux message procescsing.")

    @classmethod
    @contextlib.asynccontextmanager
    async def start(cls) -> abc.AsyncIterator["Service"]:
        async with contextlib.AsyncExitStack() as stack:
            process = await stack.enter_async_context(create_control_mode_process())
            if not isinstance(process, Process):
                raise process

            service = cls(process=process)
            service.process = process

            # Must be able to send and receive messages to and from the process.
            stdin = process.stdin
            assert stdin is not None
            assert process.stdout is not None

            task = asyncio.create_task(service.run())
            try:
                yield service
            finally:
                # Try to clean up in all cases.
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    pass


class TrayIconService:
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.tray_entries: dict[str, str] = {}
        self.taskbar = ""
        self.change_event = asyncio.Event()

    def add_tray_entry(self, name: str, value: str) -> None:
        tray_entries = self.tray_entries
        tray_entries[name] = value
        self.tray_entries = dict(sorted(tray_entries.items()))
        self.update_taskbar()

    def remove_tray_entry(self, name: str) -> None:
        self.tray_entries.pop(name, None)
        self.update_taskbar()

    def update_taskbar(self) -> None:
        self.taskbar = " ".join(self.tray_entries.values())
        change_event = self.change_event
        change_event.set()
        change_event.clear()

    async def get_taskbar(self) -> abc.AsyncIterator[str]:
        while True:
            yield self.taskbar
            await self.change_event.wait()


async def amain() -> int:
    try:
        async with Service.start() as service:
            tray_icon_service = TrayIconService()
            tray_icon_service.add_tray_entry(
                "30-default", '"#{pane_title}" %Y-%m-%d w%w %H:%M'
            )
            async for taskbar in tray_icon_service.get_taskbar():
                command = c.set_option("status-right", taskbar, global_=True)
                await service.send_command(command=command)
        # Use tmux control mode return code as own exit code.
        return_code = service.process.returncode
        if return_code is not None:
            return return_code
    except (MessageParseError, UnexpectedNestedSession) as error:
        _logger.error(error)
    return 1


def main(argv: None | list[str] = None) -> int:
    del argv
    logging.basicConfig(level=logging.DEBUG)
    try:
        return asyncio.run(amain())
    except KeyboardInterrupt:
        return 2


if __name__ == "__main__":
    sys.exit(main())
