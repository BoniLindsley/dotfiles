# Where the record lives

## In git

Each code branch with objectives of its own
has an objectives branch named `meta/<branch>/objectives`,
for example `meta/dev/objectives` for `dev`.
The objectives directory is `objectives/` at its root, and only there.

- **One objectives branch per code branch.**
  Different code branches have different goals or progress,
  so each keeps its own record.
  The branch name says which code branch it follows,
  so the record does not repeat it.
  An objectives branch merges in only its own code branch.
- **Code branches never contain it.**
  Code commits never add or change anything under `objectives/`.
- **The branch runs parallel to the code.**
  `meta/<branch>/objectives` starts from its code branch
  and merges it in as work completes.
  It is never merged back into a code branch,
  and nothing under `objectives/` is cherry-picked into one.
- **The `meta/` prefix** marks the branch as about the project,
  not part of it.
  Other branches of this kind,
  such as `meta/<branch>/time-tracking`,
  belong in the same namespace.

Check the objectives branch out at `.meta/objectives/<branch>`
inside the code checkout,
limited to the objectives directory with a sparse checkout,
so that it is within reach of tools that work in the project directory
without holding a second copy of the code:

```sh
exclude="$(git rev-parse --git-common-dir)/info/exclude"
grep -qxF '/.meta/' "$exclude" || echo '/.meta/' >> "$exclude"
git worktree add --no-checkout .meta/objectives/<branch> meta/<branch>/objectives
git -C .meta/objectives/<branch> sparse-checkout set --no-cone '/objectives/'
git -C .meta/objectives/<branch> checkout
```

The index is then `.meta/objectives/<branch>/objectives/OBJECTIVES.md`.

- `.meta/` holds agent state for the project, not only this record,
  such as the instruction backlog.
  Keep the record under `.meta/objectives/` and nothing else there.
- The exclusion goes in `.git/info/exclude`, not `.gitignore`,
  so that no code commit mentions it.
  The command adds it only if it is missing.
- Merges of the code branch still bring in all of its files;
  the sparse checkout only keeps them out of this worktree.
- `git clean -fdx` in the code checkout skips the worktree,
  because it holds its own repository link;
  only `git clean -ffdx` would remove it.
- Tools that skip hidden directories,
  such as pytest's default collection, also skip it.

Read the index without a worktree with
`git show meta/<branch>/objectives:objectives/OBJECTIVES.md`.

When a new code branch starts from one that has objectives,
give it its own objectives branch only if it has goals of its own.
Refer to the parent's entries by branch and ID,
for example `meta/dev/objectives O-008`,
since IDs are unique only within one record.

## Without git

Keep the objectives directory at `.meta/objectives/` in the working directory,
and skip the branch rules.
If the location is not writable,
say that progress cannot be kept between sessions.
Never claim persistence without a successful write.

## Not in temporary directories

Do not keep the record in `/tmp`, a scratchpad or another temporary directory,
even when it is easier to reach.
They are cleared on restart or by cleaners,
and session scratch directories can be wiped between sessions,
so a record there can vanish without warning.
Copies there are fine for scratch work, never as the record.
