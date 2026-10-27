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
3. Write `objectives/OBJECTIVES.md` with the layout in [SKILL.md](SKILL.md):
   the rules block, at least one objective,
   an ordered first plan with task IDs,
   known decisions and assumptions,
   and an exact next action.
4. Commit it, for example `Add O-001: <outcome>.`,
   before doing substantial project work.

## Finishing

Before marking the work complete:

1. Check the actual artifacts and every acceptance criterion.
2. Resolve or explicitly close remaining blockers and decisions.
3. Record the final evidence and mark the objectives `completed`.
4. Move them to detail files
   as in "Keeping the index short" in [SKILL.md](SKILL.md).
5. Set `Current task: none`,
   and replace `Next action` with follow-up or maintenance guidance,
   if any.
6. Record it in a merge of the code branch up to the final commit.

A finished objectives branch stays as the audit trail
and the starting point for later maintenance.

## Converting an older record

Convert only with the user's approval:
conversion moves the worktree and rewrites the rules block.
Until then, keep working with the record as it is,
following its own rules block,
and mention in the briefing that it can be converted.

From version 4
(checked out at `.objectives/<branch>`):

1. Move the worktree under `.meta/`:

   ```sh
   exclude="$(git rev-parse --git-common-dir)/info/exclude"
   grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
   mkdir -p .meta/objectives
   git worktree move .objectives/<branch> .meta/objectives/<branch>
   ```

   When no worktrees are left in `.objectives/`,
   remove the empty directory and the `/.objectives/` exclusion.
2. Replace the rules block with the one in [rules-block.md](rules-block.md).
3. Move decisions that still apply and take more than about five lines
   into detail files, leaving summaries,
   as in "Keeping the index short" in [SKILL.md](SKILL.md).
   Remove their lines from `Details`.
4. Add `Applies` to the entries that need it (invariant 12),
   and the new header keys and body headings to detail files.
   Remove files from `Artifacts` once an `Applies` line names them.
5. Commit, for example `Convert the record to objectives-record 5.1.0.`,
   and log the conversion.

From version 3, named resumable-objective
(`OBJECTIVES.md` at the root of the objectives branch,
checked out at `../<repository>.objectives/<branch>`):

1. On the objectives branch, move the file into the directory:
   `mkdir objectives`, then `git mv OBJECTIVES.md objectives/OBJECTIVES.md`.
2. Move completed and cancelled objectives, finished tasks,
   long decision records and old log lines into detail files,
   as in "Keeping the index short" in [SKILL.md](SKILL.md),
   and add the `Details` section.
   Rename the section `How to maintain this file`
   to `How to maintain this record`,
   rename `Progress` in `Status` to `Position`
   and shorten it to the current position.
3. Replace the rules block with the one in [rules-block.md](rules-block.md).
4. Commit, for example `Convert the record to objectives-record 5.1.0.`,
   and log the conversion.
5. Move the worktree into the code checkout
   and make it sparse:

   ```sh
   exclude="$(git rev-parse --git-common-dir)/info/exclude"
   grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
   mkdir -p .meta/objectives
   git worktree move ../<repository>.objectives/<branch> .meta/objectives/<branch>
   git -C .meta/objectives/<branch> sparse-checkout set --no-cone '/objectives/'
   ```

From an older state file, such as `PROJECT_STATE.md`,
keep its objectives, tasks, decisions, assumptions,
evidence and log with their IDs,
arrange them as [SKILL.md](SKILL.md) describes,
and drop the old embedded protocol.
