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
- **Code branches never contain it.**
  Code commits never add or change anything under `objectives/`.
- **The branch runs parallel to the code.**
  `meta/<branch>/objectives` starts from its code branch,
  and the two are never merged into each other after that.
  Nothing under `objectives/` is cherry-picked into a code branch.
  The record follows the code by citing its commits
  by stable ID (below), which survives rebases;
  a merge would point at commits that a rebase replaces.
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
- The branch still holds the code files it started from;
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

## Recording changes

In git, every change to the record is a commit on its objectives branch.
Each commit describes the change to objectives, tasks or decisions,
not the code.
The record itself keeps the history, in its entries and its log:
git makes it easy to share and to see when things changed,
but nothing should be recoverable only from git.

### Commit record updates

Every update is an ordinary commit on the objectives branch
that changes only files under `objectives/`.
The message describes only the change,
for example `Record T-053 done for O-008.`
or `Accept D-027: the first pancake goes to the cook.`

When code completes a task or an objective,
cite the commit that completes it by stable ID
in the entry's `## Evidence` or `## Delivered`,
in the same update that marks it done.
When several tasks were finished before being recorded,
cite each one's own completing commit.

### Find what has not been recorded

```sh
sh .meta/objectives/<branch>/objectives/record.sh unrecorded
```

This lists the code commits on `<branch>`
newer than the newest commit the record cites,
which is work the record may not describe yet.
Check it at the start of every session.
Commits that complete nothing,
such as a refactor before a task's code,
stay listed until a later commit is cited.
If the newest cited commit loses its stable ID,
the list starts from an older one:
it shows more, never less.

### Cite commits by stable ID

Rebasing or amending the code branch gives its commits new hashes,
so a hash in the record stops naming the commit.
Cite a code commit by a stable ID instead,
such as `commit_qurnxwovwwourvty`,
followed by its subject for readers:

```sh
sh .meta/objectives/<branch>/objectives/record.sh cite <commit>
```

`cite` prints the commit's stable ID, creating it if needed:
`commit_` and 16 random letters from `k` to `z`,
which are never hex digits, so it cannot be taken for a hash.
It keeps the ID as a note in `refs/notes/stable-id`,
and adds that ref to `notes.rewriteRef`,
so that `git rebase` and `git commit --amend`
copy the note to the rewritten commit.
Nothing is noted or configured until a commit is cited.

`sh record.sh commit <ID>` lists the commits on code branches
whose note holds the ID,
and `sh record.sh check` reports IDs that no such commit holds.

- **Squashing** keeps the notes of all the commits squashed,
  so every ID still names the result.
- **Lost IDs:** splitting a commit, `git cherry-pick`,
  merges by a hosting service, `git filter-repo`,
  and rewrites in a clone without the configuration
  copy no notes.
  Find the commit by the subject cited with it,
  and cite it again.
- **Not shared by default:** `git push` does not send notes.
  Push `refs/notes/stable-id` with the objectives branch,
  only when the user asks,
  and set `notes.rewriteRef` in the other clone.
- Cite a hash only for a commit
  that has been published on a branch that is never rewritten.

### Publishing

Push objectives branches only when the user asks.
Unpublished commits on an objectives branch may be rewritten
to improve them.
Published ones may not.

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
