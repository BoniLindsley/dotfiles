---
name: agents-md-maintainer
description: Create or update the AGENTS.md file at the root of a project — a short, contract-like reference that tells future agents which rules to follow and which tools/commands to use to follow them, without restating architecture an agent can infer by reading the code. Use this skill whenever starting substantial work in an unfamiliar or existing codebase and no AGENTS.md exists yet, whenever the user asks to "document the project for agents/AI", "write an AGENTS.md", "set up onboarding docs for Claude/agents", or after making changes that introduce a new rule, command, constraint, or non-standard pattern that would make an existing AGENTS.md stale. Also trigger this proactively (with permission) at the end of a substantial task if AGENTS.md exists but no longer reflects reality.
---

# AGENTS.md Maintainer

A skill for creating and keeping up to date an `AGENTS.md` file: a short, contract-like reference at the root of a project that tells a future agent (with no prior context) which rules govern this codebase and which tools/commands to use to follow them — without spending tool calls rediscovering things, and without padding the file with description an agent can get by reading the code itself.

## Core principle: a contract, not a tour

AGENTS.md's job is to shortcut discovery of things that are **binding but not inferable** — not to summarize the project. Evidence on these files is mixed: generic, prose-heavy, LLM-generated context files have been shown to *reduce* task success and add token/reasoning overhead, while short files full of concrete commands and explicit constraints improve efficiency. The dividing line is whether a section is a rule the agent must obey or a description the agent could reconstruct by reading the code.

Ask of every line: **"Would a competent agent get this wrong, or waste real effort discovering it, if this line didn't exist?"** If the answer is no, cut it.

This means:
- **Include:** exact commands (build/test/lint/run), version pins and non-negotiable dependency choices, constraints and rules ("always," "ask first," "never"), naming/process conventions not enforced by a linter, anything the agent would otherwise default to the "standard" or training-data-common approach and be wrong.
- **Exclude by default:** architecture overviews, prose explanations of "what this project does," and rationale/design-decision narratives. Standard-shape projects (a typical REST API, a typical React app, a typical CLI) don't need their architecture described — an agent reading the code will reconstruct it fine, and a stale architecture section is actively misleading.
- **Include architecture/rationale only when it's non-standard** — i.e., when the project deviates from what an agent would assume by convention, and that deviation isn't otherwise visible from a quick read (e.g., "this looks like a monorepo but the packages are independently versioned and must not share a lockfile," or "auth is handled by middleware in `edge/`, not in the route handlers where it'd normally live"). Frame these as rules/constraints, not backstory — state what the agent must do or must not assume, then the minimum context needed to make that make sense.

## When creating AGENTS.md for the first time

1. **Investigate for rules, not for a summary.** Read config/build files (package.json, pyproject.toml, Cargo.toml, etc.), CI config, linter/formatter config, and any existing docs to extract concrete commands and enforced conventions. Skim source directories specifically looking for: version pins, patterns that recur suspiciously consistently (a sign of an unwritten convention), anything structured in a way that breaks the "standard" shape for this kind of project. Check commit messages/CHANGELOG for constraints that were learned the hard way (reverted approaches, "never do X again" style fixes).
2. **Filter hard.** For each candidate item, check it against the core principle above. Default to leaving things out. A 15-line AGENTS.md that's all rules and commands beats a 150-line one with an architecture section.
3. **Draft using the template below.** Omit sections with nothing to put in them — an empty "Non-standard patterns" section is worse than no section.
4. **Show the draft to the user before writing it**, flagging anything you're inferring rather than confirming (especially proposed "never" rules — getting a prohibition wrong is worse than omitting it). A lightweight check is enough for an initial creation.

## Template

```markdown
# AGENTS.md

> Rules and tools for AI agents working in this repository. Keep this file current — see "Maintenance" below.

## Commands
[Exact, copy-pasteable commands an agent needs repeatedly: build, test (incl. running a single test),
lint/format, run/dev server, migrations, etc. Prefer these over describing where to find them.]

## Rules
[Binding constraints, grouped by how much latitude the agent has:
- **Always:** non-negotiable, no need to ask (e.g. run the linter before finishing, use conventional commits).
- **Ask first:** the agent may propose but must confirm before doing (e.g. adding a new dependency,
  changing a public API, touching CI config).
- **Never:** hard prohibitions (e.g. never commit secrets, never force-push to main, never edit generated files).]

## Non-standard patterns
[Only include this section if something here deviates from what an agent would assume by default/convention.
State the rule first, then just enough context to justify it, e.g.:
- Auth lives in `edge/middleware.ts`, not in route handlers — do not add per-route auth checks.
- Packages in this monorepo are independently versioned; do not add a shared lockfile.
Omit this section entirely for standard-shape projects.]

## Do not touch
[Files/directories an agent should leave alone without asking: generated code, migration history,
vendored dependencies, areas mid-refactor, anything with external side effects.]

## Pointers for more detail
[Where to look for depth this file intentionally omits — README, docs/, ADRs, subsystem docs. Link, don't duplicate.]

## Maintenance
Keep this file in sync with the project. If a change you make adds/removes a command, establishes or
retires a rule, or introduces/resolves a non-standard pattern, update AGENTS.md as part of that change.
Small factual fixes (a renamed command, a stale path) — just make the edit. Anything that adds, removes,
or reweights a rule, or restructures this file — propose it and ask the user first, since these are
judgment calls about what's binding.
```

## When updating an existing AGENTS.md

1. **Read the current file first.** Understand what it already claims before changing anything — don't regenerate it from scratch.
2. **Update as part of the work that made it stale**, not as an afterthought. If you just added a command, established a new rule, hit a non-standard pattern worth flagging, or the project moved to a more standard shape (making a prior "non-standard" entry obsolete), that's the moment to fold it in.
3. **Distinguish the kind of update, and ask permission accordingly:**
   - **Low-stakes / mechanical** (a command changed, a path was renamed, a typo) — just make the edit and mention it in passing.
   - **Substantive** (adding/removing/reweighting a rule — especially anything in "Always"/"Never" — adding a "Non-standard patterns" entry, restructuring the file) — propose the change and ask before writing. Show what you want to add/change/remove and why.
   - When unsure which bucket a change falls into, treat it as substantive and ask.
4. **Prune, don't just append.** If a rule no longer applies or a pattern became standard for the project, remove or correct the stale entry rather than leaving both old and new guidance — contradictory rules are worse than no rule.
5. **Resist scope creep back toward description.** If you're tempted to add a paragraph explaining *why* a rule exists beyond one clause, or to add an architecture section "for context," that's a sign the content belongs in README/docs instead, not in AGENTS.md.

## Splitting into multiple files

For large or multi-package projects, keep root `AGENTS.md` short and project-wide, and push package-specific rules into nested files rather than inlining everything:
- `AGENTS.md` at the root — project-wide commands and rules.
- Optionally, a nested `AGENTS.md` inside a subdirectory/package for rules specific to that area (e.g. `services/billing/AGENTS.md`), if that subproject has its own commands or non-standard patterns.
- Root AGENTS.md should mention that nested ones exist and roughly where.

## Style notes

- Write rules as imperatives ("Run `X` before finishing," "Never edit `Y`"), not descriptions ("The project uses X").
- Prefer a command or a one-line rule to a paragraph of explanation.
- Don't restate what's self-evident from the code or a standard config file.
- Don't pad the file to look thorough — an accurate 15-line file beats a padded 150-line one.
- If you can't tell whether something belongs (rule vs. description), it's probably description — leave it out.
