# Project State

> **RECOVERY DIRECTIVE FOR ANY FUTURE AGENT**
>
> This file is both the persistent state of this project and the operating manual for continuing it. Read the entire file, especially the Embedded operating protocol, before making project changes. Update this file as meaningful work progresses. Preserve the embedded protocol block verbatim during ordinary updates. If protocol text is damaged, preserve project state and reconstruct the protocol from any available copy rather than discarding state.

```yaml
state_protocol:
  name: resumable-objective
  version: 2.0.0
  state_format: markdown
  protocol_migration: explicit-only
  protocol_body_sha256: 5fc8e953b6ff9f9174899ca0954f3f1aaecfd018b977e0666794ce0ba7cc75c1
project:
  name: <project name>
  status: active
state:
  created: <ISO date or timestamp if known>
  updated: <ISO date or timestamp if known>
  last_session: <ISO date or timestamp if known>
  revalidate_after_days: 14
  session_budget: unknown
```

<!-- BEGIN RESUMABLE-OBJECTIVE OPERATING PROTOCOL v2.0.0 -->
## Embedded operating protocol

This protocol is deliberately embedded so the project remains resumable even when the original skill is unavailable.

### On every session start

1. Read this whole file before substantive project work.
2. Reconcile it against current user instructions and relevant project artifacts.
3. Repair contradictions, stale statuses, broken references, or completed items lacking evidence; log material repairs.
4. If enough time has passed or external assumptions may have changed, revalidate only the assumptions that could materially affect the next work.
5. Determine the current objective, current task, blockers, pending decisions, and exact next action.
6. If the user gives a time budget, prefer work that can reach a clean checkpoint within it. Otherwise prefer a small, high-value ready task rather than asking about time unless it materially changes the plan.

### While working

1. Keep objectives tied to observable acceptance criteria and verification methods.
2. Keep tasks ordered, dependency-aware, independently verifiable, and identified by stable IDs.
3. Track material decisions, including rejected alternatives with rationale, deferred choices with revisit triggers, and questions awaiting user decisions.
4. Update this file at meaningful checkpoints: task start/switch, meaningful progress, new blocker/constraint, material decision, task completion/failure/reopen, scope change, and before risky or interruption-prone work when practical.
5. Do not mark a task done without evidence. If later evidence disproves completion, reopen it and record why.
6. Maintain one `in_progress` task normally; document intentional parallel work.
7. Prefer safe writes and preserve concurrent changes when detectable.
8. Never store secrets, credentials, tokens, private keys, or unnecessary personal data here.

### Before ending a work period

1. Record what changed and how it was verified.
2. Update the current task's exact progress rather than only a percentage.
3. Record blockers and unresolved decisions.
4. Write one concrete `Next action` that a future agent can execute directly.
5. Include relevant paths/symbols/commands/artifacts, expected result, and hazards or rejected approaches that should not be repeated.
6. Ensure the state invariants below hold.

### State invariants

- Every objective has a unique stable ID and status.
- Every active objective has acceptance criteria and verification methods.
- Every task has a unique stable ID and references an existing objective.
- Every dependency points to an existing task or is explicitly external.
- Every `done` task has verification evidence.
- Every `blocked` task names its blocker.
- Every rejected decision has a rationale.
- Every deferred decision has a revisit trigger.
- Every `awaiting_user` decision records the question asked.
- `Current task` is `none` or references an `in_progress` task.
- Normally only one task is `in_progress`.
- A `completed` objective has evidence that every acceptance criterion passed.
- `Next action` is executable and specific.
- This Recovery directive and the complete embedded protocol remain present.

### Protocol preservation and migration

Preserve this entire protocol block verbatim during ordinary project-state edits. Put project-specific information outside it.

Change the protocol only through an explicit migration. A migration must preserve project state/history, record old and new versions, explain the reason, replace the block deliberately rather than piecemeal, recompute the protocol fingerprint, validate required sections afterward, and add a progress-log entry.

The YAML header stores a SHA-256 fingerprint of the canonical protocol body (the bytes strictly between the BEGIN and END marker lines). When tools permit, compare it during reconciliation. A mismatch means the protocol was edited or corrupted, or a migration was not finalized. Preserve project state while repairing it.

If this protocol is incomplete or damaged, preserve the project state and reconstruct the protocol from an available skill/template or other intact copy. Do not erase state merely to obtain a clean template.
<!-- END RESUMABLE-OBJECTIVE OPERATING PROTOCOL v2.0.0 -->

# Durable project knowledge

## Objectives and success criteria

- **O-001** `[active]` — <desired outcome>
  - Acceptance criteria:
    - AC-001: <observable condition>
  - Verification:
    - AC-001: <test, command, artifact inspection, or user confirmation>
  - Completion evidence: <none until verified>

## Constraints and assumptions

### Constraints
- <constraint and why it matters>

### Assumptions to revalidate
- **A-001** — <assumption>
  - Last checked: <date / never>
  - Recheck when: <trigger, dependency change, or after revalidation interval>
  - Impact if false: <what changes>

## Plan / tasks

- **T-001** `[todo]` — <task>
  - Objective: O-001
  - Depends on: none
  - Size: S
  - Why: <reason this task exists>
  - Done when: <observable completion condition>
  - Verification evidence: <none until done>

## Decisions

- **D-001** `[proposed]` — <decision/question>
  - Context: <why this matters>
  - Options: <options if useful>
  - Decision/rationale: <pending>
  - Revisit when: <required for deferred decisions>
  - Asked user: <not asked / exact question + date/session>
  - User response: <pending / response>

## Rejected approaches / do-not-repeat

- <approach> — <why it was rejected; conditions that would justify reconsidering it>

## Artifacts and verification map

- `<relative/path>` — <purpose; relevant objective/task; last verified state>

# Execution state

## Session context

- Last session: <date/timestamp>
- Available time this session: unknown
- Resumption/staleness check: <not required / findings>

## Current task

- Task: none
- Progress: <exact state of unfinished work>
- Last verified result: <command/test/inspection and result>
- Blocker: none

## Next action

<One concrete executable step. Include file/symbol/command when known and the expected immediate result.>

## Blockers and risks

- <blocker/risk, owner if relevant, impact, mitigation/next check>

## Pending user decisions

- <decision IDs or none>

## Next session handoff

- Start by: <specific action>
- Relevant context: <paths/symbols/commands/artifacts>
- Expected result: <what should happen next>
- Do not redo: <rejected work or already-verified work>
- Revalidate if stale: <assumptions/external facts>
- Pending decisions/blockers: <IDs or none>

# Progress and evidence

## Completed subtasks

- <T-ID> — <result> — Evidence: <test/artifact/user confirmation>

## Progress log

- <ISO date or timestamp> — Initialized resumable project state.

## Protocol migrations

- None.
