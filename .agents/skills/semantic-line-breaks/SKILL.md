---
name: semantic-line-breaks
description: >
  Wrap natural language at a line length limit,
  breaking at the ends of sentences and clauses
  or before important prepositions,
  so that diffs stay readable
  even when line breaks and leading spaces are ignored.
  Apply whenever writing or editing prose in files:
  Markdown paragraphs and lists, code comments, docstrings,
  commit message bodies and similar text.
  Not for chat replies or other text where line breaks render.
  Passive by default:
  no action needed on load unless file paths are provided.
---

## Behaviour on Load

- **No paths given:**
  Apply these rules to all prose written or edited in files from now on.
  No immediate action required.
- **Paths given:**
  Rewrap the prose in those files by these rules,
  leaving code, tables and other line-sensitive text unchanged.
  An explicit request to rewrap overrides the file's existing convention
  (see [Where Not to Apply](#where-not-to-apply)).

## Why

Prose with one line per sentence or clause
changes only the lines that were edited.
A reworded clause shows up as a changed line,
not as a reflowed paragraph.
Each line holds one unit of meaning,
so the diff stays readable
when a diff tool ignores whitespace, line breaks or indentation.

Where single line breaks do not render,
such as Markdown paragraphs or comments,
readers of the rendered output see no difference.

## Rules

### Line length

- Keep lines within the limit the project already uses
  for that kind of file:
  for example a formatter or linter setting,
  `.editorconfig`, or the surrounding text.
- Without one, keep lines within 80 characters,
  and prefer shorter.
  For commit message bodies, use 72.
- Count indentation and comment markers
  such as `#`, `//` or `*` toward the limit.

### Where to break

Start each sentence on a new line.
A sentence that fits within the limit may stay on one line;
break it anyway if it has two clearly separate clauses.
A longer sentence continues over several lines,
each ending at the strongest break point available.

Break, in order of preference:

1. After the end of a sentence.
2. After clause punctuation:
   a comma, semicolon, colon or dash ending a clause.
3. Before a word that starts a clause or phrase:
   a conjunction (`and`, `but`, `so`, `because`, `unless`),
   a relative word (`which`, `that`, `where`, `when`),
   or an important preposition (`for`, `with`, `without`, `from`, `by`).

Do not break:

- inside a phrase that reads as one unit,
  such as between an article or adjective and its noun,
  or a verb and a short object;
- inside inline code, a link, a path or a quoted name;
- just to make lines similar in length.

### Markdown pitfalls

A continuation line is parsed like any other line,
so it must not start with something that changes the rendering:

- a list marker (`-`, `*`, `+`) or a number followed by `.` or `)`;
- `#`, `>`, or a line made only of `=` or `-`.

Move the break one word earlier or later instead.
Never end a line with two spaces or a backslash,
since both force a visible line break.

### Editing existing text

- Rewrap only the sentences being changed.
  Do not reflow untouched lines, even if they break these rules,
  unless asked to rewrap the file.
- When adding words to a sentence,
  prefer a new line at a break point
  to reflowing the rest of the paragraph.

### Indentation

- Indent continuation lines of a Markdown list item
  to align with the item's text.
- Keep comment continuation lines in the language's comment form,
  aligned with the comment above.
- In YAML, use a folded block scalar (`>`)
  so that line breaks become spaces.

## Where Not to Apply

Line breaks are significant, or the text is not prose, in:

- code, command lines, tables, headings,
  and the first lines of list items when the format needs one line;
- commit message subject lines;
- user-facing strings in code,
  where a line break would change the output;
- text rendered with line breaks preserved,
  such as GitHub or GitLab issue and pull request descriptions,
  comments and chat messages (including your own replies),
  plain-text emails, and `<pre>` blocks;
- files whose existing style uses one line per paragraph,
  or a different wrapping convention;
  follow the file instead.

## Example

Instead of wrapping by width:

```markdown
The service retries failed requests on the next server, but only for
connection errors and HTTP 5xx responses, because repeating a request
after a 4xx would fail the same way on every server.
```

break at clauses:

```markdown
The service retries failed requests on the next server,
but only for connection errors and HTTP 5xx responses,
because repeating a request after a 4xx
would fail the same way on every server.
```

In a comment:

```python
# Updating a store triggers the section's callbacks,
# which would clear other errors shown there.
```
