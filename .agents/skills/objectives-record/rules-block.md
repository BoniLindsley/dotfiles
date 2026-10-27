# Rules block

Copy this block into `How to maintain this record`,
replacing `<branch>` with the name of the code branch.
It keeps the record usable when this skill is not available.
Change it only to follow a new version of this skill
that changes the block,
and log that change.
The version in the block is the last one that changed it.

```markdown
This record tracks objectives, tasks and decisions
so that work can resume in a later session.
It follows the objectives-record skill, version 5.1.0.

- Read this whole file before working, and again after compaction.
  Start from `Status` and `Next action`.
- Files under `details/` and `log/` are listed in `Details`
  or named by the decision they hold.
  Read one only when the work needs it.
  Never delete record content: move it into a detail file instead.
- This record exists only under `objectives/`
  on branch `meta/<branch>/objectives`,
  and tracks the code branch `<branch>`.
  Code branches never contain it,
  and this branch is never merged into them.
  It is checked out at `.meta/objectives/<branch>`
  in the code checkout, sparse to `objectives/`.
- Before changing something, check the `Applies` lines,
  and `grep '^applies:' details/*.md`, for entries that cover it.
- Run `git log --oneline meta/<branch>/objectives..<branch>`
  to find code commits this record does not describe yet.
- When code completes a task or objective, or changes a decision,
  merge the code branch up to the completing commit,
  and stage the record update into that merge.
  The message describes only the update,
  such as "Record T-053 done for O-008."
  Other updates are ordinary commits that change only `objectives/`.
- IDs (O-, AC-, T-, D-, C-, A-) are permanent.
  Never reuse them.
- A task is done only with evidence.
  An objective is completed only when its acceptance criteria pass.
- Record user decisions in their words, with the date.
- Never store secrets, credentials or tokens.
  Prefer relative paths.
```

Without git, replace the branch items with
"This record lives in `.meta/objectives/` in the project directory."
