#!/usr/bin/env python3

# Standard libraries.
import collections.abc
import asyncio
import sys
import tkinter
import typing as t

# https://tkdocs.com/tutorial/eventloop.html
# tkinter.Tk.event_generate

_P = t.ParamSpec("_P")
_T = t.TypeVar("_T")


class EventLoop(asyncio.AbstractEventLoop):
    # Running and stopping the event loop.
    def __init__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        super().__init__(*args, **kwargs)

    def run_forever(self) -> None:
        """Run the event loop until stop() is called."""
        raise NotImplementedError

    def run_until_complete(
        self,
        future: collections.abc.Generator[t.Any, None, _T]
        | collections.abc.Awaitable[_T],
    ) -> _T:
        """Run the event loop until a Future is done.

        Return the Future's result, or raise its exception.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the event loop as soon as reasonable.

        Exactly how soon that is may depend on the implementation, but
        no more I/O callbacks should be scheduled.
        """
        raise NotImplementedError

    def is_running(self) -> bool:
        """Return whether the event loop is currently running."""
        raise NotImplementedError

    def is_closed(self) -> bool:
        """Returns True if the event loop was closed."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the loop.

        The loop should not be running.

        This is idempotent and irreversible.

        No other methods should be called after this one.
        """
        raise NotImplementedError

    async def shutdown_asyncgens(self) -> None:
        """Shutdown all active asynchronous generators."""
        raise NotImplementedError

    async def shutdown_default_executor(self) -> None:
        """Schedule the shutdown of the default executor."""
        raise NotImplementedError

    # Methods scheduling callbacks.  All these return Handles.

    def _timer_handle_cancelled(self, handle) -> None:
        """Notification that a TimerHandle has been cancelled."""
        raise NotImplementedError

    def call_soon(self, callback, *args, context=None) -> None:
        return self.call_later(0, callback, *args, context=context)

    def call_later(self, delay, callback, *args, context=None) -> None:
        raise NotImplementedError

    def call_at(self, when, callback, *args, context=None) -> None:
        raise NotImplementedError

    def time(self) -> None:
        raise NotImplementedError

    def create_future(self) -> None:
        raise NotImplementedError

    # Method scheduling a coroutine object: create a task.

    def create_task(self, coro, *, name=None, context=None) -> None:
        raise NotImplementedError

    # Methods for interacting with threads.

    def call_soon_threadsafe(self, callback, *args, context=None) -> None:
        raise NotImplementedError

    def run_in_executor(self, executor, func, *args) -> None:
        raise NotImplementedError

    def set_default_executor(self, executor) -> None:
        raise NotImplementedError

    # Network I/O methods returning Futures.

    async def getaddrinfo(
        self, host, port, *, family=0, type=0, proto=0, flags=0
    ) -> None:
        raise NotImplementedError

    async def getnameinfo(self, sockaddr, flags=0) -> None:
        raise NotImplementedError

    async def create_connection(
        self,
        protocol_factory,
        host=None,
        port=None,
        *,
        ssl=None,
        family=0,
        proto=0,
        flags=0,
        sock=None,
        local_addr=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
        happy_eyeballs_delay=None,
        interleave=None
    ) -> None:
        raise NotImplementedError

    async def create_server(
        self,
        protocol_factory,
        host=None,
        port=None,
        *,
        family=socket.AF_UNSPEC,
        flags=socket.AI_PASSIVE,
        sock=None,
        backlog=100,
        ssl=None,
        reuse_address=None,
        reuse_port=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
        start_serving=True
    ) -> None:
        """A coroutine which creates a TCP server bound to host and port.

        The return value is a Server object which can be used to stop
        the service.

        If host is an empty string or None all interfaces are assumed
        and a list of multiple sockets will be returned (most likely
        one for IPv4 and another one for IPv6). The host parameter can also be
        a sequence (e.g. list) of hosts to bind to.

        family can be set to either AF_INET or AF_INET6 to force the
        socket to use IPv4 or IPv6. If not set it will be determined
        from host (defaults to AF_UNSPEC).

        flags is a bitmask for getaddrinfo().

        sock can optionally be specified in order to use a preexisting
        socket object.

        backlog is the maximum number of queued connections passed to
        listen() (defaults to 100).

        ssl can be set to an SSLContext to enable SSL over the
        accepted connections.

        reuse_address tells the kernel to reuse a local socket in
        TIME_WAIT state, without waiting for its natural timeout to
        expire. If not specified will automatically be set to True on
        UNIX.

        reuse_port tells the kernel to allow this endpoint to be bound to
        the same port as other existing endpoints are bound to, so long as
        they all set this flag when being created. This option is not
        supported on Windows.

        ssl_handshake_timeout is the time in seconds that an SSL server
        will wait for completion of the SSL handshake before aborting the
        connection. Default is 60s.

        ssl_shutdown_timeout is the time in seconds that an SSL server
        will wait for completion of the SSL shutdown procedure
        before aborting the connection. Default is 30s.

        start_serving set to True (default) causes the created server
        to start accepting connections immediately.  When set to False,
        the user should await Server.start_serving() or Server.serve_forever()
        to make the server to start accepting connections.
        """
        raise NotImplementedError

    async def sendfile(
        self, transport, file, offset=0, count=None, *, fallback=True
    ) -> None:
        """Send a file through a transport.

        Return an amount of sent bytes.
        """
        raise NotImplementedError

    async def start_tls(
        self,
        transport,
        protocol,
        sslcontext,
        *,
        server_side=False,
        server_hostname=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None
    ) -> None:
        """Upgrade a transport to TLS.

        Return a new transport that *protocol* should start using
        immediately.
        """
        raise NotImplementedError

    async def create_unix_connection(
        self,
        protocol_factory,
        path=None,
        *,
        ssl=None,
        sock=None,
        server_hostname=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None
    ) -> None:
        raise NotImplementedError

    async def create_unix_server(
        self,
        protocol_factory,
        path=None,
        *,
        sock=None,
        backlog=100,
        ssl=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None,
        start_serving=True
    ) -> None:
        """A coroutine which creates a UNIX Domain Socket server.

        The return value is a Server object, which can be used to stop
        the service.

        path is a str, representing a file system path to bind the
        server socket to.

        sock can optionally be specified in order to use a preexisting
        socket object.

        backlog is the maximum number of queued connections passed to
        listen() (defaults to 100).

        ssl can be set to an SSLContext to enable SSL over the
        accepted connections.

        ssl_handshake_timeout is the time in seconds that an SSL server
        will wait for the SSL handshake to complete (defaults to 60s).

        ssl_shutdown_timeout is the time in seconds that an SSL server
        will wait for the SSL shutdown to finish (defaults to 30s).

        start_serving set to True (default) causes the created server
        to start accepting connections immediately.  When set to False,
        the user should await Server.start_serving() or Server.serve_forever()
        to make the server to start accepting connections.
        """
        raise NotImplementedError

    async def connect_accepted_socket(
        self,
        protocol_factory,
        sock,
        *,
        ssl=None,
        ssl_handshake_timeout=None,
        ssl_shutdown_timeout=None
    ) -> None:
        """Handle an accepted connection.

        This is used by servers that accept connections outside of
        asyncio, but use asyncio to handle connections.

        This method is a coroutine.  When completed, the coroutine
        returns a (transport, protocol) pair.
        """
        raise NotImplementedError

    async def create_datagram_endpoint(
        self,
        protocol_factory,
        local_addr=None,
        remote_addr=None,
        *,
        family=0,
        proto=0,
        flags=0,
        reuse_address=None,
        reuse_port=None,
        allow_broadcast=None,
        sock=None
    ) -> None:
        """A coroutine which creates a datagram endpoint.

        This method will try to establish the endpoint in the background.
        When successful, the coroutine returns a (transport, protocol) pair.

        protocol_factory must be a callable returning a protocol instance.

        socket family AF_INET, socket.AF_INET6 or socket.AF_UNIX depending on
        host (or family if specified), socket type SOCK_DGRAM.

        reuse_address tells the kernel to reuse a local socket in
        TIME_WAIT state, without waiting for its natural timeout to
        expire. If not specified it will automatically be set to True on
        UNIX.

        reuse_port tells the kernel to allow this endpoint to be bound to
        the same port as other existing endpoints are bound to, so long as
        they all set this flag when being created. This option is not
        supported on Windows and some UNIX's. If the
        :py:data:`~socket.SO_REUSEPORT` constant is not defined then this
        capability is unsupported.

        allow_broadcast tells the kernel to allow this endpoint to send
        messages to the broadcast address.

        sock can optionally be specified in order to use a preexisting
        socket object.
        """
        raise NotImplementedError

    # Pipes and subprocesses.

    async def connect_read_pipe(self, protocol_factory, pipe) -> None:
        """Register read pipe in event loop. Set the pipe to non-blocking mode.

        protocol_factory should instantiate object with Protocol interface.
        pipe is a file-like object.
        Return pair (transport, protocol), where transport supports the
        ReadTransport interface."""
        # The reason to accept file-like object instead of just file descriptor
        # is: we need to own pipe and close it at transport finishing
        # Can got complicated errors if pass f.fileno(),
        # close fd in pipe transport then close f and vice versa.
        raise NotImplementedError

    async def connect_write_pipe(self, protocol_factory, pipe) -> None:
        """Register write pipe in event loop.

        protocol_factory should instantiate object with BaseProtocol interface.
        Pipe is file-like object already switched to nonblocking.
        Return pair (transport, protocol), where transport support
        WriteTransport interface."""
        # The reason to accept file-like object instead of just file descriptor
        # is: we need to own pipe and close it at transport finishing
        # Can got complicated errors if pass f.fileno(),
        # close fd in pipe transport then close f and vice versa.
        raise NotImplementedError

    async def subprocess_shell(
        self,
        protocol_factory,
        cmd,
        *,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs
    ) -> None:
        raise NotImplementedError

    async def subprocess_exec(
        self,
        protocol_factory,
        *args,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **kwargs
    ) -> None:
        raise NotImplementedError

    # Ready-based callback registration methods.
    # The add_*() methods return None.
    # The remove_*() methods return True if something was removed,
    # False if there was nothing to delete.

    def add_reader(self, fd, callback, *args) -> None:
        raise NotImplementedError

    def remove_reader(self, fd) -> None:
        raise NotImplementedError

    def add_writer(self, fd, callback, *args) -> None:
        raise NotImplementedError

    def remove_writer(self, fd) -> None:
        raise NotImplementedError

    # Completion based I/O methods returning Futures.

    async def sock_recv(self, sock, nbytes) -> None:
        raise NotImplementedError

    async def sock_recv_into(self, sock, buf) -> None:
        raise NotImplementedError

    async def sock_recvfrom(self, sock, bufsize) -> None:
        raise NotImplementedError

    async def sock_recvfrom_into(self, sock, buf, nbytes=0) -> None:
        raise NotImplementedError

    async def sock_sendall(self, sock, data) -> None:
        raise NotImplementedError

    async def sock_sendto(self, sock, data, address) -> None:
        raise NotImplementedError

    async def sock_connect(self, sock, address) -> None:
        raise NotImplementedError

    async def sock_accept(self, sock) -> None:
        raise NotImplementedError

    async def sock_sendfile(
        self, sock, file, offset=0, count=None, *, fallback=None
    ) -> None:
        raise NotImplementedError

    # Signal handling.

    def add_signal_handler(self, sig, callback, *args) -> None:
        raise NotImplementedError

    def remove_signal_handler(self, sig) -> None:
        raise NotImplementedError

    # Task factory.

    def set_task_factory(self, factory) -> None:
        raise NotImplementedError

    def get_task_factory(self) -> None:
        raise NotImplementedError

    # Error handlers.

    def get_exception_handler(self) -> None:
        raise NotImplementedError

    def set_exception_handler(self, handler) -> None:
        raise NotImplementedError

    def default_exception_handler(self, context) -> None:
        raise NotImplementedError

    def call_exception_handler(self, context) -> None:
        raise NotImplementedError

    # Debug flag management.

    def get_debug(self) -> bool:
        raise NotImplementedError

    def set_debug(self, enabled: bool) -> None:
        raise NotImplementedError


def main() -> int:
    return 0


if __name__ == "__main__":
    sys.exit(main())
