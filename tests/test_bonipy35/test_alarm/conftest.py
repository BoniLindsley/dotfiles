#!/usr/bin/env python3

# Standard libraries.
import datetime
import pathlib
import threading

from typing import Iterator, List

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.client import Client
from bonipy35.alarm.server import Server


@pytest.fixture(name="now")
def fixture_now() -> datetime.datetime:
    return datetime.datetime(2026, 10, 11, 12, tzinfo=datetime.timezone.utc)


@pytest.fixture(name="service")
def fixture_service(tmp_path: pathlib.Path) -> Iterator[Server]:
    service = Server(directory=tmp_path)
    failures = []  # type: List[BaseException]

    def run() -> None:
        try:
            service.run()
        # Propagate worker failures into the test instead of losing them in a thread.
        # pylint: disable-next=broad-exception-caught
        except BaseException as error:
            failures.append(error)

    worker = threading.Thread(target=run)
    worker.start()
    try:
        yield service
    finally:
        if worker.is_alive():
            service.stop()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert not failures


@pytest.fixture(name="connection")
def fixture_connection(service: Server) -> Iterator[Client]:
    with Client(directory=service.directory) as connection:
        yield connection
