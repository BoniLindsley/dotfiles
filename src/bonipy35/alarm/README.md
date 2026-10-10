# Alarm and timer service

`bonipy35.alarm` is a local, persistent alarm/timer service. The server owns
items, scheduling, notifications and the JSON state file. Clients submit
commands and display snapshots or events. Clients start the server when needed;
the server keeps running after clients disconnect.

This replaces the prototype in `bonipy35.alarm_`. Its data and wire formats are
not supported. Repeating alarms are outside the current specification.

## Items and time

An alarm has a unique integer ID, name, wall-clock deadline and lifecycle state:
`active`, `paused`, `stopped` or `triggered`. A timer additionally has a positive
duration. Starting or restarting a timer sets its deadline to now plus duration.
IDs are shared by alarms and timers and are not reused after deletion/restart.

Alarm creation accepts `HH:MM` or `YYYY-MM-DD HH:MM`. A time that has already
passed means its next occurrence, normally tomorrow. An exact match means now.
Date-only alarm input is rejected: silently choosing midnight would be surprising.
Inputs use local civil time; ambiguous/nonexistent daylight-saving times are
rejected. Stored timestamps use UTC, retaining microseconds.

Timers accept durations such as `1h30m`, `2d`, or `45s`. Remaining time is derived
from the deadline, never maintained by decrementing a counter.

Pausing records `paused_at`. A paused timer freezes its remaining time; resuming
shifts its deadline by the paused interval, including across server restarts.
A paused alarm keeps its original deadline and suspends notifications. Resuming
an overdue alarm activates a missed-deadline notification. Stopping disables
expiry and clears an active notification. Restarting a timer starts its original
duration anew. Alarms may be rescheduled with a new deadline.

## Notifications

An ordinary expiry changes an active item to `triggered` and activates a
notification. Deadlines missed while the server was down, or while an alarm was
paused, or supplied as an already-past explicit deadline, activate a notification
without changing the item's stored status.
Connection absence does not make an otherwise observed expiry a missed deadline.

Notifications are persistent occurrences independent of lifecycle state. Each
records its occurrence time (the deadline), whether it was missed, and the last
dismissal time. It remains active until globally dismissed. Repeated snapshots
may deliver the same notification; clients identify it by item ID and occurrence
and replace their displayed list rather than accumulating duplicates.

The server broadcasts changes immediately to connected clients. With no clients,
notifications remain stored. Every client explicitly requests a snapshot on
connection, including the active notification list. Updates return that list too.
Dismissals are persisted and broadcast to all clients. Restart/reschedule clears
the old occurrence; a new expiry creates a fresh one, even if its timestamp equals
an earlier dismissed deadline. Delete removes the item and its notification.

Dismissal is server-timestamped. Delivery is at least once: reconnect/refresh can
repeat an active notification, and a crash before a dismissal is committed can
repeat it. There are no per-client acknowledgements or notification history.

## Server and protocol

This implementation targets Linux (including Debian 9) and Python 3.5 or newer.
It uses a private Unix socket and a server lifetime lock. A separate client startup
lock serializes connection/startup so simultaneous clients share one server.
Startup uses an inherited readiness socket with a bounded wait; failures are
reported to the caller. A live endpoint is never unlinked by a losing server.

Messages are newline-delimited UTF-8 JSON, with a size limit. Requests carry an
integer request ID and a command; responses echo the ID. Events carry snapshots.
Reads buffer partial frames, and writes handle partial sends. Malformed requests
receive errors; malformed transport frames terminate that connection. Mutations
reserve space for future notifications and are rejected if the state would exceed
the frame limit. Slow clients with excessive queued output are disconnected.

The server uses socket readiness and a Linux realtime timerfd for the nearest
pending deadline. It never periodically polls. Clock changes cancel and rearm the
wall-clock timer; deadlines elapsed during system suspend are handled on resume.
A clock correction discovered while running is treated as observed expiry.
Countdown displays update on snapshots/input, not by polling the server.

Only the server reads/writes state. Writes use an atomic replacement in the same
directory; malformed state aborts startup instead of silently discarding data.
The default directory is `$XDG_STATE_HOME/bonipy35/alarm`, falling back to
`~/.local/state/bonipy35/alarm`. `--directory` selects an isolated instance.
Directory access is restricted to the current user. Same-user access is trusted;
there is no network listener or remote authentication.

## Commands

```sh
python -m bonipy35.alarm cli alarm 08:00 --name Breakfast
python -m bonipy35.alarm cli timer 10m --name Tea
python -m bonipy35.alarm cli status
python -m bonipy35.alarm cli pause 0
python -m bonipy35.alarm cli resume 0
python -m bonipy35.alarm cli stop 0
python -m bonipy35.alarm cli restart 0
python -m bonipy35.alarm cli reschedule 0 '2026-10-12 08:00'
python -m bonipy35.alarm cli dismiss 0
python -m bonipy35.alarm cli delete 0
python -m bonipy35.alarm cli watch
python -m bonipy35.alarm cmd
python -m bonipy35.alarm gui
python -m bonipy35.alarm tui
python -m bonipy35.alarm server
```

Place `--directory PATH` before the client command, e.g.
`python -m bonipy35.alarm cli --directory /tmp/my-alarm timer 10s`.
`cmd` accepts the same commands interactively and shows server events while
waiting for input. `watch` waits for events until interrupted. GUI and TUI provide
item creation, pause/resume, stop, timer restart, deletion and notification
dismissal. Closing an interface leaves the service running.

`python -m bonipy35.alarm cli shutdown` stops the selected service without
removing persisted state. SIGINT/SIGTERM also shut it down cleanly.

## Validation

Run `python -m pytest -q tests/test_bonipy35/test_alarm` for lifecycle, parsing,
transport and server/client integration checks. Run `python -m tox` for the full
repository checks. Development tools are current; runtime syntax remains Python
3.5 compatible.
