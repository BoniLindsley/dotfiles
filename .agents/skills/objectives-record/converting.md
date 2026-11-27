# Converting an older record

Convert only with the user's approval:
conversion rewrites the rules block and the layout,
and older versions may also move the worktree.
Until then, keep working with the record as it is,
following its own rules block,
and mention in the briefing that it can be converted.

## From version 6.3

1. Copy [record.sh](record.sh) and replace the rules block
   with the one in [rules-block.md](rules-block.md).
   From now on, do not merge the code branch into the objectives branch;
   the merges already made stay in its history.
2. Find the newest code commit the record describes,
   usually the code side of the last merge into the objectives branch,
   on the code branch, by its subject if it was rebased.
   Cite it in a log line, for example
   `- Recorded up to commit_qurnxwovwwourvty (add: flip on bubbles).`,
   so that `sh record.sh unrecorded` starts there.
3. Optionally, replace cited hashes with stable IDs,
   from `sh record.sh cite <hash>` in the code checkout,
   where the hash is still on the code branch,
   or the commit can be found there by its subject.
   Leave the others as they are.
4. Commit, for example `Convert the record to objectives-record 6.4.0.`,
   and log the conversion.

## From version 6.2

1. Copy [record.sh](record.sh) and replace the rules block
   with the one in [rules-block.md](rules-block.md).
2. Run `sh record.sh check` and fix what it reports,
   following the notes under `OBJECTIVES.md` in [SKILL.md](SKILL.md).
   What leaves `Status` and `Handoff` as history
   becomes log lines dated the day of the conversion,
   unless the log already has it.
3. Optionally, move each long decision's `## Decision`
   and `## Consequences` above its `## Question`.
4. Commit, for example `Convert the record to objectives-record 6.3.0.`,
   and log the conversion.
5. Follow "From version 6.3".

## From version 5

Version 5 keeps open entries in the index
and finished ones in `details/`.
Conversion gives every entry its own file;
nothing is summarized or dropped.
Prefer one commit per step, so each is easy to review.

1. Create `entries/` and copy [record.sh](record.sh).
2. Move decision files: `git mv details/D-xxx.md entries/D-xxx.md`,
   adjusting their headers to [entries.md](entries.md).
   Decisions that are only in the index become new files,
   their index text under `## Decision`.
   Rejected approaches become decisions with status `rejected`,
   with new IDs.
3. Move objective files the same way,
   then give each task inside them a file of its own,
   leaving the objective's `## Tasks` as an ordered list of IDs.
   Open objectives and tasks in the index become files too.
   A task title too long for a one-sentence `summary`
   goes whole into `## Scope`.
   Evidence kept in dated progress notes moves under `## Evidence`,
   or `## Evidence` says it is in the notes above.
   Take each done task's `completed:` date from the log.
   Every entry starts with `---`, `id:`, `status:`, `summary:`,
   and for tasks `objective:`.
4. Keep acceptance criteria IDs,
   written as `- AC-016:` at the start of a line
   in their objective's `## Acceptance criteria`.
5. Give each constraint and assumption a file.
   Conventions in `Handoff` become constraints.
6. Write every ID range in full, in entries and in the index.
7. Move log lines, from the index's `## Log` and from monthly files
   such as `log/2026-10.md`, into `log/<YYYY-MM-DD>.md` by date,
   one physical line per entry, the date only in the file name.
8. Replace the rules block with the one in [rules-block.md](rules-block.md),
   remove the sections `Objectives`, `Tasks`, `Decisions`,
   `Constraints and assumptions`, `Rejected approaches` and `Details`,
   and keep `Status`, `Handoff` and `Artifacts`.
9. Run `sh record.sh check`; `details/` is then empty.
10. Commit, for example `Convert the record to objectives-record 6.2.0.`,
    and log the conversion.
11. Follow "From version 6.2".

## From version 4

Version 4 is checked out at `.objectives/<branch>`.
First move the worktree under `.meta/`:

```sh
exclude="$(git rev-parse --git-common-dir)/info/exclude"
grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
mkdir -p .meta/objectives
git worktree move .objectives/<branch> .meta/objectives/<branch>
```

When no worktrees are left in `.objectives/`,
remove the empty directory and the `/.objectives/` exclusion.
Then follow "From version 5".

## From version 3, named resumable-objective

Version 3 keeps `OBJECTIVES.md` at the root of the objectives branch,
checked out at `../<repository>.objectives/<branch>`.

1. On the objectives branch, move the file into the directory:
   `mkdir objectives`, then `git mv OBJECTIVES.md objectives/OBJECTIVES.md`.
2. Move the worktree into the code checkout and make it sparse:

   ```sh
   exclude="$(git rev-parse --git-common-dir)/info/exclude"
   grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
   mkdir -p .meta/objectives
   git worktree move ../<repository>.objectives/<branch> .meta/objectives/<branch>
   git -C .meta/objectives/<branch> sparse-checkout set --no-cone '/objectives/'
   ```

3. Follow "From version 5", taking every entry from the index.
   Rename `Progress` in `Status` to `Position`
   and shorten it to the current position.

## From an older state file

From a file such as `PROJECT_STATE.md`,
keep its objectives, tasks, decisions, assumptions,
evidence and log with their IDs,
arrange them as entries and an index as [SKILL.md](SKILL.md) describes,
and drop the old embedded protocol.
