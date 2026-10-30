---
name: external-boundaries
description: >
  Manual only: load this skill only when the user names it
  or explicitly asks for it,
  never on your own judgement, even when the task matches.
  Designs and tests code that depends on something external,
  such as a network service, a subprocess, a terminal,
  or operating system or library behaviour:
  an adapter and consumers split at the boundary,
  API design that keeps them testable without monkeypatching,
  and end-to-end, assumption and unit tests
  driven by cases stored with the code.
---

# External boundaries

This skill is on trial and loads only when asked for,
so that it can be refined before it applies on its own.
When following it proves wrong, unclear or too much,
record that in the instruction backlog
as the instruction-backlog skill describes.

## Split Code at the Boundary

When code depends on something external,
such as a network service, a subprocess, a terminal or console,
or the behaviour of the operating system or a library,
split it at that boundary into:

- an **adapter**, which talks to the external thing
  and returns plain data or events in a documented shape;
- **consumers**, which take that data as input
  and never reach the external thing themselves.

Assumptions about the external output
and the handling of that output
can then be tested separately.

## Design APIs for It

Most of this is good design without any tests:

- **Give consumers data, not connections.**
  A consumer takes parsed values, such as entries, key codes
  or exit statuses, never a socket, a process or a terminal handle.
- **Split the adapter into transport and decoding.**
  Transport moves bytes; decoding turns them into the data shape,
  and is pure, so it can be tested with stored raw output.
- **Return decisions as data.**
  Where a consumer would cause side effects,
  it returns what to do, such as the files to copy,
  and the adapter does it.
- **Model events as sequences.**
  A consumer of events takes them as an iterator it pulls
  or as calls it receives, and never waits on the source.
- **Use plain values at the boundary**,
  which compare, print and serialize,
  so that cases can be stored and asserted with equality.
- **Do not read ambient state deep inside logic:**
  clocks, random seeds, environment variables,
  working directories and platform checks are external too.
- **Map external errors to the project's own** in the adapter.

Injection points are the part that is easily overdone.
Add one only where the code must use the external thing itself,
such as an event loop that blocks on real input,
and splitting the code into data in and data out is not enough.
Then use the lightest seam that works:

| Seam | Python | C++ |
| --- | --- | --- |
| Plain parameter | Argument, keyword argument | Function argument |
| Callable | Function argument | `std::function`, function pointer |
| Interface | Protocol, abstract base class | Abstract class with `virtual` functions |
| Compile time | Not applicable | Template parameter |

Do not rely on monkeypatching or link-time substitution
to reach code that could take a parameter instead.

Wire real adapters in one place, such as `main` or `run`,
without globals or singletons;
tests wire stored data or fakes in the same way.

## Limits

Apply this only at real external boundaries:
processes, networks, terminals, clocks and platforms,
not between the project's own modules.

- Prefer splitting the code over adding an injection point.
- Prefer the real thing when it is cheap and reliable,
  such as temporary directories, a pseudo-terminal,
  or a small script standing in for a subprocess.
  Fakes can drift from what they imitate.
- Do not add layers whose only purpose is a test.
- Stop when the production code becomes harder to read
  than the test gains.

Signs that it has been overdone:

- an interface with one real implementation and one fake,
  each used once;
- a wrapper whose methods only forward calls;
- a parameter that is always given the same value;
- names such as `Provider`, `Factory` or `Manager`
  around a single call;
- more fakes than tests, or fakes needing tests of their own.

## Three Kinds of Tests

| Kind | Checks | Comes from | Needs to run |
| --- | --- | --- | --- |
| End to end | Cases given as requirements: the external output used directly by the consumer | Requirements of the user or client | The external thing |
| Assumption | The external output for a specific input has the properties consumers rely on | Expected implementation details of the external thing | The external thing |
| Unit | Consumer behaviour on a fixed, stored output | The consumer's described behaviour | Nothing |

- **Unit tests** give the coverage,
  and must pass without the external thing.
  Their data may be written by hand;
  it need not come from real output.
- **Assumption tests** are written from what the consumer expects
  of the external thing's output,
  such as its format, ordering, exit codes and error cases,
  one test per assumption, named after it.
  They have their own inputs,
  and do not have to come from end-to-end cases.
- **End-to-end tests** check concrete cases
  from requirements given by the user or client,
  possibly with redacted real data,
  rather than described behaviour.
  Such a case can usually be split into assumption and unit tests,
  which makes the end-to-end test redundant in theory;
  it stays because it makes it easy to confirm the cases pass.
  When one fails, add the missing assumption and unit tests.

Name the kinds by what they check.
"Integration test" means different things in different languages:
in Rust, for example, it is any test of a crate's public API.

## Store Cases with the Code

Store test data with the code,
unless it is too large;
then find it through an option or an environment variable,
and skip its tests when it is missing.

An end-to-end case holds its **input**
and the **expected consumer result**.
It may also hold the **recorded output** of the external thing
for that input, which splits it:

- the end-to-end test checks that the consumer,
  given the external output for the input,
  gives the expected result;
- an assumption test checks that the external output for the input
  still matches the recorded output;
- a unit test checks that the consumer,
  given the recorded output,
  gives the expected result.

Provide a way to record outputs from the external thing,
used only when the tester chooses,
and review the recorded changes like code.
Recorded outputs are one source of assumption and unit tests,
not the only one.

A unit test's stored output may also be replaced by real output
when the tester chooses;
that run then counts as needing the external thing.

## Select Tests by What They Need

- Tests that need the external thing can be excluded as a group,
  and skip with a reason when it is missing.
- End-to-end tests can be selected on their own,
  to confirm the hard-coded cases pass.
- Unit tests run everywhere, with nothing to select.

For the mechanism in a language, read its reference file:

- Python with pytest: `references/python.md`.
- C++ with Catch2 and CTest: `references/cpp.md`.

For other languages, use the framework's own way
to tag, exclude and skip tests,
and to parametrize over data files.
