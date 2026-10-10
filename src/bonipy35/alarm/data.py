#!/usr/bin/env python3
"""Persistent items and notification lifecycles, independent of transport."""

# Standard libraries.
import datetime
import enum
import json
import typing

from typing import Dict, List, Union


class State(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    TRIGGERED = "triggered"


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class Datetime:
    format = "%Y%m%dT%H%M%S.%fZ"

    @classmethod
    def model_dump(cls, obj: datetime.datetime) -> str:
        if obj.tzinfo is None:
            raise ValueError("Timestamp must include a timezone")
        return obj.astimezone(datetime.timezone.utc).strftime(cls.format)

    @classmethod
    def model_validate_datetime(cls, obj: str) -> datetime.datetime:
        return datetime.datetime.strptime(obj, cls.format).replace(
            tzinfo=datetime.timezone.utc
        )


class Alarm:
    def __init__(
        self,
        *,
        end_time: datetime.datetime,
        id_: int,
        name: str,
        state: State = State.ACTIVE
    ) -> None:
        Datetime.model_dump(end_time)
        self.end_time = end_time
        self.id_ = id_
        self.name = name
        self.state = state
        self.paused_at = None  # type: Union[None, datetime.datetime]
        self.occurred_at = None  # type: Union[None, datetime.datetime]
        self.last_dismissed_at = None  # type: Union[None, datetime.datetime]
        self.missed = False

    def remaining(self, now: datetime.datetime) -> datetime.timedelta:
        reference = self.paused_at if self.paused_at is not None else now
        return max(datetime.timedelta(), self.end_time - reference)

    @property
    def notification_active(self) -> bool:
        return (
            self.occurred_at is not None
            and self.state not in (State.PAUSED, State.STOPPED)
            and (
                self.last_dismissed_at is None
                or self.occurred_at > self.last_dismissed_at
            )
        )

    def update(self, now: datetime.datetime, *, missed: bool = False) -> bool:
        if (
            self.state != State.ACTIVE
            or self.occurred_at is not None
            or self.end_time > now
        ):
            return False
        self.occurred_at = self.end_time
        self.missed = missed
        if not missed:
            self.state = State.TRIGGERED
        return True

    def pause(self, now: datetime.datetime) -> None:
        if self.state != State.ACTIVE:
            raise ValueError("Only an active item can be paused")
        self.paused_at = now
        self.state = State.PAUSED

    def resume(self, now: datetime.datetime) -> None:
        if self.state != State.PAUSED or self.paused_at is None:
            raise ValueError("Item is not paused")
        if isinstance(self, Timer):
            self.end_time += max(datetime.timedelta(), now - self.paused_at)
        self.paused_at = None
        self.state = State.ACTIVE
        self.update(now, missed=True)

    def stop(self) -> None:
        self.state = State.STOPPED
        self.paused_at = None
        self.occurred_at = None

    def reschedule(self, end_time: datetime.datetime) -> None:
        Datetime.model_dump(end_time)
        self.end_time = end_time
        self.state = State.ACTIVE
        self.paused_at = None
        self.occurred_at = None
        # Dismissal belongs to an occurrence, not permanently to the item.
        self.last_dismissed_at = None
        self.missed = False

    def dismiss(self, now: datetime.datetime) -> None:
        if self.occurred_at is None:
            raise ValueError("Item has no notification")
        # A backwards clock correction must not make dismissal ineffective.
        self.last_dismissed_at = max(now, self.occurred_at)

    def model_dump(self) -> Dict[str, typing.Any]:
        obj = {
            "id_": self.id_,
            "name": self.name,
            "state": self.state.value,
            "end_time": Datetime.model_dump(self.end_time),
            "missed": self.missed,
        }
        for key in ("paused_at", "occurred_at", "last_dismissed_at"):
            value = getattr(self, key)
            obj[key] = None if value is None else Datetime.model_dump(value)
        return obj

    @classmethod
    def model_validate(cls, obj: Dict[str, typing.Any]) -> "typing.Self":
        end_time = Datetime.model_validate_datetime(obj["end_time"])
        id_ = int(obj["id_"])
        name = str(obj["name"])
        state = State(obj["state"])
        if "duration" in obj:
            item = Timer(
                duration=datetime.timedelta(seconds=obj["duration"]),
                end_time=end_time,
                id_=id_,
                name=name,
                state=state,
            )  # type: Alarm
        else:
            item = cls(end_time=end_time, id_=id_, name=name, state=state)
        for key in ("paused_at", "occurred_at", "last_dismissed_at"):
            value = obj.get(key)
            setattr(
                item,
                key,
                (
                    None
                    if value is None
                    else Datetime.model_validate_datetime(value)
                ),
            )
        item.missed = bool(obj.get("missed", False))
        if (item.state == State.PAUSED) != (item.paused_at is not None):
            raise ValueError("Paused state requires paused_at")
        if item.id_ < 0:
            raise ValueError("ID must be nonnegative")
        return typing.cast("typing.Self", item)


class Timer(Alarm):
    def __init__(
        self, *, duration: datetime.timedelta, **kwargs: typing.Any
    ) -> None:
        if duration <= datetime.timedelta():
            raise ValueError("Duration must be positive")
        super().__init__(**kwargs)
        self.duration = duration

    def model_dump(self) -> Dict[str, typing.Any]:
        obj = super().model_dump()
        obj["duration"] = self.duration.total_seconds()
        return obj

    def start(self, now: datetime.datetime) -> None:
        self.reschedule(now + self.duration)


class UserData:
    def __init__(self) -> None:
        self.alarms = []  # type: List[Alarm]
        self.next_id = 0

    def get(self, id_: int) -> Alarm:
        for item in self.alarms:
            if item.id_ == id_:
                return item
        raise ValueError("Unknown item ID: {}".format(id_))

    def add_alarm(
        self, *, end_time: datetime.datetime, name: str = ""
    ) -> Alarm:
        item = Alarm(
            end_time=end_time,
            id_=self.next_id,
            name=name or "Alarm {}".format(self.next_id),
        )
        self.alarms.append(item)
        self.next_id += 1
        return item

    def add_timer(
        self,
        *,
        duration: datetime.timedelta,
        now: datetime.datetime,
        name: str = ""
    ) -> Timer:
        item = Timer(
            duration=duration,
            end_time=now + duration,
            id_=self.next_id,
            name=name or "Timer {}".format(self.next_id),
        )
        self.alarms.append(item)
        self.next_id += 1
        return item

    def delete(self, id_: int) -> None:
        self.alarms.remove(self.get(id_))

    def update(self, now: datetime.datetime, *, missed: bool = False) -> bool:
        changed = False
        for item in self.alarms:
            changed = item.update(now, missed=missed) or changed
        return changed

    def next_deadline(self) -> Union[None, datetime.datetime]:
        deadlines = [
            item.end_time
            for item in self.alarms
            if item.state == State.ACTIVE and item.occurred_at is None
        ]
        return min(deadlines) if deadlines else None

    def model_dump(self) -> Dict[str, typing.Any]:
        return {
            "next_id": self.next_id,
            "alarms": [item.model_dump() for item in self.alarms],
        }

    def model_dump_json(self) -> str:
        return json.dumps(self.model_dump(), allow_nan=False)

    @classmethod
    def model_validate(cls, obj: Dict[str, typing.Any]) -> "typing.Self":
        self = cls()
        self.alarms = [Alarm.model_validate(item) for item in obj["alarms"]]
        ids = [item.id_ for item in self.alarms]
        self.next_id = int(obj["next_id"])
        if len(set(ids)) != len(ids) or self.next_id <= max(ids, default=-1):
            raise ValueError("Invalid item IDs or next_id")
        return self

    @classmethod
    def model_validate_json(cls, json_data: str) -> "typing.Self":
        return cls.model_validate(json.loads(json_data))

    def snapshot(self, now: datetime.datetime) -> Dict[str, typing.Any]:
        items = []
        notifications = []
        for item in self.alarms:
            obj = item.model_dump()
            obj["remaining"] = item.remaining(now).total_seconds()
            items.append(obj)
            if item.notification_active:
                notifications.append(
                    {
                        "id_": item.id_,
                        "name": item.name,
                        "occurred_at": obj["occurred_at"],
                        "missed": item.missed,
                    }
                )
        return {"items": items, "notifications": notifications}
