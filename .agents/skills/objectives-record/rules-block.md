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
It follows the objectives-record skill, version 6.1.0.

- Read this whole file before working, and again after compaction.
  Start from `Status` and `Next action`.
- Each objective, task, decision, constraint and assumption
  is a file `entries/<ID>.md`, and the files are authoritative.
  `record.sh` beside this file keeps the rest consistent:
  `sh record.sh update` rewrites `Open entries` from them,
  `sh record.sh check` checks this record's rules,
  `sh record.sh applies <path>` lists the entries covering a path,
  and `sh record.sh next T` gives the next free ID of a prefix.
- Read an entry when the work needs it:
  `Next action` or the current task names it,
  or its `applies:` covers what the work changes.
  `applies:` paths are relative to the repository root.
- Headers hold one `key: value` per line.
  Write IDs in full wherever they appear, never as ranges.
- New IDs come from `sh record.sh next`;
  create a file only if none exists.
  Acceptance criteria take record-wide `AC-` IDs,
  each defined once, as `- AC-020:` in its objective.
  IDs are permanent; never reuse them.
  One session writes this record at a time.
- Log lines record events in `log/<YYYY-MM-DD>.md`,
  one physical line each, never wrapped, naming full IDs;
  never in this file or in entries.
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
