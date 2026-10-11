#!/usr/bin/env python3

# Standard libraries.
import argparse
import logging

from typing import Dict, List, Union

# External dependencies.
import pytest

# Internal modules.
from bonipy35 import logging_ext
from bonipy35.logging_ext import (
    ALL,
    TRACE,
    add_verbose_flag,
    run,
    set_logger_verbosity,
    set_up_logging,
)


class TestSetLoggerVerbosity:
    def test_defaults_to_warning_for_gap_in_map(self) -> None:
        logger = logging.Logger("verbosity", level=logging.CRITICAL)
        set_logger_verbosity(
            logger=logger,
            verbosity=1,
            verbosity_map={0: logging.ERROR, 2: logging.DEBUG},
        )
        assert logger.level == logging.WARNING

    @pytest.mark.parametrize(
        "verbosity, expected",
        [
            (-99, logging.CRITICAL),
            (-2, logging.CRITICAL),
            (-1, logging.ERROR),
            (0, logging.WARNING),
            (1, logging.INFO),
            (2, logging.DEBUG),
            (3, TRACE),
            (4, ALL),
            (99, ALL),
        ],
    )
    def test_maps_and_clamps_verbosity(
        self, verbosity: int, expected: int
    ) -> None:
        logger = logging.Logger("verbosity", level=logging.CRITICAL)
        set_logger_verbosity(logger=logger, verbosity=verbosity)
        assert logger.level == expected

    def test_preserves_more_verbose_level(self) -> None:
        logger = logging.Logger("verbosity", level=logging.DEBUG)
        set_logger_verbosity(logger=logger, verbosity=0)
        assert logger.level == logging.DEBUG

    def test_respects_inherited_level(self) -> None:
        parent = logging.Logger("parent", level=logging.DEBUG)
        logger = logging.Logger("parent.child")
        logger.parent = parent
        set_logger_verbosity(logger=logger, verbosity=0)
        assert logger.level == logging.NOTSET
        assert logger.getEffectiveLevel() == logging.DEBUG

    def test_uses_custom_map(self) -> None:
        logger = logging.Logger("verbosity", level=logging.CRITICAL)
        set_logger_verbosity(
            logger=logger,
            verbosity=10,
            verbosity_map={10: logging.INFO, 20: logging.DEBUG},
        )
        assert logger.level == logging.INFO

    @pytest.mark.parametrize("verbosity_map", [None, {}])
    def test_uses_default_map(
        self, verbosity_map: Union[None, Dict[int, int]]
    ) -> None:
        logger = logging.Logger("verbosity", level=logging.CRITICAL)
        set_logger_verbosity(
            logger=logger, verbosity=2, verbosity_map=verbosity_map
        )
        assert logger.level == logging.DEBUG


class TestSetUpLogging:
    def test_adds_formatted_stream_handler(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        logger = logging.Logger("formatted", level=logging.WARNING)
        set_up_logging(logger=logger)
        assert len(logger.handlers) == 1
        assert isinstance(logger.handlers[0], logging.StreamHandler)
        logger.warning("example")
        captured = capsys.readouterr()
        assert "[python/formatted] [W] example" in captured.err
        assert captured.out == ""

    def test_adds_handler_when_propagation_disabled(self) -> None:
        parent = logging.Logger("parent")
        parent.addHandler(logging.NullHandler())
        logger = logging.Logger("parent.child")
        logger.parent = parent
        logger.propagate = False
        set_up_logging(logger=logger)
        assert len(logger.handlers) == 1

    def test_is_idempotent(self) -> None:
        logger = logging.Logger("logging")
        set_up_logging(logger=logger)
        handlers = list(logger.handlers)
        set_up_logging(logger=logger)
        assert logger.handlers == handlers

    def test_preserves_existing_handler(self) -> None:
        logger = logging.Logger("logging")
        handler = logging.NullHandler()
        logger.addHandler(handler)
        set_up_logging(logger=logger)
        assert logger.handlers == [handler]

    def test_respects_parent_handler(self) -> None:
        parent = logging.Logger("parent")
        parent.addHandler(logging.NullHandler())
        logger = logging.Logger("parent.child")
        logger.parent = parent
        set_up_logging(logger=logger)
        assert not logger.handlers


class TestAddVerboseFlag:
    @pytest.mark.parametrize(
        "arguments, expected",
        [
            ([], 0),
            (["-v"], 1),
            (["--verbose"], 1),
            (["-vvv"], 3),
            (["--verbose", "-v"], 2),
        ],
    )
    def test_counts_flags(self, arguments: List[str], expected: int) -> None:
        parser = argparse.ArgumentParser()
        add_verbose_flag(parser)
        assert parser.parse_args(arguments).verbosity == expected


class TestRun:
    def test_reports_message_at_each_level(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        logger = logging.Logger("example", level=ALL)
        logger.addHandler(caplog.handler)
        caplog.handler.setLevel(ALL)
        monkeypatch.setattr(logging_ext, "_logger", logger)
        assert run("hello") == 0
        assert capsys.readouterr().out == "Command is hello\n"
        assert [record.levelno for record in caplog.records] == [
            ALL,
            TRACE,
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]
        assert logging.getLevelName(ALL) == "ALL"
        assert logging.getLevelName(TRACE) == "TRACE"
