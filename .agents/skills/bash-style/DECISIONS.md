# Decisions: bash-style

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.
Records start on 2026-11-15.

- **D-1** `[accepted]` 1.0.0: The skill, from `bin/dockered-claude`.
  - Change: a new skill describing the layout and rules
    of `bin/dockered-claude` in the dockered-claude project,
    which `.meta/apply-skill-drafts` there was rewritten to follow.
  - Reason: user, 2026-11-15: "update `.meta/apply-skill-drafts`
    script style to be similar to `bin/dockered-claude`
    in the sense of how it splits `main`, `run`, `parse_aguments`,
    calling into `main`, and other rules you may derive.
    Create a skill for this to be applied in future scripts,
    taking inspiration for the other language styling skills."
  - Reason: `main` parsing and forwarding to `run` follows python-style.
    `bin/dockered-claude`, whose `main` called each step itself,
    was refactored to match; user, 2026-11-15: "Refactor."
    Its `run` reads `kwargs`, `tools` and `packages` from `main`,
    as passing them would need namerefs,
    so the skill allows that when there are many options.
  - Reason: the opening paragraph for invocation with file paths
    and no load-behaviour wording follow cpp-style D-1.
- **D-2** `[accepted]` 1.0.0: `run` always reads `kwargs` and `args`.
  - Change: `run` takes no parameters
    and resolves the defaults of the options;
    `main` only parses, handles `--help` and calls `run`.
    Replaces the rule from D-1 that passed a few options as parameters.
  - Reason: user, 2026-11-15:
    "Evaluate pros and cons of allowing `run` to always use `args`
    and `kwargs` instead of taking aruments."
    Then: "Apply."
    One rule instead of a judgement on the number of options;
    the helpers below `run` read `kwargs` already,
    and option arrays cannot be passed by value.
    The cost, an interface nothing checks,
    is what every helper has under dynamic scope;
    a comment on `run` naming the keys it reads covers it.
  - Rejected: quoting inside `(( ))` and indexed subscripts.
    Double quotes work there,
    but a quoted empty value is a syntax error where a bare name is 0,
    and a quoted value is parsed as text where a bare one is evaluated alone;
    user, 2026-11-15: "Drop quoting change from before."
- **D-3** `[accepted]` 1.0.0: Functions trust their callers;
  associative keys are literal.
  - Change: "Functions", on naming parameters on the first line,
    no parsing or validation in internal functions,
    optional `:?` and `:-` guards, and comments on what else they use;
    a rule in "Syntax" that an associative subscript is a literal string.
  - Reason: user, 2026-11-15, on `run` reading `kwargs`:
    "Doing a full parse and validation for every function
    seems excessive. There has to be a convention somewhere."
    The convention is that the entry point parses and validates
    and internal functions trust their callers,
    as both scripts already did;
    Google's shell style guide documents a function's interface
    in its comment instead.
    Asked whether to add it: "Yes. And add with optional cheap guards."
  - Reason: a failed `:?` exits a non-interactive shell
    rather than failing the function,
    tested on bash 5.2.37: status 127, past `|| return`;
    inside `$( )` it ends only the subshell.
    Hence only for a caller's bug.
