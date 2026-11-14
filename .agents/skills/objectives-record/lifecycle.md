# Starting and finishing

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
