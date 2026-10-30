# Starting, finishing and converting

## Starting

When no record exists:

1. Agree the objective with the user,
   with observable acceptance criteria and how to check each.
2. In git, create the objectives branch from the code branch
   and check it out as described in [git-setup.md](git-setup.md):
   `git branch meta/<branch>/objectives <branch>`,
   then the exclusion, worktree and sparse-checkout commands.
   Without git, create `.meta/objectives/` in the working directory.
3. In `objectives/`, create `entries/` and `log/`,
   and copy [record.sh](record.sh) from this skill.
4. Write the entries ([entries.md](entries.md)):
   at least one objective with its criteria
   and an ordered first plan in its `## Tasks`,
   a file for each of those tasks,
   and known decisions, constraints and assumptions.
5. Write `objectives/OBJECTIVES.md` with the layout in [SKILL.md](SKILL.md):
   the rules block and `Status` with an exact next action;
   run `sh record.sh list` and `sh record.sh check`.
6. Log the start, and commit, for example `Add O-001: <outcome>.`,
   before doing substantial project work.

## Finishing

Before marking an objective complete:

1. Check the actual artifacts and every acceptance criterion.
2. Resolve or explicitly close remaining blockers and decisions,
   and cancel tasks that are no longer needed, with the reason.
3. In the objective's entry, set `status: completed`
   and `completed: <date>`,
   and write `## Delivered`:
   what was delivered, where (paths, commits),
   what was left out or not verified,
   and the evidence for each criterion.
   Make sure `applies` names the delivered paths.
4. For each of its `data/` directories,
   keep or delete it, and log which.
5. Set `Current task: none`,
   replace `Next action` with follow-up or maintenance guidance,
   if any, and run `sh record.sh check`.
6. Record it in a merge of the code branch up to the final commit,
   and log it.

Nothing moves: the entry stays where it is,
and leaves `sh record.sh list` because of its status.
A finished objectives branch stays as the audit trail
and the starting point for later maintenance.

## Converting an older record

Convert only with the user's approval:
conversion rewrites the rules block and the layout,
and older versions may also move the worktree.
Until then, keep working with the record as it is,
following its own rules block,
and mention in the briefing that it can be converted.

### From version 5

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

### From version 4

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

### From version 3, named resumable-objective

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

### From an older state file

From a file such as `PROJECT_STATE.md`,
keep its objectives, tasks, decisions, assumptions,
evidence and log with their IDs,
arrange them as entries and an index as [SKILL.md](SKILL.md) describes,
and drop the old embedded protocol.
