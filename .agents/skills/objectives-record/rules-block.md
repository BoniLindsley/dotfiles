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
It follows the objectives-record skill, version 6.0.0.

- Read this whole file before working, and again after compaction.
  Start from `Status` and `Next action`.
- Each objective, task, decision, constraint and assumption
  is a file `entries/<ID>.md`, and the files are authoritative.
  `Open entries` lists those still open; rebuild it with
  `awk -f list.awk entries/*.md | sort | cut -f 2-`
  and trust the files where the two differ.
- Read an entry when the work needs it:
  `Next action` or the current task names it,
  or its `applies:` covers what the work changes,
  as `grep -l '^applies:.*<path>' entries/*.md` finds.
- Headers hold one `key: value` per line.
  Write IDs in full wherever they appear, never as ranges.
- A new ID is the highest of its prefix in `entries/` and `log/`
  plus one, three digits:
  `grep -rohwE 'T-[0-9]+' entries log | sort -t- -k2 -n | tail -1`.
  Create its file only if none exists.
  One session writes this record at a time.
  Acceptance criteria take record-wide IDs the same way (`AC-`),
  each defined once, as `- AC-020:` in its objective.
  IDs are permanent; never reuse them.
- Log lines record events, one per line naming full IDs,
  in `log/<YYYY-MM-DD>.md`; never in this file or in entries.
- Files under `data/<ID>/` are named by that entry.
  Never delete record content;
  only data no longer needed may be deleted, with a log line.
- This record exists only under `objectives/`
  on branch `meta/<branch>/objectives`,
  and tracks the code branch `<branch>`.
  Code branches never contain it,
  and this branch is never merged into them.
  It is checked out at `.meta/objectives/<branch>`
  in the code checkout, sparse to `objectives/`.
- Run `git log --oneline meta/<branch>/objectives..<branch>`
  to find code commits this record does not describe yet.
- When code completes a task or objective, or changes a decision,
  merge the code branch up to the completing commit,
  and stage the record update into that merge.
  The message describes only the update,
  such as "Record T-053 done for O-008."
  Other updates are ordinary commits that change only `objectives/`.
- A task is done only with evidence.
  An objective is completed only when its acceptance criteria pass.
- Record user decisions in their words, with the date.
- Never store secrets, credentials or tokens.
  Prefer relative paths.
```

Without git, replace the branch items with
"This record lives in `.meta/objectives/` in the project directory."
