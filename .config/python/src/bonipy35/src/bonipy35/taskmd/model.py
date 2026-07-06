#!/usr/bin/env python3

# Standard libraries.
import datetime
import enum
import pathlib
import typing

from typing import List, Union

# Internal modules.
from . import errors


class ClockEntry:
    def __init__(
        self,
        *args: typing.Any,
        description: str,
        end: Union[None, datetime.datetime] = None,
        start: datetime.datetime,
        work_notes: str,
        source_line: int = 0,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.description = description
        self.end = end
        self.source_line = source_line
        self.start = start
        self.work_notes = work_notes

    def duration(self) -> datetime.timedelta:
        end = self.end
        if end is None:
            return datetime.timedelta(0)
        return end - self.start

    def is_open(self) -> bool:
        return self.end is None


class Update:
    def __init__(
        self,
        *args: typing.Any,
        body: str,
        source_line: int = 0,
        timestamp: Union[None, datetime.datetime] = None,
        title: str,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.body = body
        self.source_line = source_line
        self.timestamp = timestamp
        self.title = title


class Status(enum.Enum):
    TODO = 0
    DONE = 1
    DROP = 2
    WAIT = 3


class Task:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: typing.Any,
        clocks: Union[None, List[ClockEntry]] = None,
        description: Union[None, str] = None,
        events: Union[None, List["Event"]] = None,
        level: int,
        source_line: Union[None, int] = None,
        status: Status,
        tags: Union[None, List[str]] = None,
        tasks: Union[None, List["Task"]] = None,
        title: str,
        updates: Union[None, List[Update]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)

        if clocks is None:
            clocks = []
        if description is None:
            description = ""
        if events is None:
            events = []
        if source_line is None:
            source_line = 0
        if tags is None:
            tags = []
        if tasks is None:
            tasks = []
        if updates is None:
            updates = []

        self.clocks = clocks
        self.description = description
        self.events = events
        self.level = level
        self.source_line = source_line
        self.status = status
        self.tags = tags
        self.tasks = tasks
        self.title = title
        self.updates = updates

    def effective_tags(
        self, parent_tags: Union[None, List[str]] = None
    ) -> List[str]:

        if parent_tags is None:
            parent_tags = []

        seen = set()
        combined = []
        for tag in list(parent_tags) + list(self.tags):
            if tag not in seen:
                seen.add(tag)
                combined.append(tag)
        return combined

    def total_duration(
        self, *, recursive: Union[None, bool] = None
    ) -> datetime.timedelta:
        if recursive is None:
            recursive = True

        total = datetime.timedelta(0)
        for clock in self.clocks:
            total += clock.duration()

        for event in self.events:
            total += event.actual_duration()

        if recursive:
            for subtask in self.tasks:
                total += subtask.total_duration(recursive=True)

        return total

    def walk(self) -> typing.Iterator["Task"]:
        yield self
        for subtask in self.tasks:
            yield from subtask.walk()


class TaskFile:
    def __init__(
        self,
        *args: typing.Any,
        events: Union[None, List["Event"]] = None,
        path: Union[None, pathlib.Path],
        tasks: Union[None, List[Task]] = None,
        warnings: Union[None, List[errors.ParseWarning]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        if events is None:
            events = []
        if tasks is None:
            tasks = []
        if warnings is None:
            warnings = []
        self.events = events
        self.path = path
        self.tasks = tasks
        self.warnings = warnings

    def walk(self) -> typing.Iterator[Task]:
        for task in self.tasks:
            yield from task.walk()


class RecurRule:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: typing.Any,
        interval: int,
        prefix: 'typing.Literal["+", "++", ".+"]',
        raw: str,
        unit: 'typing.Literal["d", "w", "m", "y"]',
        until: Union[None, object] = None,
        weekdays: Union[None, List[str]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.interval = interval
        self.prefix = prefix
        self.raw = raw
        self.unit = unit
        self.until = until
        self.weekdays = weekdays


class Event:
    def __init__(  # pylint: disable=too-many-arguments
        self,
        *args: typing.Any,
        clocks: Union[None, List[ClockEntry]] = None,
        description: Union[None, str] = None,
        level: int,
        recur: Union[None, RecurRule] = None,
        scheduled_end: datetime.datetime,
        scheduled_start: datetime.datetime,
        source_line: Union[None, int] = None,
        sub_events: Union[None, List["Event"]] = None,
        tags: Union[None, List[str]] = None,
        title: str,
        updates: Union[None, List[Update]] = None,
        **kwargs: typing.Any
    ) -> None:
        super().__init__(*args, **kwargs)

        if clocks is None:
            clocks = []
        if description is None:
            description = ""
        if source_line is None:
            source_line = 0
        if sub_events is None:
            sub_events = []
        if tags is None:
            tags = []
        if updates is None:
            updates = []

        self.clocks = clocks
        self.description = description
        self.level = level
        self.recur = recur
        self.scheduled_end = scheduled_end
        self.scheduled_start = scheduled_start
        self.source_line = source_line
        self.sub_events = sub_events
        self.tags = tags
        self.title = title
        self.updates = updates

    def actual_duration(self) -> datetime.timedelta:
        total = datetime.timedelta(0)
        for clock in self.clocks:
            total += clock.duration()
        return total

    def divergence(self) -> datetime.timedelta:
        return self.actual_duration() - self.scheduled_duration()

    def occurrences(
        self, from_date: datetime.datetime, to_date: datetime.datetime
    ) -> List[datetime.datetime]:
        raise NotImplementedError

    def scheduled_duration(self) -> datetime.timedelta:
        return self.scheduled_end - self.scheduled_start
