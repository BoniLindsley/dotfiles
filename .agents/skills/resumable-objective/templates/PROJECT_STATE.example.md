# Project State — example excerpt

> **RECOVERY DIRECTIVE FOR ANY FUTURE AGENT**
>
> This project uses a self-contained resumable state file. Read the complete real `PROJECT_STATE.md` before working and preserve its embedded protocol block.

## Objectives and success criteria

- **O-001** `[active]` — Automatically back up family photos from a home server to encrypted off-site storage.
  - Acceptance criteria:
    - AC-001: New photos are copied off-site automatically.
    - AC-002: Restore of a sampled folder succeeds on a clean machine.
    - AC-003: Backup failure produces a visible alert.
  - Verification:
    - AC-001: add a test photo and verify remote copy.
    - AC-002: perform documented restore test.
    - AC-003: simulate a failed backup and observe alert.

## Plan / tasks

- **T-004** `[in_progress]` — Add failure notification to backup job.
  - Objective: O-001
  - Depends on: T-003
  - Size: S
  - Why: required by AC-003.
  - Done when: a forced backup failure triggers one notification and normal success does not.
  - Verification evidence: pending.

## Decisions

- **D-002** `[rejected]` — Replace the existing backup tool with a different sync utility.
  - Context: notification support initially looked easier elsewhere.
  - Decision/rationale: rejected because the current tool already satisfies encryption and restore requirements; migration cost is not justified for notification alone.
  - Revisit when: current tool can no longer access the selected storage provider.
  - Asked user: not required.
  - User response: n/a.

## Current task

- Task: T-004
- Progress: failure exit code is detected; notification function exists but is not yet wired into the systemd service. The unit currently calls `/opt/photo-backup/run.sh` directly.
- Last verified result: running `run.sh --simulate-failure` exits 2 and writes the expected error to the journal.
- Blocker: none.

## Next action

Edit `~/.config/systemd/user/photo-backup.service` so `ExecStart` invokes the wrapper that calls `notify_failure` on non-zero exit; then run the simulated-failure test and verify exactly one notification appears.

## Next session handoff

- Start by: make the service change described in `Next action`.
- Relevant context: `run.sh`, `notify.sh`, and the user systemd service.
- Expected result: simulated failure creates one desktop notification while preserving exit status 2.
- Do not redo: do not replace the backup tool; D-002 records why.
- Revalidate if stale: confirm the off-site provider endpoint if more than 14 days have passed.
- Pending decisions/blockers: none.
