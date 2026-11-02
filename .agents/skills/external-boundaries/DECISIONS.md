# Decisions: external-boundaries

Why this skill is as it is,
and changes that were rejected.
Read before proposing a change to it; not needed to use it.

- **D-1** `[accepted]` Split code at external boundaries
  so that assumptions and consumers are tested separately.
  - Reason: user, 2026-10-29: "When working with an external output
    such as network and subprocess, set up API in such a way
    that assumptions on output and consuming the output
    can be tested separately."
- **D-2** `[accepted]` Three kinds of tests:
  end to end, assumption and unit.
  - Reason: user, 2026-10-29: "(1) End to end testing is set up
    so that output is directly used by the consumer under test.
    (2) Assumption tests validate expected output from external API
    based on specific input. (3) Unit tests check behaviour
    of consumer based on fixed stored output."
    On (1): "They should be stored with the codebase,
    unless the data is huge. Think of it as checking hard-coded cases
    or requirements, as opposed to checking described behaviour."
- **D-3** `[accepted]` Assumption tests have their own inputs.
  - Change: they do not have to come from end-to-end cases;
    a "Comes from" column in the table of kinds.
  - Reason: user, 2026-10-29: "Assumption tests do not have to come
    from e2e. Assumptions can be created based on expected
    implementation detail of the third party output, whereas e2e
    would be more based on requirements given by user or client."
- **D-4** `[accepted]` Unit test data need not be real;
  real output only when the tester chooses.
  - Reason: user, 2026-10-29: "The fake data need not come from
    a real output. [...] tests can be set up to allow the input data
    to be overridden using real data based on user decision."
- **D-5** `[accepted]` Kinds named by what they check,
  not "integration test".
  - Reason: the term means different things across languages,
    such as Rust's tests of a crate's public API.
    User, 2026-10-29: "I would like this design
    to be a general coding style."
- **D-6** `[accepted]` Limits on API design for testing.
  - Change: "Limits": only at real external boundaries,
    splitting the code before adding injection points,
    the lightest seam, no layers only for tests,
    and signs of overdoing it.
  - Reason: user, 2026-10-29: "I worry that agents will try too hard
    to confirm to this, potentially making APIs too convoluted."
- **D-7** `[accepted]` A separate skill, manual only,
  through its summary alone.
  - Change: instead of additions to coding-conventions,
    python-style and cpp-style; language mechanics in `references/`.
  - Reason: user, 2026-10-29: "Can this be modified to a skill
    that requires manual trigger? This will give opportunities
    to refine the skill over time before it becomes automatic."
    Then: "Don't make this Claude specific.
    Consider using the header summary for this."
    Rejected: a tool-specific setting
    to stop agents loading it on their own.
  - Revisit: make it automatic, or move stable parts
    into coding-conventions and the language styles.
- **D-8** `[accepted]` Adapters may be tested by replacing
  the external library's own functions.
  - Change: under "Design APIs for It",
    an adapter calls the library directly,
    and its tests may replace the library's functions
    when the real thing cannot be used;
    the project's own code is never replaced this way.
  - Reason: "Do not rely on monkeypatching" and
    "a parameter that is always given the same value"
    pulled opposite ways for an adapter calling
    module-level functions of a terminal library,
    which production always passes the real ones.
    Found by an agent, 2026-10-30.
