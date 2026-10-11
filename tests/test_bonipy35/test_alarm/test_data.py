#!/usr/bin/env python3

# Standard libraries.
import datetime

# External dependencies.
import pytest

# Internal modules.
from bonipy35.alarm.data import (
    Alarm,
    Datetime,
    State,
    NotificationState,
    Timer,
    UserData,
    utc_now,
)


class TestDatetime:
    def test_round_trip_preserves_instant_and_microseconds(
        self, now: datetime.datetime
    ) -> None:
        instant = now.replace(microsecond=123456).astimezone(
            datetime.timezone(datetime.timedelta(hours=3))
        )
        assert (
            Datetime.model_validate_datetime(Datetime.model_dump(instant))
            == instant
        )

    def test_naive_timestamp_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone"):
            Datetime.model_dump(datetime.datetime(2026, 1, 1))

    def test_now_is_utc(self) -> None:
        assert utc_now().utcoffset() == datetime.timedelta()


class TestAlarmUpdate:
    def test_expiry_notifies_once_without_changing_scheduling(
        self, now: datetime.datetime
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        assert item.update(now - datetime.timedelta(seconds=1)) is False
        assert item.update(now) is True
        assert item.state == State.RUNNING
        assert item.notification_state == NotificationState.TRIGGERED
        assert item.notification_active
        assert item.update(now + datetime.timedelta(days=1)) is False
        item.dismiss(now)
        assert not item.notification_active
        assert item.update(now + datetime.timedelta(days=2)) is False

    def test_stopped_item_does_not_expire(
        self, now: datetime.datetime
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        item.stop()
        assert not item.update(now)
        assert not item.notification_active


class TestNotificationState:
    def test_schedule_controls_suppress_without_acknowledging(
        self, now: datetime.datetime
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        assert item.notification_state.value == "pending"
        item.update(now)
        item.pause(now)
        assert item.notification_state == NotificationState.TRIGGERED
        assert not item.notification_active
        item.resume(now + datetime.timedelta(minutes=1))
        assert item.notification_active
        item.stop()
        assert item.notification_state == NotificationState.TRIGGERED
        assert not item.notification_active
        restored = Alarm.model_validate(item.model_dump())
        restored.dismiss(now)
        assert restored.notification_state == NotificationState.DISMISSED
        assert restored.state == State.STOPPED

    @pytest.mark.parametrize("stored_state", ["active", "triggered"])
    def test_previous_format_migrates_without_losing_acknowledgement(
        self, now: datetime.datetime, stored_state: str
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        item.update(now)
        item.dismiss(now)
        obj = item.model_dump()
        obj["state"] = stored_state
        obj["missed"] = True
        restored = Alarm.model_validate(obj)
        assert restored.state == State.RUNNING
        assert restored.notification_state == NotificationState.DISMISSED
        assert "missed" not in restored.model_dump()


class TestAlarmPauseResume:
    def test_resume_overdue_keeps_deadline_and_active_status(
        self, now: datetime.datetime
    ) -> None:
        item = Alarm(
            end_time=now + datetime.timedelta(minutes=5), id_=0, name="Wake"
        )
        item.pause(now)
        assert item.remaining(
            now + datetime.timedelta(hours=1)
        ) == datetime.timedelta(minutes=5)
        assert not item.update(now + datetime.timedelta(hours=1))
        assert not item.notification_active
        item = Alarm.model_validate(item.model_dump())
        item.resume(now + datetime.timedelta(hours=1))
        assert item.end_time == now + datetime.timedelta(minutes=5)
        assert item.paused_at is None
        assert item.state == State.RUNNING
        assert item.notification_active

    def test_resume_future_alarm(self, now: datetime.datetime) -> None:
        item = Alarm(
            end_time=now + datetime.timedelta(hours=1), id_=0, name="Wake"
        )
        item.pause(now)
        item.resume(now + datetime.timedelta(minutes=1))
        assert item.state == State.RUNNING
        assert not item.notification_active

    @pytest.mark.parametrize("operation", ["pause", "resume"])
    def test_invalid_transitions(
        self, now: datetime.datetime, operation: str
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake", state=State.STOPPED)
        with pytest.raises(ValueError):
            getattr(item, operation)(now)


class TestTimerPauseResume:
    def test_resume_after_restart_freezes_remaining(
        self, now: datetime.datetime
    ) -> None:
        item = Timer(
            duration=datetime.timedelta(minutes=10),
            end_time=now + datetime.timedelta(minutes=10),
            id_=1,
            name="Tea",
        )
        paused = now + datetime.timedelta(minutes=3)
        item.pause(paused)
        restored = Alarm.model_validate(item.model_dump())
        resumed = now + datetime.timedelta(days=1)
        restored.resume(resumed)
        assert restored.end_time == resumed + datetime.timedelta(minutes=7)
        assert restored.remaining(resumed) == datetime.timedelta(minutes=7)
        assert not restored.notification_active

    def test_clock_backwards_does_not_shorten_timer(
        self, now: datetime.datetime
    ) -> None:
        item = Timer(
            duration=datetime.timedelta(minutes=1),
            end_time=now + datetime.timedelta(minutes=1),
            id_=0,
            name="Tea",
        )
        item.pause(now)
        item.resume(now - datetime.timedelta(seconds=1))
        assert item.end_time == now + datetime.timedelta(minutes=1)


class TestAlarmDismiss:
    def test_clock_backwards_dismissal_is_effective(
        self, now: datetime.datetime
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        item.update(now)
        item.dismiss(now - datetime.timedelta(hours=1))
        assert not item.notification_active
        assert item.last_dismissed_at == now

    def test_no_notification_rejected(self, now: datetime.datetime) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        with pytest.raises(ValueError, match="no notification"):
            item.dismiss(now)

    def test_reschedule_same_deadline_creates_fresh_occurrence(
        self, now: datetime.datetime
    ) -> None:
        item = Alarm(end_time=now, id_=0, name="Wake")
        item.update(now)
        item.dismiss(now)
        item.reschedule(now)
        item.update(now)
        assert item.notification_active
        item.stop()
        assert not item.notification_active


class TestTimerStart:
    def test_restart_clears_pause_and_dismissal(
        self, now: datetime.datetime
    ) -> None:
        item = Timer(
            duration=datetime.timedelta(minutes=1),
            end_time=now,
            id_=0,
            name="Tea",
        )
        item.update(now)
        item.dismiss(now)
        item.start(now)
        assert item.end_time == now + datetime.timedelta(minutes=1)
        assert item.state == State.RUNNING
        assert item.occurred_at is None and item.last_dismissed_at is None

    @pytest.mark.parametrize("seconds", [0, -1])
    def test_nonpositive_duration(
        self, now: datetime.datetime, seconds: int
    ) -> None:
        with pytest.raises(ValueError, match="positive"):
            Timer(
                duration=datetime.timedelta(seconds=seconds),
                end_time=now,
                id_=0,
                name="Tea",
            )


class TestUserData:
    def test_ids_not_reused_after_delete_and_round_trip(
        self, now: datetime.datetime
    ) -> None:
        state = UserData()
        alarm = state.add_alarm(end_time=now)
        timer = state.add_timer(
            duration=datetime.timedelta(minutes=1), now=now
        )
        assert [alarm.id_, timer.id_] == [0, 1]
        state.delete(timer.id_)
        restored = UserData.model_validate_json(state.model_dump_json())
        assert restored.add_alarm(end_time=now).id_ == 2
        with pytest.raises(ValueError, match="Unknown"):
            restored.get(timer.id_)

    def test_snapshot_and_next_deadline(self, now: datetime.datetime) -> None:
        state = UserData()
        assert state.next_deadline() is None
        alarm = state.add_alarm(end_time=now, name="Wake")
        timer = state.add_timer(
            duration=datetime.timedelta(minutes=1), now=now, name="Tea"
        )
        timer.pause(now)
        assert state.next_deadline() == now
        assert state.update(now)
        assert state.next_deadline() is None
        snapshot = state.snapshot(now)
        assert snapshot["notifications"] == [
            {
                "id_": alarm.id_,
                "name": "Wake",
                "occurred_at": Datetime.model_dump(now),
                "notification_state": "triggered",
            }
        ]
        alarm.dismiss(now)
        assert not state.snapshot(now)["notifications"]
        assert not state.update(now)
        assert (
            UserData.model_validate_json(state.model_dump_json()).model_dump()
            == state.model_dump()
        )

    @pytest.mark.parametrize(
        "corruption", ["duplicate", "next_id", "negative", "paused"]
    )
    def test_invalid_persisted_state(
        self, now: datetime.datetime, corruption: str
    ) -> None:
        state = UserData()
        state.add_alarm(end_time=now)
        obj = state.model_dump()
        if corruption == "duplicate":
            obj["alarms"].append(obj["alarms"][0])
        elif corruption == "next_id":
            obj["next_id"] = 0
        elif corruption == "negative":
            obj["alarms"][0]["id_"] = -1
        else:
            obj["alarms"][0]["state"] = "paused"
        with pytest.raises(ValueError):
            UserData.model_validate(obj)
