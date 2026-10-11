#!/usr/bin/env python3

# Standard libraries.
import contextlib
import datetime
import pathlib
import threading

from typing import Iterator, List, Tuple, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.client import Client
from bonipy35.alarm.server import Server


@pytest.fixture(name="now")
def fixture_now() -> datetime.datetime:
    return datetime.datetime(2026, 10, 11, 12, tzinfo=datetime.timezone.utc)


@contextlib.contextmanager
def running_server(
    directory: pathlib.Path, *, idle_timeout: Union[None, float] = None
) -> Iterator[Tuple[Server, threading.Thread]]:
    service = Server(directory=directory, idle_timeout=idle_timeout)
    failures = []  # type: List[BaseException]

    def run() -> None:
        try:
            service.run()
        # Worker failures must fail the test, including persistence failures.
        # pylint: disable-next=broad-exception-caught
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        yield service, worker
    finally:
        if worker.is_alive():
            service.stop()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert not failures


@pytest.fixture(name="service")
def fixture_service(tmp_path: pathlib.Path) -> Iterator[Server]:
    with running_server(tmp_path) as (service, _worker):
        yield service


@pytest.fixture(name="connection")
def fixture_connection(service: Server) -> Iterator[Client]:
    with Client(directory=service.directory) as connection:
        yield connection
